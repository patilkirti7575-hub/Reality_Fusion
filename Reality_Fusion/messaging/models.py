from django.db import models
from users.models import CustomUser


class Message(models.Model):
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField(blank=True, default='')
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    is_delivered = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    gif_url = models.URLField(max_length=500, blank=True, default='')
    shared_post = models.ForeignKey('posts.Post', on_delete=models.SET_NULL, null=True, blank=True, related_name='shared_in_messages')
    shared_reel = models.ForeignKey('posts.Reel', on_delete=models.SET_NULL, null=True, blank=True, related_name='shared_in_messages')
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    image = models.ImageField(upload_to='chat_images/', blank=True, null=True)
    video = models.FileField(upload_to='chat_videos/', blank=True, null=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Message from {self.sender.email}"


class MessageReaction(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    emoji = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('message', 'user', 'emoji')

    def __str__(self):
        return f"{self.user.email} reacted {self.emoji}"


class DeletedMessage(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='deleted_records')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    deleted_for_everyone = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('message', 'user')

    def __str__(self):
        return f"Deleted {self.message.id} for {self.user.email}"
