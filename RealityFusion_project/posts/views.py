import json
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, ListView, TemplateView, View
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db import models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib import messages
from .models import (
    Post, Comment, Story, StoryView, MutedStory, StoryLike, StoryMention,
    Reel, ReelComment, SavedPost, SavedReel, ReelShare, TaggedItem,
    StoryMusic, StoryPoll, StoryPollVote, StoryReaction, ReelAudio, CameraFilter, CameraEffect
)
from .forms import PostForm, StoryForm, ReelForm
from users.models import CustomUser, Follow
from notifications.models import Notification

class FeedView(LoginRequiredMixin, ListView):
    model = Post
    template_name = 'posts/feed.html'
    context_object_name = 'posts'

    def get_queryset(self):
        # Show only image/text posts (no videos)
        following = Follow.objects.filter(from_user=self.request.user).values_list('to_user', flat=True)
        return Post.objects.filter(
            models.Q(user=self.request.user) | models.Q(user_id__in=following)
        ).select_related('user').prefetch_related('comments', 'likes')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['trending_posts'] = Post.objects.annotate(like_count=models.Count('likes')).order_by('-like_count')[:5]
        # Active stories (not expired) from followed users + own
        following = Follow.objects.filter(from_user=self.request.user).values_list('to_user', flat=True)
        user_ids = list(following) + [self.request.user.id]
        active_stories = Story.objects.filter(
            user_id__in=user_ids,
            expires_at__gt=timezone.now()
        ).select_related('user__profile').order_by('-created_at')
        # Group by user
        story_users = {}
        for s in active_stories:
            if s.user not in story_users:
                story_users[s.user] = []
            story_users[s.user].append(s)
        # Check if current user has stories
        context['user_has_stories'] = self.request.user in story_users
        # Users who have active stories (excluding current user)
        other_users = [u for u in story_users.keys() if u != self.request.user]
        ordered_users = sorted(other_users, key=lambda u: u.email)

        # Determine which users have ALL stories viewed
        user = self.request.user
        viewed_user_ids = set()
        for u in other_users:
            user_stories = story_users[u]
            total = len(user_stories)
            viewed = StoryView.objects.filter(story__in=user_stories, user=user).count()
            if viewed >= total:
                viewed_user_ids.add(u.id)

        # Get muted user IDs and move muted users to end
        muted_ids = set(MutedStory.objects.filter(user=user).values_list('muted_user_id', flat=True))
        muted_users = [u for u in ordered_users if u.id in muted_ids]
        unmuted_users = [u for u in ordered_users if u.id not in muted_ids]
        ordered_users = unmuted_users + muted_users

        context['stories_users'] = ordered_users
        context['users_with_stories'] = [u.id for u in story_users.keys()]
        context['viewed_user_ids'] = viewed_user_ids
        context['muted_user_ids'] = muted_ids
        context['saved_post_ids'] = set(
            SavedPost.objects.filter(user=self.request.user).values_list('post_id', flat=True)
        )
        context['feed_reels'] = Reel.objects.exclude(video='').select_related('user__profile').order_by('-created_at')[:10]
        context['saved_reel_ids'] = set(
            SavedReel.objects.filter(user=self.request.user).values_list('reel_id', flat=True)
        )
        return context

class ExploreView(LoginRequiredMixin, ListView):
    model = Post
    template_name = 'posts/explore.html'
    context_object_name = 'posts'

    def get_queryset(self):
        return Post.objects.all().select_related('user').order_by('-created_at')[:30]

class ReelsView(LoginRequiredMixin, ListView):
    model = Reel
    template_name = 'posts/reels.html'
    context_object_name = 'reels'

    def get_queryset(self):
        return Reel.objects.exclude(video='').select_related('user__profile').order_by('-created_at')[:50]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reel_ids = [r.id for r in context['reels']]
        context['saved_reel_ids'] = set(
            SavedReel.objects.filter(user=self.request.user, reel_id__in=reel_ids).values_list('reel_id', flat=True)
        )
        context['liked_reel_ids'] = set(
            Reel.likes.through.objects.filter(customuser=self.request.user, reel_id__in=reel_ids).values_list('reel_id', flat=True)
        )
        return context


class ReelCreateView(LoginRequiredMixin, CreateView):
    model = Reel
    form_class = ReelForm
    template_name = 'posts/upload_reel.html'
    success_url = reverse_lazy('reels')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Error uploading reel. Check the form.')
        return super().form_invalid(form)


