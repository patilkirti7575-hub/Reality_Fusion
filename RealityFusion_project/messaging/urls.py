from django.urls import path
from .views import (
    ChatView, MessageListView, ChatListView, SharePostView,
    MessageDeleteView, MessageReactionView, GifSearchView, TypingStatusView
)

urlpatterns = [
    path('', ChatListView.as_view(), name='chat_list'),
    path('chat/<int:user_id>/', ChatView.as_view(), name='chat'),
    path('api/messages/<int:user_id>/', MessageListView.as_view(), name='message_list'),
    path('api/share/', SharePostView.as_view(), name='share_post'),
    path('api/delete/<int:message_id>/', MessageDeleteView.as_view(), name='message_delete'),
    path('api/react/<int:message_id>/', MessageReactionView.as_view(), name='message_react'),
    path('api/gifs/', GifSearchView.as_view(), name='gif_search'),
    path('api/typing/<int:user_id>/', TypingStatusView.as_view(), name='typing_status'),
]
