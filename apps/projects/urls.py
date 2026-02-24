"""
Projects URL configuration.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Project CRUD
    path('', views.ProjectListView.as_view(), name='project-list'),
    path('create/', views.ProjectCreateView.as_view(), name='project-create'),
    path('<int:pk>/', views.ProjectDetailView.as_view(), name='project-detail'),
    path('<int:pk>/update/', views.ProjectUpdateView.as_view(), name='project-update'),
    
    # Archive/Unarchive
    path('<int:pk>/archive/', views.ProjectArchiveView.as_view(), name='project-archive'),
    path('<int:pk>/unarchive/', views.ProjectUnarchiveView.as_view(), name='project-unarchive'),
    
    # Delete (super admin only)
    path('<int:pk>/delete/', views.ProjectDeleteView.as_view(), name='project-delete'),
    
    # Progress
    path('<int:pk>/progress/', views.ProjectProgressView.as_view(), name='project-progress'),
    
    # Members
    path('<int:pk>/members/', views.ProjectMemberUpdateView.as_view(), name='project-members'),
]