class ReelLikeView(LoginRequiredMixin, TemplateView):
    def post(self, request, reel_id):
        reel = get_object_or_404(Reel, id=reel_id)
        if request.user in reel.likes.all():
            reel.likes.remove(request.user)
            liked = False
        else:
            reel.likes.add(request.user)
            liked = True
            if reel.user != request.user:
                Notification.objects.get_or_create(
                    recipient=reel.user,
                    actor=request.user,
                    verb=Notification.REEL_LIKE,
                    target_reel=reel,
                )
        return JsonResponse({'likes_count': reel.likes.count(), 'liked': liked})


class ReelDeleteView(LoginRequiredMixin, TemplateView):
    def post(self, request, reel_id):
        reel = get_object_or_404(Reel, id=reel_id, user=request.user)
        if reel.video:
            reel.video.delete(save=False)
        reel.delete()
        return JsonResponse({'status': 'deleted'})


class ReelCommentView(LoginRequiredMixin, TemplateView):
    def post(self, request, reel_id):
        reel = get_object_or_404(Reel, id=reel_id)
        content = request.POST.get('content', '').strip()
        if content:
            ReelComment.objects.create(reel=reel, user=request.user, content=content)
            if reel.user != request.user:
                Notification.objects.get_or_create(
                    recipient=reel.user,
                    actor=request.user,
                    verb=Notification.REEL_COMMENT,
                    target_reel=reel,
                )
        return JsonResponse({'status': 'success', 'count': reel.comments.count()})


class ReelCommentsJSONView(LoginRequiredMixin, TemplateView):
    def get(self, request, reel_id):
        reel = get_object_or_404(Reel, id=reel_id)
        comments = ReelComment.objects.filter(reel=reel).select_related('user__profile').order_by('-created_at')
        data = [{
            'id': c.id,
            'user_id': c.user.id,
            'username': c.user.username or c.user.email,
            'profile_pic': c.user.profile.profile_pic.url if hasattr(c.user, 'profile') and c.user.profile.profile_pic else None,
            'content': c.content,
            'created_at': c.created_at.strftime('%b %d, %Y at %I:%M %p'),
            'time_ago': c.created_at.timestamp(),
        } for c in comments]
        return JsonResponse({'comments': data, 'count': len(data)})


class ReelSaveView(LoginRequiredMixin, TemplateView):
    def post(self, request, reel_id):
        reel = get_object_or_404(Reel, id=reel_id)
        saved, created = SavedReel.objects.get_or_create(user=request.user, reel=reel)
        if not created:
            saved.delete()
            return JsonResponse({'saved': False})
        return JsonResponse({'saved': True})


class ReelShareView(LoginRequiredMixin, TemplateView):
    def post(self, request, reel_id):
        reel = get_object_or_404(Reel, id=reel_id)
        action = request.POST.get('action', 'link')
        recipient_id = request.POST.get('recipient_id')

        if action == 'chat' and recipient_id:
            from messaging.models import Message
            recipient = get_object_or_404(CustomUser, id=recipient_id)
            Message.objects.create(
                sender=request.user,
                receiver=recipient,
                content=f'Shared a reel: {reel.caption[:80]}{"..." if len(reel.caption) > 80 else ""}',
                shared_reel=reel
            )

        # Record share
        ReelShare.objects.create(user=request.user, reel=reel)
        reel.views += 1
        reel.save(update_fields=['views'])

        if reel.user != request.user:
            Notification.objects.get_or_create(
                recipient=reel.user,
                actor=request.user,
                verb=Notification.REEL_SHARE,
                target_reel=reel,
            )

        share_url = request.build_absolute_uri(f'/reel/{reel_id}/')
        return JsonResponse({
            'status': 'shared',
            'share_url': share_url,
            'share_count': reel.share_count,
            'views': reel.views,
        })


class ReelDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'posts/reel_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reel = get_object_or_404(
            Reel.objects.select_related('user__profile').exclude(video=''),
            id=kwargs['reel_id']
        )
        reel.views += 1
        reel.save(update_fields=['views'])
        context['reel'] = reel
        context['saved'] = SavedReel.objects.filter(user=self.request.user, reel=reel).exists()
        return context


