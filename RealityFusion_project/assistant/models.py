from django.db import models
from users.models import CustomUser


class AIChat(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='ai_chats')
    title = models.CharField(max_length=255, blank=True, default='New Chat')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class AIChatMessage(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]
    chat = models.ForeignKey(AIChat, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role}: {self.content[:60]}"


class AIContent(models.Model):
    TYPE_CHOICES = [
        ('caption', 'Caption'),
        ('hashtag', 'Hashtag'),
        ('bio', 'Bio Suggestion'),
        ('comment', 'Comment Reply'),
        ('idea', 'Content Idea'),
        ('reel_script', 'Reel Script'),
        ('reel_hook', 'Reel Hook'),
        ('story_idea', 'Story Idea'),
        ('music_suggestion', 'Music Suggestion'),
        ('translation', 'Translation'),
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='ai_contents')
    content_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    prompt = models.TextField()
    result = models.TextField()
    language = models.CharField(max_length=50, blank=True, default='English')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.content_type}"


class AIHistory(models.Model):
    ACTION_CHOICES = [
        ('chat', 'Chat'),
        ('generate', 'Content Generation'),
        ('enhance', 'Enhancement'),
        ('translate', 'Translation'),
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='ai_history')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    prompt = models.TextField(blank=True, default='')
    result = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'AI histories'

    def __str__(self):
        return f"{self.user.username} - {self.action}"
