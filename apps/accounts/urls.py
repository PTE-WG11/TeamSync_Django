"""
Accounts URL configuration.
"""
from django.urls import path
from . import views
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    # Authentication
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('refresh/', views.CustomTokenRefreshView.as_view(), name='token-refresh'),
    path('me/', views.CurrentUserView.as_view(), name='current-user'),
    path('me/update/', views.UpdateCurrentUserView.as_view(), name='update-current-user'),
    
    # Visitor
    path('visitor/status/', views.visitor_status, name='visitor-status'),
]
