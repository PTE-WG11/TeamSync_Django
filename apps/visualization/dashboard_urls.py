"""
Dashboard URL configuration.
"""
from django.urls import path
from . import dashboard_views

urlpatterns = [
    path('member/', dashboard_views.MemberDashboardView.as_view(), name='member-dashboard'),
    path('admin/', dashboard_views.AdminDashboardView.as_view(), name='admin-dashboard'),
]
