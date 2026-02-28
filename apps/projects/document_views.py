"""
Project document views for TeamSync.
Supports folders, documents (with markdown editing), and comments.
"""
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta

from .models import Project, Folder, ProjectDocument, DocumentComment, DocumentType, DocumentStatus
from .serializers import (
    FolderSerializer, FolderCreateSerializer,
    DocumentListSerializer, DocumentDetailSerializer,
    MarkdownCreateSerializer, MarkdownUpdateSerializer,
    DocumentMoveSerializer, FileUploadSerializer, FileConfirmSerializer,
    DocumentCommentSerializer, CommentCreateSerializer,
    DocumentStatisticsSerializer
)
from apps.files.storage import StorageFactory, BaseStorage
from config.permissions import IsTeamMember
from config.exceptions import ValidationError, ResourceNotFound, PermissionDenied


# =============================================================================
# Helper Functions
# =============================================================================

def check_project_member(user, project):
    """Check if user is a member of the project."""
    if not project.has_member(user):
        raise PermissionDenied('您不是该项目的成员')


def check_project_archived(project):
    """Check if project is archived."""
    if project.is_archived:
        raise ValidationError('项目已归档，无法操作', code=3006)


def get_document_type_by_mime(file_type, file_name):
    """Get document type by MIME type and file name."""
    mime_to_type = {
        'text/markdown': DocumentType.MARKDOWN,
        'text/x-markdown': DocumentType.MARKDOWN,
        'application/pdf': DocumentType.PDF,
    }
    
    # Check by MIME type first
    if file_type in mime_to_type:
        return mime_to_type[file_type]
    
    # Check by file extension
    ext = file_name.split('.')[-1].lower() if '.' in file_name else ''
    ext_to_type = {
        'md': DocumentType.MARKDOWN,
        'markdown': DocumentType.MARKDOWN,
        'pdf': DocumentType.PDF,
        'doc': DocumentType.WORD,
        'docx': DocumentType.WORD,
        'xls': DocumentType.EXCEL,
        'xlsx': DocumentType.EXCEL,
        'ppt': DocumentType.PPT,
        'pptx': DocumentType.PPT,
        'jpg': DocumentType.IMAGE,
        'jpeg': DocumentType.IMAGE,
        'png': DocumentType.IMAGE,
        'gif': DocumentType.IMAGE,
        'webp': DocumentType.IMAGE,
        'bmp': DocumentType.IMAGE,
        'svg': DocumentType.IMAGE,
    }
    
    return ext_to_type.get(ext, DocumentType.OTHER)


# =============================================================================
# Folder Views
# =============================================================================

class FolderListCreateView(generics.ListCreateAPIView):
    """List folders or create a new folder."""
    permission_classes = [IsTeamMember]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return FolderCreateSerializer
        return FolderSerializer
    
    def get_queryset(self):
        project_id = self.kwargs.get('project_id')
        return Folder.objects.filter(project_id=project_id)
    
    def list(self, request, *args, **kwargs):
        project_id = self.kwargs.get('project_id')
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            raise ResourceNotFound('项目不存在')
        
        check_project_member(request.user, project)
        
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'code': 0,
            'data': serializer.data
        })
    
    def create(self, request, *args, **kwargs):
        project_id = self.kwargs.get('project_id')
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            raise ResourceNotFound('项目不存在')
        
        check_project_member(request.user, project)
        check_project_archived(project)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        folder = Folder.objects.create(
            **serializer.validated_data,
            project=project,
            created_by=request.user
        )
        
        return Response({
            'code': 0,
            'data': FolderSerializer(folder).data
        }, status=status.HTTP_201_CREATED)


class FolderUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    """Update or delete a folder."""
    permission_classes = [IsTeamMember]
    serializer_class = FolderCreateSerializer
    queryset = Folder.objects.all()
    lookup_url_kwarg = 'folder_id'
    
    def get_object(self):
        folder_id = self.kwargs.get('folder_id')
        try:
            return Folder.objects.get(id=folder_id)
        except Folder.DoesNotExist:
            raise ResourceNotFound('文件夹不存在')
    
    def update(self, request, *args, **kwargs):
        folder = self.get_object()
        check_project_member(request.user, folder.project)
        check_project_archived(folder.project)
        
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        for attr, value in serializer.validated_data.items():
            setattr(folder, attr, value)
        folder.save()
        
        return Response({
            'code': 0,
            'data': FolderSerializer(folder).data
        })
    
    def destroy(self, request, *args, **kwargs):
        folder = self.get_object()
        check_project_member(request.user, folder.project)
        check_project_archived(folder.project)
        
        # Check if folder has documents
        force = request.query_params.get('force', 'false').lower() == 'true'
        if folder.documents.exists() and not force:
            raise ValidationError('文件夹非空，无法删除。如需删除请使用 force=true 参数')
        
        # Delete all documents in folder if force=true
        if force:
            for doc in folder.documents.all():
                if doc.file_key:
                    try:
                        storage = StorageFactory.get_storage()
                        storage.delete_file(doc.file_key)
                    except:
                        pass
                doc.delete()
        
        folder.delete()
        
        return Response({
            'code': 0,
            'message': '删除成功',
            'data': None
        })


# =============================================================================
# Document List/Detail Views
# =============================================================================

class DocumentListView(generics.ListAPIView):
    """List documents in a project."""
    permission_classes = [IsTeamMember]
    serializer_class = DocumentListSerializer
    
    def get_queryset(self):
        project_id = self.kwargs.get('project_id')
        queryset = ProjectDocument.objects.filter(project_id=project_id)
        
        # Filter by folder
        folder_id = self.request.query_params.get('folder_id')
        if folder_id:
            if folder_id == 'null' or folder_id == '':
                queryset = queryset.filter(folder__isnull=True)
            else:
                queryset = queryset.filter(folder_id=folder_id)
        
        # Filter by type
        doc_type = self.request.query_params.get('type')
        if doc_type:
            queryset = queryset.filter(doc_type=doc_type)
        
        # Search by keyword
        keyword = self.request.query_params.get('keyword')
        if keyword:
            queryset = queryset.filter(title__icontains=keyword)
        
        return queryset.select_related('folder', 'uploaded_by')
    
    def list(self, request, *args, **kwargs):
        project_id = self.kwargs.get('project_id')
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            raise ResourceNotFound('项目不存在')
        
        check_project_member(request.user, project)
        
        queryset = self.get_queryset()
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        total = queryset.count()
        total_pages = (total + page_size - 1) // page_size
        
        start = (page - 1) * page_size
        end = start + page_size
        queryset = queryset[start:end]
        
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'code': 0,
            'data': {
                'list': serializer.data,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total': total,
                    'total_pages': total_pages
                }
            }
        })


class DocumentDetailView(generics.RetrieveAPIView):
    """Get document detail."""
    permission_classes = [IsTeamMember]
    serializer_class = DocumentDetailSerializer
    
    def get_object(self):
        document_id = self.kwargs.get('document_id')
        try:
            return ProjectDocument.objects.select_related('folder', 'uploaded_by').get(id=document_id)
        except ProjectDocument.DoesNotExist:
            raise ResourceNotFound('文档不存在')
    
    def retrieve(self, request, *args, **kwargs):
        document = self.get_object()
        check_project_member(request.user, document.project)
        
        serializer = self.get_serializer(document)
        
        return Response({
            'code': 0,
            'data': serializer.data
        })


class DocumentDeleteView(generics.DestroyAPIView):
    """Delete a document."""
    permission_classes = [IsTeamMember]
    
    def get_object(self):
        document_id = self.kwargs.get('document_id')
        try:
            return ProjectDocument.objects.get(id=document_id)
        except ProjectDocument.DoesNotExist:
            raise ResourceNotFound('文档不存在')
    
    def destroy(self, request, *args, **kwargs):
        document = self.get_object()
        check_project_member(request.user, document.project)
        check_project_archived(document.project)
        
        # Check permission (only uploader or admin can delete)
        user = request.user
        can_delete = (
            user.is_super_admin or
            user.is_team_admin or
            document.uploaded_by_id == user.id
        )
        
        if not can_delete:
            raise PermissionDenied('无权删除此文档')
        
        # Delete file from storage
        if document.file_key:
            try:
                storage = StorageFactory.get_storage()
                storage.delete_file(document.file_key)
            except Exception as e:
                print(f"Failed to delete file from storage: {e}")
        
        # Delete document
        document.delete()
        
        return Response({
            'code': 0,
            'message': '删除成功',
            'data': None
        })


