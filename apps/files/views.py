"""
Files views for TeamSync.
"""
from rest_framework import generics, status, permissions
from rest_framework.response import Response

from apps.tasks.models import Task, TaskAttachment
from apps.tasks.serializers import TaskAttachmentSerializer
from config.permissions import IsTeamMember, IsTaskAssigneeOrAdmin
from config.exceptions import ValidationError, ResourceNotFound

from .storage import StorageFactory, BaseStorage


class UploadUrlView(generics.GenericAPIView):
    """Get presigned upload URL."""
    permission_classes = [IsTeamMember]
    
    def post(self, request, task_id, *args, **kwargs):
        """Get upload URL for a task."""
        try:
            task = Task.objects.get(id=task_id)
        except Task.DoesNotExist:
            raise ResourceNotFound('任务不存在')
        
        # Check permission - only task assignee or admin can upload
        user = request.user
        if not (user.is_super_admin or user.is_team_admin or task.assignee_id == user.id):
            raise ValidationError('无权上传附件', code=3004)
        
        # Check if project is archived
        if task.project.is_archived:
            raise ValidationError('项目已归档，无法上传附件', code=3006)
        
        # Get file info
        file_name = request.data.get('file_name')
        file_type = request.data.get('file_type')
        file_size = request.data.get('file_size')
        
        if not file_name or not file_type or not file_size:
            raise ValidationError('请提供文件名、类型和大小')
        
        # Validate file
        try:
            from .storage import BaseStorage
            BaseStorage.validate_file(file_name, file_size, file_type)
        except ValueError as e:
            raise ValidationError(str(e), code=5002)
        
        # Generate file key
        file_key = BaseStorage.generate_file_key(task_id, file_name)
        
        # Get storage and generate URL
        try:
            storage = StorageFactory.get_storage()
            upload_url = storage.get_upload_url(file_key, file_type)
        except Exception as e:
            raise ValidationError(f'生成上传URL失败: {e}', code=5001)
        
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'upload_url': upload_url,
                'file_key': file_key,
                'expires_in': 300
            }
        })


class ConfirmUploadView(generics.GenericAPIView):
    """Confirm file upload and save attachment record."""
    permission_classes = [IsTeamMember]
    
    def post(self, request, task_id, *args, **kwargs):
        """Confirm upload and create attachment record."""
        try:
            task = Task.objects.get(id=task_id)
        except Task.DoesNotExist:
            raise ResourceNotFound('任务不存在')
        
        # Check permission
        user = request.user
        if not (user.is_super_admin or user.is_team_admin or task.assignee_id == user.id):
            raise ValidationError('无权上传附件', code=3004)
        
        # Get file info
        file_key = request.data.get('file_key')
        file_name = request.data.get('file_name')
        file_type = request.data.get('file_type')
        file_size = request.data.get('file_size')
        
        if not all([file_key, file_name, file_type, file_size]):
            raise ValidationError('请提供完整的文件信息')
        
        # Get storage and generate URL
        try:
            storage = StorageFactory.get_storage()
            url = storage.get_file_url(file_key)
        except Exception as e:
            raise ValidationError(f'获取文件URL失败: {e}', code=5001)
        
        # Create attachment record
        attachment = TaskAttachment.objects.create(
            task=task,
            file_key=file_key,
            file_name=file_name,
            file_type=file_type,
            file_size=file_size,
            url=url,
            uploaded_by=user
        )
        
        return Response({
            'code': 201,
            'message': '附件上传成功',
            'data': TaskAttachmentSerializer(attachment).data
        }, status=status.HTTP_201_CREATED)


class DownloadUrlView(generics.GenericAPIView):
    """Get presigned download URL."""
    permission_classes = [IsTeamMember]
    
    def get(self, request, attachment_id, *args, **kwargs):
        """Get download URL for an attachment."""
        try:
            attachment = TaskAttachment.objects.get(id=attachment_id)
        except TaskAttachment.DoesNotExist:
            raise ResourceNotFound('附件不存在', code=5004)
        
        task = attachment.task
        user = request.user
        
        # Check permission - only task assignee or admin can download
        if not (user.is_super_admin or user.is_team_admin or task.assignee_id == user.id):
            raise ValidationError('无权下载此附件', code=3004)
        
        # Get storage and generate URL
        try:
            storage = StorageFactory.get_storage()
            download_url = storage.get_download_url(attachment.file_key)
        except Exception as e:
            raise ValidationError(f'生成下载URL失败: {e}', code=5001)
        
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'download_url': download_url,
                'expires_in': 300
            }
        })


class AttachmentDeleteView(generics.DestroyAPIView):
    """Delete attachment."""
    permission_classes = [IsTeamMember]
    
    def destroy(self, request, attachment_id, *args, **kwargs):
        try:
            attachment = TaskAttachment.objects.get(id=attachment_id)
        except TaskAttachment.DoesNotExist:
            raise ResourceNotFound('附件不存在', code=5004)
        
        user = request.user
        
        # Check permission - only uploader or admin can delete
        can_delete = (
            user.is_super_admin or
            user.is_team_admin or
            attachment.uploaded_by_id == user.id
        )
        
        if not can_delete:
            raise ValidationError('无权删除此附件', code=3004)
        
        # Delete from storage
        try:
            storage = StorageFactory.get_storage()
            storage.delete_file(attachment.file_key)
        except Exception as e:
            print(f"Failed to delete file from storage: {e}")
        
        # Delete record
        self.perform_destroy(attachment)
        
        return Response({
            'code': 204,
            'message': '附件已删除',
            'data': None
        })


# =============================================================================
# CORS Configuration View
# =============================================================================

class CORSConfigView(generics.GenericAPIView):
    """
    Setup CORS policy for storage bucket.
    Only super admin can access this endpoint.
    """
    permission_classes = [permissions.IsAdminUser]
    
    def post(self, request, *args, **kwargs):
        """Setup CORS policy."""
        origins = request.data.get('origins')
        allow_all = request.data.get('allow_all', False)
        
        if allow_all:
            origins = ['*']
        elif not origins:
            return Response({
                'code': 400,
                'message': '请提供 origins 列表或设置 allow_all 为 true',
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if isinstance(origins, str):
            origins = [origins]
        
        try:
            storage = StorageFactory.get_storage()
            
            if hasattr(storage, 'setup_cors'):
                success = storage.setup_cors(origins)
                if success:
                    return Response({
                        'code': 0,
                        'message': 'CORS 配置成功',
                        'data': {
                            'allowed_origins': origins,
                            'allowed_methods': ['GET', 'PUT', 'POST', 'DELETE', 'HEAD'],
                            'allowed_headers': ['*']
                        }
                    })
                else:
                    return Response({
                        'code': 500,
                        'message': 'CORS 配置失败',
                        'data': None
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                return Response({
                    'code': 400,
                    'message': '当前存储不支持 CORS 配置',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'code': 500,
                'message': f'配置失败: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
