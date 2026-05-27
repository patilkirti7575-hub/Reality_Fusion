import os
from django.db import models
from django.conf import settings
from users.models import CustomUser
from django.utils import timezone
from datetime import timedelta
import json


class Hashtag(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"#{self.name}"


class HashtagTrend(models.Model):
    hashtag = models.ForeignKey(Hashtag, on_delete=models.CASCADE, related_name='trends')
    count = models.PositiveIntegerField(default=0)
    date = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('hashtag', 'date')
        ordering = ['-count']

    def __str__(self):
        return f"#{self.hashtag.name}: {self.count}"


class Post(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField()
    image = models.ImageField(upload_to='posts/', blank=True, null=True)
    video = models.FileField(upload_to='posts/videos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    likes = models.ManyToManyField(CustomUser, related_name='liked_posts', blank=True)
    hashtags = models.ManyToManyField(Hashtag, related_name='posts', blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Post by {self.user.email}"

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment on {self.post.id}"

class Story(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='stories')
    image = models.ImageField(upload_to='stories/', blank=True, null=True)
    video = models.FileField(upload_to='stories/videos/', blank=True, null=True)
    caption = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    audio = models.ForeignKey('StoryMusic', on_delete=models.SET_NULL, null=True, blank=True, related_name='stories')
    location_name = models.CharField(max_length=200, blank=True)
    location_lat = models.FloatField(null=True, blank=True)
    location_lng = models.FloatField(null=True, blank=True)
    text_overlay_data = models.TextField(blank=True)  # JSON: [{text, color, font, size, x, y, rotation}]
    allow_reactions = models.BooleanField(default=True)
    allow_music = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def view_count(self):
        return self.views.count()

    @property
    def like_count(self):
        return self.likes.count()

    def add_view(self, user):
        view, created = StoryView.objects.get_or_create(story=self, user=user)
        return created

    def __str__(self):
        return f"Story by {self.user.email}"

class StoryView(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='views')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='story_views')
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('story', 'user')

    def __str__(self):
        return f"{self.user.email} viewed {self.story}"


class MutedStory(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='story_muted_users')
    muted_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='muted_by_users')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'muted_user')

    def __str__(self):
        return f"{self.user.email} muted {self.muted_user.email}"


class StoryLike(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='story_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('story', 'user')

    def __str__(self):
        return f"{self.user.email} liked {self.story}"


class StoryMention(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='mentions')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='story_mentions')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('story', 'user')

    def __str__(self):
        return f"{self.user.email} mentioned in {self.story}"


class Reel(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reels')
    video = models.FileField(upload_to='reels/')
    caption = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    likes = models.ManyToManyField(CustomUser, related_name='liked_reels', blank=True)
    views = models.PositiveIntegerField(default=0)
    hashtags = models.ManyToManyField(Hashtag, related_name='reels', blank=True)
    audio = models.ForeignKey('ReelAudio', on_delete=models.SET_NULL, null=True, blank=True, related_name='reels')

    class Meta:
        ordering = ['-created_at']

    @property
    def share_count(self):
        return self.shares.count()

    @property
    def comment_count(self):
        return self.comments.count()

    @property
    def video_exists(self):
        try:
            return bool(self.video and os.path.isfile(os.path.join(settings.MEDIA_ROOT, self.video.name)))
        except (ValueError, TypeError):
            return False

    def __str__(self):
        return f"Reel by {self.user.email}"


class ReelComment(models.Model):
    reel = models.ForeignKey(Reel, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment on reel {self.reel.id}"


class SavedPost(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='saved_posts')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='saved_by')
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')
        ordering = ['-saved_at']

    def __str__(self):
        return f"{self.user.email} saved post {self.post.id}"


class SavedReel(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='saved_reels')
    reel = models.ForeignKey(Reel, on_delete=models.CASCADE, related_name='saved_by')
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'reel')
        ordering = ['-saved_at']

    def __str__(self):
        return f"{self.user.email} saved reel {self.reel.id}"


class ReelShare(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reel_shares')
    reel = models.ForeignKey(Reel, on_delete=models.CASCADE, related_name='shares')
    shared_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-shared_at']

    def __str__(self):
        return f"{self.user.email} shared reel {self.reel.id}"


class TaggedItem(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='tagged_items')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True, related_name='tagged_users')
    reel = models.ForeignKey(Reel, on_delete=models.CASCADE, null=True, blank=True, related_name='tagged_users')
    tagged_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='tags_given')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} tagged in {self.post or self.reel}"


