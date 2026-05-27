from django.urls import path
from . import views

urlpatterns = [
    path('sessions/', views.my_sessions_view, name='logs-sessions'),
    path('sessions/<int:session_id>/', views.session_logs_view, name='logs-session-detail'),
]
