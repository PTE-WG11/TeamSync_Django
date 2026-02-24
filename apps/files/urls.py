"""
Files URL configuration.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Upload
    path('tasks/<int:task_id>/upload-url/', views.UploadUrlView.as_view(), name='upload-url'),
    path('tasks/<int:task_id>/attachments/', views.ConfirmUploadView.as_view(), name='confirm-upload'),
    
    # Download
    path('attachments/<int:attachment_id>/download-url/', views.DownloadUrlView.as_view(), name='download-url'),
    
    # Delete
    path('attachments/<int:attachment_id>/', views.AttachmentDeleteView.as_view(), name='attachment-delete'),
]
