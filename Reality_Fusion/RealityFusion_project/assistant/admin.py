from django.contrib import admin
from .models import AIChat, AIChatMessage, AIContent, AIHistory

@admin.register(AIChat)
class AIChatAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'title', 'created_at']

@admin.register(AIChatMessage)
class AIChatMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'chat', 'role', 'short_content', 'created_at']
    list_filter = ['role']

    def short_content(self, obj):
        return obj.content[:60] if obj.content else ''

@admin.register(AIContent)
class AIContentAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'content_type', 'created_at']

@admin.register(AIHistory)
class AIHistoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'action', 'created_at']