class TaggedView(LoginRequiredMixin, ListView):
    model = TaggedItem
    template_name = 'posts/tagged.html'
    context_object_name = 'tagged_items'

    def get_queryset(self):
        user_id = self.kwargs.get('user_id')
        if user_id:
            user = get_object_or_404(CustomUser, id=user_id)
        else:
            user = self.request.user
        return TaggedItem.objects.filter(user=user).select_related('post', 'reel', 'tagged_by')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_id = self.kwargs.get('user_id')
        if user_id:
            context['profile_user'] = get_object_or_404(CustomUser, id=user_id)
        else:
            context['profile_user'] = self.request.user
        return context


class PostCreateView(LoginRequiredMixin, CreateView):
    form_class = PostForm
    template_name = 'posts/post_create.html'
    success_url = reverse_lazy('feed')

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        if self.object.image:
            Story.objects.create(
                user=self.request.user,
                image=self.object.image,
                caption=self.object.content,
            )
        return response

class LikeView(LoginRequiredMixin, TemplateView):
    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        if request.user in post.likes.all():
            post.likes.remove(request.user)
            liked = False
        else:
            post.likes.add(request.user)
            liked = True
            if post.user != request.user:
                Notification.objects.create(
                    recipient=post.user,
                    actor=request.user,
                    verb=Notification.LIKE,
                    target_post=post,
                )
        return JsonResponse({'likes_count': post.likes.count(), 'liked': liked})

class CommentView(LoginRequiredMixin, TemplateView):
    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        content = request.POST.get('content', '').strip()
        if content:
            Comment.objects.create(post=post, user=request.user, content=content)
            if post.user != request.user:
                Notification.objects.create(
                    recipient=post.user,
                    actor=request.user,
                    verb=Notification.COMMENT,
                    target_post=post,
                )
        return JsonResponse({'status': 'success', 'count': post.comments.count()})

class SavePostView(LoginRequiredMixin, TemplateView):
    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        saved, created = SavedPost.objects.get_or_create(user=request.user, post=post)
        if not created:
            saved.delete()
            return JsonResponse({'saved': False})
        return JsonResponse({'saved': True})


class PostDeleteView(LoginRequiredMixin, TemplateView):
    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id, user=request.user)
        if post.image:
            post.image.delete(save=False)
        post.delete()
        return JsonResponse({'status': 'deleted'})


class StoryUploadView(LoginRequiredMixin, CreateView):
    form_class = StoryForm
    template_name = 'posts/upload_story.html'
    success_url = reverse_lazy('feed')

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        story = self.object
        if story.caption:
            import re
            mentioned_usernames = re.findall(r'@(\w+)', story.caption)
            for username in mentioned_usernames:
                try:
                    mentioned_user = CustomUser.objects.get(username__iexact=username)
                    StoryMention.objects.get_or_create(story=story, user=mentioned_user)
                    if mentioned_user != self.request.user:
                        Notification.objects.get_or_create(
                            recipient=mentioned_user,
                            actor=self.request.user,
                            verb=Notification.STORY_MENTION,
                            target_story=story,
                        )
                except CustomUser.DoesNotExist:
                    pass
        messages.success(self.request, 'Your story has been shared!')
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'Please select an image or video for your story.')
        return super().form_invalid(form)

class StoryJSONView(LoginRequiredMixin, TemplateView):
    def get(self, request, user_id):
        user = get_object_or_404(CustomUser, id=user_id)
        stories = Story.objects.filter(
            user=user, expires_at__gt=timezone.now()
        ).order_by('-created_at')

        # Mark first story as viewed BEFORE building data (so count is accurate)
        if stories:
            first_story = stories.first()
            first_view_created = False
            if request.user != user:
                _, first_view_created = StoryView.objects.get_or_create(story=first_story, user=request.user)
            else:
                StoryView.objects.get_or_create(story=first_story, user=request.user)

        viewed_ids = StoryView.objects.filter(
            story__in=stories, user=request.user
        ).values_list('story_id', flat=True)
        liked_ids = set(StoryLike.objects.filter(
            story__in=stories, user=request.user
        ).values_list('story_id', flat=True))
        data = [{
            'id': s.id,
            'userId': user.id,
            'image_url': s.image.url if s.image else None,
            'video_url': s.video.url if s.video else None,
            'caption': s.caption,
            'created_at': s.created_at.strftime('%I:%M %p'),
            'viewed': s.id in viewed_ids,
            'is_owner': request.user == user,
            'views_count': s.views.count(),
            'likes_count': s.likes.count(),
            'is_liked': s.id in liked_ids,
            'mentions': [{'id': m.user.id, 'username': m.user.username or m.user.email} for m in s.mentions.select_related('user')],
        } for s in stories]

        # Send notification for first view if applicable
        if stories and first_view_created and request.user != user:
            Notification.objects.get_or_create(
                recipient=user,
                actor=request.user,
                verb=Notification.STORY_VIEW,
                target_story=stories.first(),
            )

        return JsonResponse({
            'stories': data,
            'user': {
                'id': user.id,
                'email': user.email,
                'username': user.username or user.email,
                'profile_pic': user.profile.profile_pic.url if hasattr(user, 'profile') and user.profile.profile_pic else None,
            }
        })

