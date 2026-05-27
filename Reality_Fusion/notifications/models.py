from django.db import models
from django.conf import settings


class Notification(models.Model):
    LIKE = 'like'
    COMMENT = 'comment'
    FOLLOW = 'follow'
    SHARE = 'share'
    REEL_LIKE = 'reel_like'
    REEL_COMMENT = 'reel_comment'
    REEL_SHARE = 'reel_share'
    STORY_REPLY = 'story_reply'
    STORY_VIEW = 'story_view'
    STORY_LIKE = 'story_like'
    STORY_MENTION = 'story_mention'
    VERB_CHOICES = [
        (LIKE, 'liked your post'),
        (COMMENT, 'commented on your post'),
        (FOLLOW, 'started following you'),
        (SHARE, 'shared your post'),
        (REEL_LIKE, 'liked your reel'),
        (REEL_COMMENT, 'commented on your reel'),
        (REEL_SHARE, 'shared your reel'),
        (STORY_REPLY, 'replied to your story'),
        (STORY_VIEW, 'viewed your story'),
        (STORY_LIKE, 'liked your story'),
        (STORY_MENTION, 'mentioned you in a story'),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='notifications'
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='actor_notifications'
    )
    verb = models.CharField(max_length=20, choices=VERB_CHOICES)
    target_post = models.ForeignKey(
        'posts.Post', on_delete=models.CASCADE, null=True, blank=True
    )
    target_reel = models.ForeignKey(
        'posts.Reel', on_delete=models.CASCADE, null=True, blank=True
    )
    target_story = models.ForeignKey(
        'posts.Story', on_delete=models.CASCADE, null=True, blank=True
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.actor.email} {self.get_verb_display()} → {self.recipient.email}"
