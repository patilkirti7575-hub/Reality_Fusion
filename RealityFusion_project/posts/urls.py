"""
URL patterns for posts app
"""
from django.urls import path
from .views import (
    FeedView, ExploreView, ReelsView, PostCreateView, LikeView, CommentView,
    PostDeleteView, SavePostView, TaggedView,
    StoryUploadView, StoryJSONView, StoryViewedView, StoryViewersJSONView, StoryLikeView, StoryDeleteView, StoryViewerView,
    ReelCreateView, ReelLikeView, ReelDeleteView, ReelCommentView, ReelCommentsJSONView, ReelSaveView, ReelShareView, ReelDetailView, SavedReelsView,
    StoryEditorView, StorySaveAdvancedView, StoryReactView, StoryPollVoteView, StoryMuteView,
    StoryMusicJSONView, StoryMusicSearchView, StoryReactionsJSONView, StoryPollResultsJSONView,
    ReelAudioJSONView, CameraView, CameraFilterJSONView, CameraEffectJSONView
)

urlpatterns = [
    path('', FeedView.as_view(), name='feed'),
    path('explore/', ExploreView.as_view(), name='explore'),
    path('reels/', ReelsView.as_view(), name='reels'),
    path('post/create/', PostCreateView.as_view(), name='post_create'),
    path('post/<int:post_id>/like/', LikeView.as_view(), name='like_post'),
    path('post/<int:post_id>/comment/', CommentView.as_view(), name='comment_post'),
    path('post/<int:post_id>/delete/', PostDeleteView.as_view(), name='delete_post'),
    path('post/<int:post_id>/save/', SavePostView.as_view(), name='save_post'),
    # Reel routes
    path('reel/upload/', ReelCreateView.as_view(), name='reel_upload'),
    path('reel/<int:reel_id>/like/', ReelLikeView.as_view(), name='like_reel'),
    path('reel/<int:reel_id>/comment/', ReelCommentView.as_view(), name='reel_comment'),
    path('reel/<int:reel_id>/comments/', ReelCommentsJSONView.as_view(), name='reel_comments_json'),
    path('reel/<int:reel_id>/save/', ReelSaveView.as_view(), name='reel_save'),
    path('reel/<int:reel_id>/share/', ReelShareView.as_view(), name='reel_share'),
    path('reel/<int:reel_id>/delete/', ReelDeleteView.as_view(), name='delete_reel'),
    path('reel/<int:reel_id>/', ReelDetailView.as_view(), name='reel_detail'),
    # Tagged routes
    path('tagged/', TaggedView.as_view(), name='tagged'),
    path('tagged/<int:user_id>/', TaggedView.as_view(), name='tagged_user'),
    # Story routes
    path('story/upload/', StoryUploadView.as_view(), name='story_upload'),
    path('story/json/<int:user_id>/', StoryJSONView.as_view(), name='story_json'),
    path('story/<int:story_id>/viewed/', StoryViewedView.as_view(), name='story_viewed'),
    path('story/<int:user_id>/mute/', StoryMuteView.as_view(), name='story_mute'),
    path('story/<int:story_id>/viewers/', StoryViewersJSONView.as_view(), name='story_viewers'),
    path('story/<int:story_id>/like/', StoryLikeView.as_view(), name='story_like'),
    path('story/<int:story_id>/delete/', StoryDeleteView.as_view(), name='story_delete'),
    path('story/<int:story_id>/', StoryViewerView.as_view(), name='story_view'),
    path('story/viewers/<int:story_id>/', StoryViewerView.as_view(), name='story_viewers_page'),
    path('reels/saved/', SavedReelsView.as_view(), name='saved_reels'),
    # Advanced story routes
    path('story/editor/', StoryEditorView.as_view(), name='story_editor'),
    path('story/save-advanced/', StorySaveAdvancedView.as_view(), name='story_save_advanced'),
    path('story/<int:story_id>/react/', StoryReactView.as_view(), name='story_react'),
    path('story/<int:story_id>/vote/', StoryPollVoteView.as_view(), name='story_vote'),
    path('api/story/music/', StoryMusicJSONView.as_view(), name='story_music_json'),
    path('api/story/music/search/', StoryMusicSearchView.as_view(), name='story_music_search'),
    path('story/<int:story_id>/reactions/', StoryReactionsJSONView.as_view(), name='story_reactions_json'),
    path('story/<int:story_id>/poll-results/', StoryPollResultsJSONView.as_view(), name='story_poll_results'),
    # Advanced reel routes
    path('api/reel/audio/', ReelAudioJSONView.as_view(), name='reel_audio_json'),
    # Camera routes
    path('camera/', CameraView.as_view(), name='camera'),
    path('api/filters/', CameraFilterJSONView.as_view(), name='camera_filters_json'),
    path('api/effects/', CameraEffectJSONView.as_view(), name='camera_effects_json'),
]
