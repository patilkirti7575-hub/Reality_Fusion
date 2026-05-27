from rest_framework import serializers
from django.contrib.auth import get_user_model
from RealityFusion_project.users.models import Profile, Follow, Block
from RealityFusion_project.posts.models import Post, Comment, Story, StoryView, StoryLike, StoryMention, Reel, ReelComment, SavedPost, SavedReel, Report, StoryHighlight, Hashtag, HashtagTrend
from RealityFusion_project.messaging.models import Message
from RealityFusion_project.notifications.models import Notification

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    profile_pic = serializers.SerializerMethodField()
    is_verified = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'profile_pic', 'is_verified', 'is_online', 'last_seen', 'created_at']

    def get_profile_pic(self, obj):
        if hasattr(obj, 'profile') and obj.profile.profile_pic:
            return obj.profile.profile_pic.url
        return None

    def get_is_verified(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.is_verified
        return False


class UserDetailSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()
    follower_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    post_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'profile', 'follower_count', 'following_count', 'post_count', 'is_online', 'last_seen', 'created_at']

    def get_profile(self, obj):
        if hasattr(obj, 'profile'):
            return ProfileSerializer(obj.profile).data
        return None

    def get_follower_count(self, obj):
        return obj.followers.count()

    def get_following_count(self, obj):
        return obj.following.count()

    def get_post_count(self, obj):
        return obj.posts.count()


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['bio', 'profile_pic', 'cover_image', 'website', 'is_verified', 'theme']


class FollowSerializer(serializers.ModelSerializer):
    from_user = UserSerializer(read_only=True)
    to_user = UserSerializer(read_only=True)

    class Meta:
        model = Follow
        fields = ['id', 'from_user', 'to_user', 'created_at']


class BlockSerializer(serializers.ModelSerializer):
    blocker = UserSerializer(read_only=True)
    blocked = UserSerializer(read_only=True)

    class Meta:
        model = Block
        fields = ['id', 'blocker', 'blocked', 'created_at']


class HashtagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hashtag
        fields = ['id', 'name', 'created_at']


class HashtagTrendSerializer(serializers.ModelSerializer):
    hashtag = HashtagSerializer(read_only=True)

    class Meta:
        model = HashtagTrend
        fields = ['id', 'hashtag', 'count', 'date']


class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'post', 'user', 'content', 'created_at']


class PostSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    comment_count = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    is_saved = serializers.SerializerMethodField()
    hashtags = HashtagSerializer(many=True, read_only=True)

    class Meta:
        model = Post
        fields = ['id', 'user', 'content', 'image', 'video', 'created_at', 'likes', 'comment_count', 'like_count', 'is_liked', 'is_saved', 'hashtags']

    def get_comment_count(self, obj):
        return obj.comments.count()

    def get_like_count(self, obj):
        return obj.likes.count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.id).exists()
        return False

    def get_is_saved(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return SavedPost.objects.filter(user=request.user, post=obj).exists()
        return False


class PostCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ['content', 'image', 'video', 'hashtags']


class SavedPostSerializer(serializers.ModelSerializer):
    post = PostSerializer(read_only=True)

    class Meta:
        model = SavedPost
        fields = ['id', 'user', 'post', 'saved_at']


class ReportSerializer(serializers.ModelSerializer):
    reporter = UserSerializer(read_only=True)

    class Meta:
        model = Report
        fields = ['id', 'reporter', 'post', 'comment', 'reason', 'description', 'resolved', 'created_at']


class StorySerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    view_count = serializers.SerializerMethodField()
    is_viewed = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Story
        fields = ['id', 'user', 'image', 'video', 'caption', 'created_at', 'expires_at', 'is_expired', 'view_count', 'is_viewed', 'likes_count', 'is_liked']

    def get_view_count(self, obj):
        return obj.views.count()

    def get_is_viewed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return StoryView.objects.filter(story=obj, user=request.user).exists()
        return False

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return StoryLike.objects.filter(story=obj, user=request.user).exists()
        return False


class StoryHighlightSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    stories = StorySerializer(many=True, read_only=True)

    class Meta:
        model = StoryHighlight
        fields = ['id', 'user', 'title', 'cover', 'stories', 'created_at']


class ReelSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    like_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    is_saved = serializers.SerializerMethodField()
    hashtags = HashtagSerializer(many=True, read_only=True)

    class Meta:
        model = Reel
        fields = ['id', 'user', 'video', 'caption', 'created_at', 'likes', 'views', 'like_count', 'is_liked', 'comment_count', 'is_saved', 'hashtags']

    def get_like_count(self, obj):
        return obj.likes.count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.id).exists()
        return False

    def get_comment_count(self, obj):
        return obj.comments.count()

    def get_is_saved(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return SavedReel.objects.filter(user=request.user, reel=obj).exists()
        return False


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    receiver = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'sender', 'receiver', 'content', 'timestamp', 'is_read', 'is_delivered', 'shared_post']


class NotificationSerializer(serializers.ModelSerializer):
    actor = UserSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'recipient', 'actor', 'verb', 'target_post', 'target_reel', 'target_story', 'is_read', 'created_at']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['email', 'username', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data.get('username', ''),
            password=validated_data['password']
        )
        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=6)
