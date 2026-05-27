from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='auth-login'),
    path('profile/', views.profile_view, name='auth-profile'),
    path('change-password/', views.change_password_view, name='auth-change-password'),
]
