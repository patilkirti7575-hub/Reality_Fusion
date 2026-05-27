from django.contrib import admin
from .models import (
    Post, Comment, Story, StoryView, MutedStory, StoryLike, StoryMention, StoryHighlight,
    StoryMusic, StoryPoll, StoryPollVote, StoryReaction, ReelAudio, CameraFilter
)

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'content_preview', 'created_at')
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'user', 'content_preview')
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content

@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'caption_preview', 'view_count', 'created_at', 'expires_at')
    def caption_preview(self, obj):
        return obj.caption[:50] + '...' if len(obj.caption) > 50 else obj.caption

@admin.register(StoryView)
class StoryViewAdmin(admin.ModelAdmin):
    list_display = ('id', 'story', 'user', 'viewed_at')
    list_filter = ('viewed_at',)

@admin.register(MutedStory)
class MutedStoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'muted_user', 'created_at')

@admin.register(StoryLike)
class StoryLikeAdmin(admin.ModelAdmin):
    list_display = ('id', 'story', 'user', 'created_at')

@admin.register(StoryMention)
class StoryMentionAdmin(admin.ModelAdmin):
    list_display = ('id', 'story', 'user', 'created_at')

@admin.register(StoryHighlight)
class StoryHighlightAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'created_at')

@admin.register(StoryMusic)
class StoryMusicAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'artist', 'duration')

@admin.register(StoryPoll)
class StoryPollAdmin(admin.ModelAdmin):
    list_display = ('id', 'story', 'question')

@admin.register(StoryPollVote)
class StoryPollVoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'poll', 'user', 'option')

@admin.register(StoryReaction)
class StoryReactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'story', 'user', 'emoji')

@admin.register(ReelAudio)
class ReelAudioAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'artist', 'duration')

@admin.register(CameraFilter)
class CameraFilterAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'css_filter', 'is_active', 'order')