class DocumentMoveView(generics.GenericAPIView):
    """Move document to a folder."""
    permission_classes = [IsTeamMember]
    serializer_class = DocumentMoveSerializer
    
    def post(self, request, document_id, *args, **kwargs):
        try:
            document = ProjectDocument.objects.get(id=document_id)
        except ProjectDocument.DoesNotExist:
            raise ResourceNotFound('文档不存在')
        
        check_project_member(request.user, document.project)
        check_project_archived(document.project)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        folder_id = serializer.validated_data.get('folder_id')
        
        if folder_id:
            try:
                folder = Folder.objects.get(id=folder_id, project=document.project)
                document.folder = folder
            except Folder.DoesNotExist:
                raise ResourceNotFound('目标文件夹不存在')
        else:
            document.folder = None
        
        document.save(update_fields=['folder', 'updated_at'])
        
        return Response({
            'code': 0,
            'data': DocumentDetailSerializer(document).data
        })


# =============================================================================
# Markdown Document Views
# =============================================================================

class MarkdownCreateView(generics.GenericAPIView):
    """Create a new markdown document."""
    permission_classes = [IsTeamMember]
    serializer_class = MarkdownCreateSerializer
    
    def post(self, request, project_id, *args, **kwargs):
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            raise ResourceNotFound('项目不存在')
        
        check_project_member(request.user, project)
        check_project_archived(project)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        folder_id = serializer.validated_data.get('folder_id')
        folder = None
        if folder_id:
            try:
                folder = Folder.objects.get(id=folder_id, project=project)
            except Folder.DoesNotExist:
                raise ResourceNotFound('文件夹不存在')
        
        document = ProjectDocument.objects.create(
            project=project,
            folder=folder,
            title=serializer.validated_data['title'],
            doc_type=DocumentType.MARKDOWN,
            status=DocumentStatus.EDITABLE,
            content=serializer.validated_data.get('content', ''),
            uploaded_by=request.user
        )
        
        return Response({
            'code': 0,
            'data': DocumentDetailSerializer(document).data
        }, status=status.HTTP_201_CREATED)


class MarkdownUpdateView(generics.GenericAPIView):
    """Update markdown document content."""
    permission_classes = [IsTeamMember]
    serializer_class = MarkdownUpdateSerializer
    
    def put(self, request, document_id, *args, **kwargs):
        try:
            document = ProjectDocument.objects.get(id=document_id)
        except ProjectDocument.DoesNotExist:
            raise ResourceNotFound('文档不存在')
        
        check_project_member(request.user, document.project)
        check_project_archived(document.project)
        
        if not document.can_edit:
            raise PermissionDenied('该文档不支持编辑')
        
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        # Update fields
        if 'title' in serializer.validated_data:
            document.title = serializer.validated_data['title']
        if 'content' in serializer.validated_data:
            document.content = serializer.validated_data['content']
        if 'status' in serializer.validated_data:
            document.status = serializer.validated_data['status']
        
        document.save()
        
        return Response({
            'code': 0,
            'data': DocumentDetailSerializer(document).data
        })


# =============================================================================
# File Upload Views (Presigned URL)
# =============================================================================