class StoryViewedView(LoginRequiredMixin, TemplateView):
    def post(self, request, story_id):
        story = get_object_or_404(Story, id=story_id)
        _, created = StoryView.objects.get_or_create(story=story, user=request.user)
        if created and story.user != request.user:
            Notification.objects.get_or_create(
                recipient=story.user,
                actor=request.user,
                verb=Notification.STORY_VIEW,
                target_story=story,
            )
        return JsonResponse({'status': 'viewed'})


class StoryMuteView(LoginRequiredMixin, TemplateView):
    def post(self, request, user_id):
        target = get_object_or_404(CustomUser, id=user_id)
        if target == request.user:
            return JsonResponse({'status': 'error', 'error': 'Cannot mute yourself'}, status=400)
        muted, created = MutedStory.objects.get_or_create(user=request.user, muted_user=target)
        if not created:
            muted.delete()
            return JsonResponse({'status': 'unmuted'})
        return JsonResponse({'status': 'muted'})


class StoryViewersJSONView(LoginRequiredMixin, TemplateView):
    def get(self, request, story_id):
        story = get_object_or_404(Story, id=story_id)
        if story.user != request.user:
            return JsonResponse({'error': 'Forbidden'}, status=403)
        viewers = StoryView.objects.filter(story=story).select_related('user__profile').order_by('-viewed_at')
        data = [{
            'id': sv.user.id,
            'username': sv.user.username or sv.user.email,
            'profile_pic': sv.user.profile.profile_pic.url if hasattr(sv.user, 'profile') and sv.user.profile.profile_pic else None,
            'viewed_at': sv.viewed_at.strftime('%b %d, %Y at %I:%M %p'),
            'time_ago': sv.viewed_at.timestamp(),
        } for sv in viewers]
        return JsonResponse({'viewers': data, 'count': len(data)})

class StoryLikeView(LoginRequiredMixin, TemplateView):
    def post(self, request, story_id):
        story = get_object_or_404(Story, id=story_id)
        like, created = StoryLike.objects.get_or_create(story=story, user=request.user)
        if not created:
            like.delete()
            return JsonResponse({'liked': False, 'likes_count': story.likes.count()})
        if story.user != request.user:
            Notification.objects.get_or_create(
                recipient=story.user,
                actor=request.user,
                verb=Notification.STORY_LIKE,
                target_story=story,
            )
        return JsonResponse({'liked': True, 'likes_count': story.likes.count()})


class StoryDeleteView(LoginRequiredMixin, TemplateView):
    def post(self, request, story_id):
        story = get_object_or_404(Story, id=story_id, user=request.user)
        if story.image:
            story.image.delete(save=False)
        if story.video:
            story.video.delete(save=False)
        story.delete()
        return JsonResponse({'status': 'deleted'})


class StoryViewerView(LoginRequiredMixin, TemplateView):
    template_name = 'posts/story_view.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        story = get_object_or_404(Story, id=self.kwargs['story_id'])
        if story.is_expired():
            context['error'] = 'This story has expired.'
            return context
        user = story.user
        other_stories = Story.objects.filter(
            user=user, expires_at__gt=timezone.now()
        ).order_by('-created_at')
        context['story'] = story
        context['story_user'] = user
        context['other_stories'] = other_stories
        context['is_owner'] = self.request.user == user
        context['viewed'] = StoryView.objects.filter(story=story, user=self.request.user).exists()
        context['is_liked'] = StoryLike.objects.filter(story=story, user=self.request.user).exists()
        context['viewers'] = StoryView.objects.filter(story=story).select_related('user__profile').order_by('-viewed_at') if context['is_owner'] else []
        if not context['viewed']:
            StoryView.objects.get_or_create(story=story, user=self.request.user)
            if not context['is_owner']:
                Notification.objects.get_or_create(
                    recipient=user,
                    actor=self.request.user,
                    verb=Notification.STORY_VIEW,
                    target_story=story,
                )
        return context


