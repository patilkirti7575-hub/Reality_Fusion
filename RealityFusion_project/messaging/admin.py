from django.contrib import admin
from .models import Message, MessageReaction, DeletedMessage

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'receiver', 'content_preview', 'is_deleted', 'timestamp')
    list_filter = ('is_deleted', 'is_read')
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content

@admin.register(MessageReaction)
class MessageReactionAdmin(admin.ModelAdmin):
    list_display = ('message', 'user', 'emoji', 'created_at')

@admin.register(DeletedMessage)
class DeletedMessageAdmin(admin.ModelAdmin):
    list_display = ('message', 'user', 'deleted_for_everyone', 'deleted_at')
