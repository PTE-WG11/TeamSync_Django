"""
Team management URL configuration.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Team Members
    path('members/', views.TeamMemberListView.as_view(), name='team-members'),
    path('invite/', views.InviteMemberView.as_view(), name='invite-member'),
    path('check-user/', views.CheckUserInviteView.as_view(), name='check-user-invite'),
    path('members/<int:pk>/role/', views.ChangeMemberRoleView.as_view(), name='change-member-role'),
    path('members/<int:pk>/', views.RemoveMemberView.as_view(), name='remove-member'),
]
