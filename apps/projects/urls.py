"""
Projects URL configuration.
"""
from django.urls import path
from . import views
from . import document_views

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
    
    # =============================================================================
    # Document URLs
    # =============================================================================
    
    # Folders
    path('<int:project_id>/folders/', document_views.FolderListCreateView.as_view(), name='folder-list-create'),
    path('folders/<int:folder_id>/', document_views.FolderUpdateDeleteView.as_view(), name='folder-update-delete'),
    
    # Documents
    path('<int:project_id>/documents/', document_views.DocumentListView.as_view(), name='document-list'),
    path('documents/<int:document_id>/', document_views.DocumentDetailView.as_view(), name='document-detail'),
    path('documents/<int:document_id>/delete/', document_views.DocumentDeleteView.as_view(), name='document-delete'),
    path('documents/<int:document_id>/move/', document_views.DocumentMoveView.as_view(), name='document-move'),
    
    # Markdown
    path('<int:project_id>/documents/markdown/', document_views.MarkdownCreateView.as_view(), name='markdown-create'),
    path('documents/<int:document_id>/content/', document_views.MarkdownUpdateView.as_view(), name='markdown-update'),
    
    # File Upload (Presigned URL)
    path('<int:project_id>/documents/upload-url/', document_views.DocumentUploadUrlView.as_view(), name='document-upload-url'),
    path('<int:project_id>/documents/confirm-upload/', document_views.DocumentConfirmUploadView.as_view(), name='document-confirm-upload'),
    path('documents/<int:document_id>/download/', document_views.DocumentDownloadUrlView.as_view(), name='document-download'),
    
    # Comments
    path('documents/<int:document_id>/comments/', document_views.CommentListCreateView.as_view(), name='comment-list-create'),
    path('comments/<int:comment_id>/', document_views.CommentDeleteView.as_view(), name='comment-delete'),
    
    # Statistics
    path('<int:project_id>/documents/statistics/', document_views.DocumentStatisticsView.as_view(), name='document-statistics'),
]
