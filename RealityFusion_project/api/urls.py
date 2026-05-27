from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'profiles', views.ProfileViewSet, basename='profile')
router.register(r'posts', views.PostViewSet)
router.register(r'reels', views.ReelViewSet)
router.register(r'stories', views.StoryViewSet)
router.register(r'highlights', views.StoryHighlightViewSet, basename='highlight')
router.register(r'saved', views.SavedPostViewSet, basename='saved')
router.register(r'comments', views.CommentViewSet)
router.register(r'hashtags', views.HashtagViewSet)
router.register(r'trending', views.TrendingHashtagsViewSet, basename='trending')
router.register(r'messages', views.MessageViewSet, basename='message')
router.register(r'notifications', views.NotificationViewSet, basename='notification')
router.register(r'follows', views.FollowViewSet)
router.register(r'feed', views.FeedViewSet, basename='feed')
router.register(r'explore', views.ExploreViewSet, basename='explore')
router.register(r'search', views.SearchViewSet, basename='search')

urlpatterns = [
    path('', include(router.urls)),
    path('register/', views.RegisterView.as_view(), name='api_register'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
