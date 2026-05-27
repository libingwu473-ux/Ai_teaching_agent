from django.urls import path
from . import views

urlpatterns = [
    path('send/', views.chat_send_view, name='chat-send'),
    path('stop/', views.chat_stop_view, name='chat-stop'),
    path('conversations/', views.conversation_list_view, name='chat-conversations'),
    path('conversations/<int:conv_id>/', views.conversation_detail_view, name='chat-conversation-detail'),
    path('conversations/<int:conv_id>/messages/', views.conversation_messages_view, name='chat-conversation-messages'),
    path('conversations/<int:conv_id>/delete/', views.conversation_delete_view, name='chat-conversation-delete'),
    path('upload/', views.file_upload_view, name='chat-upload'),
    path('sync/', views.sync_trigger_view, name='chat-sync'),
]