class DocumentUploadUrlView(generics.GenericAPIView):
    """Get presigned upload URL for document."""
    permission_classes = [IsTeamMember]
    serializer_class = FileUploadSerializer
    
    def post(self, request, project_id, *args, **kwargs):
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            raise ResourceNotFound('项目不存在')
        
        check_project_member(request.user, project)
        check_project_archived(project)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        file_name = serializer.validated_data['file_name']
        file_type = serializer.validated_data['file_type']
        file_size = serializer.validated_data['file_size']
        
        # Validate file
        try:
            BaseStorage.validate_file(file_name, file_size, file_type)
        except ValueError as e:
            raise ValidationError(str(e), code=5002)
        
        # Generate file key
        file_key = BaseStorage.generate_document_file_key(project_id, file_name)
        
        # Get storage and generate URL
        try:
            storage = StorageFactory.get_storage()
            upload_url = storage.get_upload_url(file_key, file_type)
        except Exception as e:
            raise ValidationError(f'生成上传URL失败: {e}', code=5001)
        
        return Response({
            'code': 0,
            'message': 'success',
            'data': {
                'upload_url': upload_url,
                'file_key': file_key,
                'expires_in': 300
            }
        })


class DocumentConfirmUploadView(generics.GenericAPIView):
    """Confirm document upload and save record."""
    permission_classes = [IsTeamMember]
    serializer_class = FileConfirmSerializer
    
    def post(self, request, project_id, *args, **kwargs):
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            raise ResourceNotFound('项目不存在')
        
        check_project_member(request.user, project)
        check_project_archived(project)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        file_key = serializer.validated_data['file_key']
        file_name = serializer.validated_data['file_name']
        file_type = serializer.validated_data['file_type']
        file_size = serializer.validated_data['file_size']
        folder_id = serializer.validated_data.get('folder_id')
        title = serializer.validated_data.get('title') or file_name
        
        # Get folder if specified
        folder = None
        if folder_id:
            try:
                folder = Folder.objects.get(id=folder_id, project=project)
            except Folder.DoesNotExist:
                raise ResourceNotFound('文件夹不存在')
        
        # Determine document type
        doc_type = get_document_type_by_mime(file_type, file_name)
        
        # Determine status (markdown can be editable, others are readonly)
        doc_status = DocumentStatus.EDITABLE if doc_type == DocumentType.MARKDOWN else DocumentStatus.READONLY
        
        # Create document record
        document = ProjectDocument.objects.create(
            project=project,
            folder=folder,
            title=title,
            doc_type=doc_type,
            status=doc_status,
            file_key=file_key,
            file_name=file_name,
            file_type=file_type,
            file_size=file_size,
            uploaded_by=request.user
        )
        
        return Response({
            'code': 0,
            'message': '上传成功',
            'data': DocumentDetailSerializer(document).data
        }, status=status.HTTP_201_CREATED)


class DocumentDownloadUrlView(generics.GenericAPIView):
    """Get presigned download URL for document."""
    permission_classes = [IsTeamMember]
    
    def get(self, request, document_id, *args, **kwargs):
        try:
            document = ProjectDocument.objects.get(id=document_id)
        except ProjectDocument.DoesNotExist:
            raise ResourceNotFound('文档不存在')
        
        check_project_member(request.user, document.project)
        
        if not document.file_key:
            raise ValidationError('该文档没有文件', code=5004)
        
        # Get inline parameter
        inline = request.query_params.get('inline', 'false').lower() == 'true'
        
        try:
            storage = StorageFactory.get_storage()
            if inline:
                download_url = storage.get_file_url(document.file_key)
            else:
                download_url = storage.get_download_url(document.file_key)
        except Exception as e:
            raise ValidationError(f'生成下载URL失败: {e}', code=5001)
        
        return Response({
            'code': 0,
            'data': {
                'download_url': download_url,
                'expires_in': 300 if not inline else None
            }
        })


# =============================================================================
# Comment Views
# =============================================================================