class SavedReelsView(LoginRequiredMixin, TemplateView):
    template_name = 'posts/saved_reels.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['saved_reels'] = SavedReel.objects.filter(
            user=self.request.user
        ).select_related('reel__user__profile').order_by('-saved_at')
        return context


# ====== ADVANCED STORY VIEWS ======

class StoryEditorView(LoginRequiredMixin, TemplateView):
    template_name = 'posts/story_editor.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['music_tracks'] = StoryMusic.objects.all()
        context['filters'] = CameraFilter.objects.filter(is_active=True)
        return context


class StorySaveAdvancedView(LoginRequiredMixin, View):
    def post(self, request):
        image = request.FILES.get('image')
        video = request.FILES.get('video')
        caption = request.POST.get('caption', '')
        audio_id = request.POST.get('audio_id')
        location_name = request.POST.get('location_name', '')
        text_overlays = request.POST.get('text_overlays', '[]')
        poll_question = request.POST.get('poll_question', '')
        poll_option1 = request.POST.get('poll_option1', '')
        poll_option2 = request.POST.get('poll_option2', '')
        poll_option3 = request.POST.get('poll_option3', '')
        poll_option4 = request.POST.get('poll_option4', '')

        if not image and not video:
            return JsonResponse({'error': 'No media provided'}, status=400)

        story = Story(
            user=request.user,
            image=image,
            video=video,
            caption=caption,
            location_name=location_name,
            text_overlay_data=text_overlays,
        )
        if audio_id:
            story.audio_id = int(audio_id)
        story.save()

        # Parse @mentions
        if caption:
            import re
            for username in re.findall(r'@(\w+)', caption):
                try:
                    mentioned = CustomUser.objects.get(username__iexact=username)
                    StoryMention.objects.get_or_create(story=story, user=mentioned)
                    if mentioned != request.user:
                        Notification.objects.get_or_create(
                            recipient=mentioned, actor=request.user,
                            verb=Notification.STORY_MENTION, target_story=story,
                        )
                except CustomUser.DoesNotExist:
                    pass

        # Create poll if provided (supports up to 4 options)
        if poll_question and poll_option1 and poll_option2:
            StoryPoll.objects.create(
                story=story, question=poll_question,
                option1=poll_option1, option2=poll_option2,
                option3=poll_option3, option4=poll_option4,
            )

        return JsonResponse({'status': 'ok', 'story_id': story.id})


class StoryReactView(LoginRequiredMixin, View):
    def post(self, request, story_id):
        story = get_object_or_404(Story, id=story_id)
        emoji = request.POST.get('emoji', '❤️')
        if not story.allow_reactions:
            return JsonResponse({'error': 'Reactions disabled'}, status=400)
        reaction, created = StoryReaction.objects.get_or_create(
            story=story, user=request.user, emoji=emoji
        )
        if not created:
            reaction.delete()
            return JsonResponse({'reacted': False})
        return JsonResponse({'reacted': True, 'emoji': emoji})


class StoryPollVoteView(LoginRequiredMixin, View):
    def post(self, request, story_id):
        story = get_object_or_404(Story, id=story_id)
        poll = getattr(story, 'poll', None)
        if not poll:
            return JsonResponse({'error': 'No poll'}, status=400)
        option = int(request.POST.get('option', 0))
        if option not in [1, 2, 3, 4]:
            return JsonResponse({'error': 'Invalid option'}, status=400)
        vote, created = StoryPollVote.objects.get_or_create(
            poll=poll, user=request.user, defaults={'option': option}
        )
        if not created:
            vote.option = option
            vote.save()
        return JsonResponse({
            'voted': True,
            'option': option,
            'total': poll.total_votes(),
        })


class StoryMusicJSONView(LoginRequiredMixin, View):
    def get(self, request):
        music = StoryMusic.objects.all()
        data = [{
            'id': m.id, 'title': m.title, 'artist': m.artist,
            'audio_url': m.audio_file.url if m.audio_file else None,
            'cover_url': m.cover_image.url if m.cover_image else None,
            'duration': m.duration,
            'language': m.language,
        } for m in music]
        return JsonResponse({'music': data})


