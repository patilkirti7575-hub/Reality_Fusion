"""
URL patterns for users app
"""
from django.urls import path
from .views import (
    RegisterView, ProfileView,
    FollowView, UnfollowView, FollowersJSONView, FollowingJSONView,
    UserListView, UserSearchJSON, FollowingListView,
    # Settings
    SettingsHomeView, SettingsProfileEditView, SettingsChangePasswordView,
    SettingsPrivacyView, SettingsNotificationsView, SettingsSecurityView,
    SettingsAppearanceView, SettingsSavedContentView, SettingsBlockedUsersView,
    SettingsStoryView, SettingsMessagingView,
    # Settings Actions
    TogglePrivateView, ToggleActiveStatusView,
    UnblockUserView, RemoveRestrictedUserView, UnmuteUserView,
    RemoveCloseFriendView, AddCloseFriendView,
    LogoutAllDevicesView, ClearLoginActivityView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('profile/<int:user_id>/', ProfileView.as_view(), name='profile'),
    path('profile/', ProfileView.as_view(), name='my_profile'),
    path('profile/edit/', SettingsProfileEditView.as_view(), name='profile_edit'),
    path('users/', UserListView.as_view(), name='user_list'),
    path('following/', FollowingListView.as_view(), name='following_list'),
    path('search/', UserSearchJSON.as_view(), name='user_search_json'),
    path('follow/<int:user_id>/', FollowView.as_view(), name='follow_user'),
    path('unfollow/<int:user_id>/', UnfollowView.as_view(), name='unfollow_user'),
    path('followers/<int:user_id>/', FollowersJSONView.as_view(), name='followers_json'),
    path('following/<int:user_id>/', FollowingJSONView.as_view(), name='following_json'),

    # ===== SETTINGS PAGES =====
    path('settings/', SettingsHomeView.as_view(), name='settings'),
    path('settings/edit/', SettingsProfileEditView.as_view(), name='settings_profile_edit'),
    path('settings/password/', SettingsChangePasswordView.as_view(), name='settings_change_password'),
    path('settings/privacy/', SettingsPrivacyView.as_view(), name='settings_privacy'),
    path('settings/notifications/', SettingsNotificationsView.as_view(), name='settings_notifications'),
    path('settings/security/', SettingsSecurityView.as_view(), name='settings_security'),
    path('settings/appearance/', SettingsAppearanceView.as_view(), name='settings_appearance'),
    path('settings/saved/', SettingsSavedContentView.as_view(), name='settings_saved_content'),
    path('settings/blocked/', SettingsBlockedUsersView.as_view(), name='settings_blocked_users'),
    path('settings/story/', SettingsStoryView.as_view(), name='settings_story'),
    path('settings/messaging/', SettingsMessagingView.as_view(), name='settings_messaging'),

    # ===== SETTINGS ACTIONS =====
    path('settings/toggle-private/', TogglePrivateView.as_view(), name='toggle_private'),
    path('settings/toggle-active-status/', ToggleActiveStatusView.as_view(), name='toggle_active_status'),
    path('settings/unblock/<int:user_id>/', UnblockUserView.as_view(), name='unblock_user'),
    path('settings/remove-restricted/<int:user_id>/', RemoveRestrictedUserView.as_view(), name='remove_restricted_user'),
    path('settings/unmute/<int:user_id>/', UnmuteUserView.as_view(), name='unmute_user'),
    path('settings/remove-close-friend/<int:user_id>/', RemoveCloseFriendView.as_view(), name='remove_close_friend'),
    path('settings/add-close-friend/<int:user_id>/', AddCloseFriendView.as_view(), name='add_close_friend'),
    path('settings/logout-all-devices/', LogoutAllDevicesView.as_view(), name='logout_all_devices'),
    path('settings/clear-login-activity/', ClearLoginActivityView.as_view(), name='clear_login_activity'),
]