class CommentListCreateView(generics.ListCreateAPIView):
    """List comments or create a new comment."""
    permission_classes = [IsTeamMember]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CommentCreateSerializer
        return DocumentCommentSerializer
    
    def get_queryset(self):
        document_id = self.kwargs.get('document_id')
        return DocumentComment.objects.filter(document_id=document_id)
    
    def list(self, request, *args, **kwargs):
        document_id = self.kwargs.get('document_id')
        try:
            document = ProjectDocument.objects.get(id=document_id)
        except ProjectDocument.DoesNotExist:
            raise ResourceNotFound('文档不存在')
        
        check_project_member(request.user, document.project)
        
        queryset = self.get_queryset().select_related('author')
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        total = queryset.count()
        total_pages = (total + page_size - 1) // page_size
        
        start = (page - 1) * page_size
        end = start + page_size
        queryset = queryset[start:end]
        
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'code': 0,
            'data': {
                'list': serializer.data,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total': total,
                    'total_pages': total_pages
                }
            }
        })
    
    def create(self, request, *args, **kwargs):
        document_id = self.kwargs.get('document_id')
        try:
            document = ProjectDocument.objects.get(id=document_id)
        except ProjectDocument.DoesNotExist:
            raise ResourceNotFound('文档不存在')
        
        check_project_member(request.user, document.project)
        check_project_archived(document.project)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        comment = DocumentComment.objects.create(
            document=document,
            content=serializer.validated_data['content'],
            author=request.user
        )
        
        return Response({
            'code': 0,
            'data': DocumentCommentSerializer(comment).data
        }, status=status.HTTP_201_CREATED)


class CommentDeleteView(generics.DestroyAPIView):
    """Delete a comment."""
    permission_classes = [IsTeamMember]
    
    def get_object(self):
        comment_id = self.kwargs.get('comment_id')
        try:
            return DocumentComment.objects.select_related('document', 'author').get(id=comment_id)
        except DocumentComment.DoesNotExist:
            raise ResourceNotFound('评论不存在')
    
    def destroy(self, request, *args, **kwargs):
        comment = self.get_object()
        check_project_member(request.user, comment.document.project)
        
        # Check permission (only author or admin can delete)
        user = request.user
        can_delete = (
            user.is_super_admin or
            user.is_team_admin or
            comment.author_id == user.id
        )
        
        if not can_delete:
            raise PermissionDenied('无权删除此评论')
        
        comment.delete()
        
        return Response({
            'code': 0,
            'message': '删除成功',
            'data': None
        })


# =============================================================================
# Statistics View
# =============================================================================

class DocumentStatisticsView(generics.GenericAPIView):
    """Get document statistics for a project."""
    permission_classes = [IsTeamMember]
    
    def get(self, request, project_id, *args, **kwargs):
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            raise ResourceNotFound('项目不存在')
        
        check_project_member(request.user, project)
        
        documents = ProjectDocument.objects.filter(project=project)
        
        # Total count and size
        total_documents = documents.count()
        total_size = sum(doc.file_size for doc in documents if doc.file_size)
        
        # Type distribution
        type_distribution = {}
        for doc_type, _ in DocumentType.choices:
            type_distribution[doc_type] = documents.filter(doc_type=doc_type).count()
        
        # Recent uploads (last 7 days)
        seven_days_ago = timezone.now() - timedelta(days=7)
        recent_uploads = documents.filter(created_at__gte=seven_days_ago).count()
        
        return Response({
            'code': 0,
            'data': {
                'total_documents': total_documents,
                'total_size': total_size,
                'type_distribution': type_distribution,
                'recent_uploads': recent_uploads
            }
        })


# =============================================================================
# Global Document Detail View (for /documents/{id}/ endpoint)
# =============================================================================

class GlobalDocumentDetailView(generics.RetrieveAPIView):
    """
    Get document detail by ID (global endpoint).
    URL: /documents/{id}/
    """
    permission_classes = [IsTeamMember]
    serializer_class = DocumentDetailSerializer
    lookup_url_kwarg = 'id'
    lookup_field = 'id'
    queryset = ProjectDocument.objects.all()
    
    def get_object(self):
        document_id = self.kwargs.get(self.lookup_url_kwarg)
        try:
            return ProjectDocument.objects.select_related(
                'folder', 'uploaded_by', 'project'
            ).get(id=document_id)
        except ProjectDocument.DoesNotExist:
            raise ResourceNotFound('文档不存在')
    
    def retrieve(self, request, *args, **kwargs):
        document = self.get_object()
        check_project_member(request.user, document.project)
        
        serializer = self.get_serializer(document)
        
        return Response({
            'code': 0,
            'data': serializer.data
        })
