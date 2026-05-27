"""/api/admin/ 路由：仅 admin 角色可访问。"""
from django.urls import path

from apps.dify_integration.views_config import dify_config_view
from . import views_admin

urlpatterns = [
    path('dify-config/', dify_config_view, name='admin-dify-config'),
    path('teachers/', views_admin.admin_teachers_view, name='admin-teachers'),
    path('teachers/<int:teacher_id>/', views_admin.admin_teacher_detail_view, name='admin-teacher-detail'),
    path('teachers/<int:teacher_id>/reset-password/', views_admin.admin_teacher_reset_password_view, name='admin-teacher-reset-password'),
    path('majors/', views_admin.admin_majors_view, name='admin-majors'),
    path('majors/<int:major_id>/', views_admin.admin_major_detail_view, name='admin-major-detail'),
]