class Report(models.Model):
    REASON_CHOICES = [
        ('spam', 'Spam'),
        ('harassment', 'Harassment'),
        ('nudity', 'Nudity/Sexual content'),
        ('violence', 'Violence/Hate speech'),
        ('copyright', 'Copyright violation'),
        ('other', 'Other'),
    ]
    reporter = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reports')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True, related_name='reports')
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True, related_name='reports')
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    description = models.TextField(blank=True)
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Report by {self.reporter.email}"


class StoryHighlight(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='highlights')
    title = models.CharField(max_length=100)
    cover = models.ImageField(upload_to='highlights/covers/', blank=True, null=True)
    stories = models.ManyToManyField(Story, related_name='highlights', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email}'s highlight: {self.title}"


# ====== ADVANCED STORY FEATURES ======

class StoryMusic(models.Model):
    title = models.CharField(max_length=100)
    artist = models.CharField(max_length=100, blank=True)
    audio_file = models.FileField(upload_to='story_music/')
    cover_image = models.ImageField(upload_to='story_music/covers/', blank=True, null=True)
    duration = models.PositiveIntegerField(default=30, help_text='Duration in seconds')
    language = models.CharField(max_length=50, blank=True, default='', help_text='e.g. Hindi, English, Korean, Punjabi')
    lyrics = models.TextField(blank=True, default='', help_text='Song lyrics for display on story')

    def __str__(self):
        return f"{self.title} - {self.artist}"


class StoryPoll(models.Model):
    story = models.OneToOneField(Story, on_delete=models.CASCADE, related_name='poll')
    question = models.CharField(max_length=200)
    option1 = models.CharField(max_length=100)
    option2 = models.CharField(max_length=100)
    option3 = models.CharField(max_length=100, blank=True)
    option4 = models.CharField(max_length=100, blank=True)

    def total_votes(self):
        return self.votes.count()

    def __str__(self):
        return f"Poll: {self.question}"


class StoryPollVote(models.Model):
    poll = models.ForeignKey(StoryPoll, on_delete=models.CASCADE, related_name='votes')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    option = models.PositiveSmallIntegerField()
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('poll', 'user')

    def __str__(self):
        return f"{self.user.email} voted option {self.option}"


class StoryReaction(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    emoji = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('story', 'user', 'emoji')

    def __str__(self):
        return f"{self.user.email} reacted {self.emoji}"


# ====== ADVANCED REEL FEATURES ======

class ReelAudio(models.Model):
    title = models.CharField(max_length=100)
    artist = models.CharField(max_length=100, blank=True)
    audio_file = models.FileField(upload_to='reel_audio/')
    cover_image = models.ImageField(upload_to='reel_audio/covers/', blank=True, null=True)
    duration = models.PositiveIntegerField(default=30, help_text='Duration in seconds')

    def __str__(self):
        return f"{self.title} - {self.artist}"


# ====== CAMERA FILTERS ======

class CameraFilter(models.Model):
    name = models.CharField(max_length=50)
    css_filter = models.CharField(max_length=200, help_text='CSS filter string e.g. grayscale(100%)')
    preview_image = models.ImageField(upload_to='filters/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name


class CameraEffect(models.Model):
    EFFECT_TYPES = [
        ('beauty', 'Beauty Filter'),
        ('ar', 'AR Effect'),
        ('video', 'Video Effect'),
    ]
    name = models.CharField(max_length=50)
    effect_type = models.CharField(max_length=20, choices=EFFECT_TYPES, default='beauty')
    css_filter = models.CharField(max_length=300, blank=True, default='', help_text='CSS filter string')
    overlay_html = models.TextField(blank=True, default='', help_text='HTML for AR overlay element')
    overlay_css = models.TextField(blank=True, default='', help_text='CSS for AR overlay')
    icon = models.CharField(max_length=10, blank=True, default='', help_text='Emoji icon')
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['effect_type', 'order']

    def __str__(self):
        return f"[{self.effect_type}] {self.name}"
