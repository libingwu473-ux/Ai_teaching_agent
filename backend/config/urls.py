from django.contrib import admin
from django.urls import path, include

from apps.dify_integration.views_config import dify_config_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.users.urls')),
    path('api/chat/', include('apps.dify_integration.urls')),
    path('api/logs/', include('apps.chat_logs.urls')),
    path('api/teacher/', include('apps.scoring.urls')),
    path('api/teacher/dify-config/', dify_config_view, name='teacher-dify-config'),
]
