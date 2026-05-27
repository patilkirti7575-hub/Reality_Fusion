from rest_framework import viewsets, status, generics, permissions, filters
from rest_framework.decorators import action, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from django_filters.rest_framework import DjangoFilterBackend
from users.models import Profile, Follow, Block
from posts.models import Post, Comment, Story, StoryView, StoryLike, StoryMention, Reel, SavedPost, Report, StoryHighlight, Hashtag, HashtagTrend
from messaging.models import Message
from notifications.models import Notification
from .serializers import (
    UserSerializer, UserDetailSerializer, ProfileSerializer,
    FollowSerializer, BlockSerializer, HashtagSerializer, HashtagTrendSerializer,
    CommentSerializer, PostSerializer, PostCreateSerializer,
    SavedPostSerializer, ReportSerializer, StorySerializer,
    StoryHighlightSerializer, ReelSerializer, MessageSerializer,
    NotificationSerializer, RegisterSerializer, ChangePasswordSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    search_fields = ['email', 'username']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return UserDetailSerializer
        return UserSerializer

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = UserDetailSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def follow(self, request, pk=None):
        user_to_follow = self.get_object()
        if request.user == user_to_follow:
            return Response({'error': 'Cannot follow yourself'}, status=status.HTTP_400_BAD_REQUEST)
        if Block.objects.filter(blocker=user_to_follow, blocked=request.user).exists():
            return Response({'error': 'You are blocked by this user'}, status=status.HTTP_403_FORBIDDEN)
        Follow.objects.get_or_create(from_user=request.user, to_user=user_to_follow)
        Notification.objects.get_or_create(
            recipient=user_to_follow,
            actor=request.user,
            verb=Notification.FOLLOW,
        )
        return Response({'status': 'followed'})

    @action(detail=True, methods=['post'])
    def unfollow(self, request, pk=None):
        user_to_unfollow = self.get_object()
        Follow.objects.filter(from_user=request.user, to_user=user_to_unfollow).delete()
        return Response({'status': 'unfollowed'})

    @action(detail=True, methods=['get'])
    def followers(self, request, pk=None):
        user = self.get_object()
        follows = Follow.objects.filter(to_user=user)
        serializer = FollowSerializer(follows, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def following(self, request, pk=None):
        user = self.get_object()
        follows = Follow.objects.filter(from_user=user)
        serializer = FollowSerializer(follows, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def posts(self, request, pk=None):
        user = self.get_object()
        posts = Post.objects.filter(user=user)
        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = PostSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = PostSerializer(posts, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def reels(self, request, pk=None):
        user = self.get_object()
        reels = Reel.objects.filter(user=user)
        page = self.paginate_queryset(reels)
        if page is not None:
            serializer = ReelSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = ReelSerializer(reels, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def stories(self, request, pk=None):
        user = self.get_object()
        stories = Story.objects.filter(user=user, expires_at__gt=__import__('django').utils.timezone.now())
        serializer = StorySerializer(stories, many=True, context={'request': request})
        return Response(serializer.data)


class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer

    def get_object(self):
        return self.request.user.profile

    @action(detail=False, methods=['patch'])
    def update_me(self, request):
        profile = request.user.profile
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not user.check_password(serializer.validated_data['old_password']):
                return Response({'error': 'Wrong password'}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({'status': 'password changed'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    filterset_fields = ['user']
    search_fields = ['content']

    def get_serializer_class(self):
        if self.action == 'create':
            return PostCreateSerializer
        return PostSerializer

    def perform_create(self, serializer):
        post = serializer.save(user=self.request.user)
        self._extract_hashtags(post)

    def perform_update(self, serializer):
        post = serializer.save()
        post.hashtags.clear()
        self._extract_hashtags(post)

    def _extract_hashtags(self, post):
        import re
        tags = re.findall(r'#(\w+)', post.content)
        for tag_name in tags:
            hashtag, _ = Hashtag.objects.get_or_create(name=tag_name.lower())
            post.hashtags.add(hashtag)
            today = __import__('django').utils.timezone.now().date()
            trend, _ = HashtagTrend.objects.get_or_create(hashtag=hashtag, date=today)
            trend.count = HashtagTrend.objects.filter(hashtag=hashtag, date=today).count() + 1
            trend.save()

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        post = self.get_object()
        if request.user in post.likes.all():
            post.likes.remove(request.user)
            return Response({'status': 'unliked'})
        post.likes.add(request.user)
        if post.user != request.user:
            Notification.objects.get_or_create(
                recipient=post.user,
                actor=request.user,
                verb=Notification.LIKE,
                target_post=post,
            )
        return Response({'status': 'liked'})

    @action(detail=True, methods=['post'])
    def save(self, request, pk=None):
        post = self.get_object()
        saved, created = SavedPost.objects.get_or_create(user=request.user, post=post)
        if not created:
            saved.delete()
            return Response({'status': 'unsaved'})
        return Response({'status': 'saved'})

    @action(detail=True, methods=['get'])
    def comments(self, request, pk=None):
        post = self.get_object()
        comments = Comment.objects.filter(post=post)
        page = self.paginate_queryset(comments)
        if page is not None:
            serializer = CommentSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = CommentSerializer(comments, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def comment(self, request, pk=None):
        post = self.get_object()
        serializer = CommentSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            comment = serializer.save(post=post, user=request.user)
            if post.user != request.user:
                Notification.objects.get_or_create(
                    recipient=post.user,
                    actor=request.user,
                    verb=Notification.COMMENT,
                    target_post=post,
                )
            return Response(CommentSerializer(comment, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def report(self, request, pk=None):
        post = self.get_object()
        serializer = ReportSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(reporter=request.user, post=post)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FeedViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PostSerializer

    def get_queryset(self):
        following_users = Follow.objects.filter(from_user=self.request.user).values_list('to_user', flat=True)
        blocked_users = Block.objects.filter(blocker=self.request.user).values_list('blocked', flat=True)
        blocked_by = Block.objects.filter(blocked=self.request.user).values_list('blocker', flat=True)
        exclude_users = set(list(blocked_users) + list(blocked_by))
        users = list(following_users) + [self.request.user.id]
        return Post.objects.filter(user_id__in=users).exclude(user_id__in=exclude_users)


class ExploreViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PostSerializer
    search_fields = ['content']

    def get_queryset(self):
        blocked_users = Block.objects.filter(blocker=self.request.user).values_list('blocked', flat=True)
        blocked_by = Block.objects.filter(blocked=self.request.user).values_list('blocker', flat=True)
        exclude_users = set(list(blocked_users) + list(blocked_by))
        return Post.objects.exclude(user_id__in=exclude_users).annotate(
            like_count=Count('likes')
        ).order_by('-like_count', '-created_at')


class ReelViewSet(viewsets.ModelViewSet):
    queryset = Reel.objects.all()
    serializer_class = ReelSerializer
    search_fields = ['caption']

    def perform_create(self, serializer):
        reel = serializer.save(user=self.request.user)
        import re
        tags = re.findall(r'#(\w+)', reel.caption)
        for tag_name in tags:
            hashtag, _ = Hashtag.objects.get_or_create(name=tag_name.lower())
            reel.hashtags.add(hashtag)

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        reel = self.get_object()
        if request.user in reel.likes.all():
            reel.likes.remove(request.user)
            return Response({'status': 'unliked'})
        reel.likes.add(request.user)
        if reel.user != request.user:
            Notification.objects.get_or_create(
                recipient=reel.user,
                actor=request.user,
                verb=Notification.REEL_LIKE,
                target_reel=reel,
            )
        return Response({'status': 'liked'})

    @action(detail=True, methods=['post'])
    def view(self, request, pk=None):
        reel = self.get_object()
        reel.views += 1
        reel.save()
        return Response({'views': reel.views})


class StoryViewSet(viewsets.ModelViewSet):
    queryset = Story.objects.all()
    serializer_class = StorySerializer

    def get_queryset(self):
        following_users = Follow.objects.filter(from_user=self.request.user).values_list('to_user', flat=True)
        return Story.objects.filter(
            Q(user__in=following_users) | Q(user=self.request.user),
            expires_at__gt=__import__('django').utils.timezone.now()
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def view(self, request, pk=None):
        story = self.get_object()
        StoryView.objects.get_or_create(story=story, user=request.user)
        return Response({'status': 'viewed'})

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        story = self.get_object()
        like, created = StoryLike.objects.get_or_create(story=story, user=request.user)
        if not created:
            like.delete()
            return Response({'liked': False, 'likes_count': story.likes.count()})
        if story.user != request.user:
            Notification.objects.get_or_create(
                recipient=story.user,
                actor=request.user,
                verb=Notification.STORY_LIKE,
                target_story=story,
            )
        return Response({'liked': True, 'likes_count': story.likes.count()})


class StoryHighlightViewSet(viewsets.ModelViewSet):
    queryset = StoryHighlight.objects.all()
    serializer_class = StoryHighlightSerializer

    def get_queryset(self):
        return StoryHighlight.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SavedPostViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SavedPostSerializer

    def get_queryset(self):
        return SavedPost.objects.filter(user=self.request.user)

    def get_serializer_context(self):
        return {'request': self.request}


class HashtagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Hashtag.objects.all()
    serializer_class = HashtagSerializer
    search_fields = ['name']

    @action(detail=True, methods=['get'])
    def posts(self, request, pk=None):
        hashtag = self.get_object()
        posts = Post.objects.filter(hashtags=hashtag)
        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = PostSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = PostSerializer(posts, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def reels(self, request, pk=None):
        hashtag = self.get_object()
        reels = Reel.objects.filter(hashtags=hashtag)
        page = self.paginate_queryset(reels)
        if page is not None:
            serializer = ReelSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = ReelSerializer(reels, many=True, context={'request': request})
        return Response(serializer.data)


class TrendingHashtagsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HashtagTrend.objects.all()
    serializer_class = HashtagTrendSerializer

    def get_queryset(self):
        return HashtagTrend.objects.all().order_by('-count')[:20]


class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    filterset_fields = ['sender', 'receiver']

    def get_queryset(self):
        return Message.objects.filter(
            Q(sender=self.request.user) | Q(receiver=self.request.user)
        )

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

    @action(detail=False, methods=['get'])
    def conversation(self, request):
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        messages = Message.objects.filter(
            Q(sender=request.user, receiver_id=user_id) |
            Q(sender_id=user_id, receiver=request.user)
        )
        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = MessageSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = MessageSerializer(messages, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        message = self.get_object()
        message.is_read = True
        message.save()
        return Response({'status': 'marked as read'})


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({'count': count})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({'status': 'all marked as read'})


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class FollowViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Follow.objects.all()
    serializer_class = FollowSerializer
    filterset_fields = ['from_user', 'to_user']


class SearchViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def all(self, request):
        q = request.query_params.get('q', '')
        if not q:
            return Response({'error': 'q parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        users = User.objects.filter(
            Q(email__icontains=q) | Q(username__icontains=q)
        )[:10]
        posts = Post.objects.filter(content__icontains=q)[:10]
        hashtags = Hashtag.objects.filter(name__icontains=q)[:10]
        return Response({
            'users': UserSerializer(users, many=True, context={'request': request}).data,
            'posts': PostSerializer(posts, many=True, context={'request': request}).data,
            'hashtags': HashtagSerializer(hashtags, many=True).data,
        })
