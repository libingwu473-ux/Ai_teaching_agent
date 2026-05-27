from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.users.urls')),
    path('api/admin/', include('apps.users.urls_admin')),
    path('api/chat/', include('apps.dify_integration.urls')),
    path('api/logs/', include('apps.chat_logs.urls')),
    path('api/teacher/', include('apps.scoring.urls')),
    path('api/teacher/', include('apps.users.urls_teacher')),
]