class StoryMusicSearchView(LoginRequiredMixin, View):
    """Search music tracks by query and/or language, with hardcoded fallback."""
    def get(self, request):
        query = request.GET.get('q', '').strip()
        lang = request.GET.get('lang', '').strip()

        tracks = StoryMusic.objects.all()
        if query:
            tracks = tracks.filter(
                models.Q(title__icontains=query) |
                models.Q(artist__icontains=query) |
                models.Q(language__icontains=query)
            )
        if lang and lang != 'all':
            tracks = tracks.filter(language__iexact=lang)

        if tracks.exists():
            data = [{
                'id': m.id, 'title': m.title, 'artist': m.artist,
                'audio_url': m.audio_file.url if m.audio_file else None,
                'cover_url': m.cover_image.url if m.cover_image else None,
                'duration': m.duration,
                'language': m.language,
            } for m in tracks]
            return JsonResponse({'music': data, 'source': 'db'})

        # Fallback: return all tracks if no match
        tracks = StoryMusic.objects.all()
        if lang and lang != 'all':
            tracks = tracks.filter(language__iexact=lang)
        data = [{
            'id': m.id, 'title': m.title, 'artist': m.artist,
            'audio_url': m.audio_file.url if m.audio_file else None,
            'cover_url': m.cover_image.url if m.cover_image else None,
            'duration': m.duration,
            'language': m.language,
        } for m in tracks]
        return JsonResponse({'music': data, 'source': 'fallback'})


class StoryReactionsJSONView(LoginRequiredMixin, View):
    def get(self, request, story_id):
        story = get_object_or_404(Story, id=story_id)
        reactions = StoryReaction.objects.filter(story=story)
        emoji_counts = {}
        for r in reactions:
            emoji_counts[r.emoji] = emoji_counts.get(r.emoji, 0) + 1
        return JsonResponse({'reactions': emoji_counts})


class StoryPollResultsJSONView(LoginRequiredMixin, View):
    def get(self, request, story_id):
        story = get_object_or_404(Story, id=story_id)
        poll = getattr(story, 'poll', None)
        if not poll:
            return JsonResponse({'error': 'No poll'}, status=404)
        total = poll.total_votes() or 1
        opt1_pct = round(poll.votes.filter(option=1).count() / total * 100)
        opt2_pct = round(poll.votes.filter(option=2).count() / total * 100)
        opt3_pct = round(poll.votes.filter(option=3).count() / total * 100) if poll.option3 else 0
        opt4_pct = round(poll.votes.filter(option=4).count() / total * 100) if poll.option4 else 0
        user_vote = None
        try:
            user_vote = poll.votes.get(user=request.user).option
        except StoryPollVote.DoesNotExist:
            pass
        return JsonResponse({
            'total': poll.total_votes(),
            'opt1_pct': opt1_pct, 'opt2_pct': opt2_pct,
            'opt3_pct': opt3_pct, 'opt4_pct': opt4_pct,
            'option1': poll.option1, 'option2': poll.option2,
            'option3': poll.option3, 'option4': poll.option4,
            'user_vote': user_vote,
        })


# ====== ADVANCED REEL VIEWS ======

class ReelAudioJSONView(LoginRequiredMixin, View):
    def get(self, request):
        audio = ReelAudio.objects.all()
        data = [{
            'id': a.id, 'title': a.title, 'artist': a.artist,
            'audio_url': a.audio_file.url if a.audio_file else None,
            'cover_url': a.cover_image.url if a.cover_image else None,
            'duration': a.duration,
        } for a in audio]
        return JsonResponse({'audio': data})


# ====== CAMERA VIEWS ======

class CameraView(LoginRequiredMixin, TemplateView):
    template_name = 'posts/reel_camera.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filters'] = CameraFilter.objects.filter(is_active=True)
        context['effects'] = CameraEffect.objects.filter(is_active=True)
        context['reel_audio'] = ReelAudio.objects.all()
        return context


class CameraFilterJSONView(LoginRequiredMixin, View):
    def get(self, request):
        filters = CameraFilter.objects.filter(is_active=True)
        data = [{
            'id': f.id, 'name': f.name,
            'css_filter': f.css_filter,
            'preview_url': f.preview_image.url if f.preview_image else None,
        } for f in filters]
        return JsonResponse({'filters': data})


class CameraEffectJSONView(LoginRequiredMixin, View):
    def get(self, request):
        effects = CameraEffect.objects.filter(is_active=True)
        data = [{
            'id': e.id, 'name': e.name,
            'effect_type': e.effect_type,
            'css_filter': e.css_filter,
            'overlay_html': e.overlay_html,
            'overlay_css': e.overlay_css,
            'icon': e.icon,
        } for e in effects]
        return JsonResponse({'effects': data})
