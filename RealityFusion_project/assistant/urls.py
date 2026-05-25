from django.urls import path
from .views import (
    AIAssistantView, AIChatSendView, AIChatHistoryView, AIChatDeleteView,
    AIGenerateView, AIHistoryView, AIChatsListView,
)

urlpatterns = [
    path('', AIAssistantView.as_view(), name='ai_assistant'),
    path('api/chat/', AIChatSendView.as_view(), name='ai_chat_send'),
    path('api/chat/<int:chat_id>/', AIChatHistoryView.as_view(), name='ai_chat_history'),
    path('api/chat/<int:chat_id>/delete/', AIChatDeleteView.as_view(), name='ai_chat_delete'),
    path('api/chats/', AIChatsListView.as_view(), name='ai_chats_list'),
    path('api/generate/', AIGenerateView.as_view(), name='ai_generate'),
    path('api/history/', AIHistoryView.as_view(), name='ai_history'),
]
