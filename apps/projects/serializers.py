"""
Projects serializers for TeamSync.
"""
from rest_framework import serializers
from .models import (
    Project, ProjectMember, ProjectStatus,
    Folder, ProjectDocument, DocumentComment, DocumentType, DocumentStatus
)


class ProjectMemberSerializer(serializers.ModelSerializer):
    """Project member serializer."""
    id = serializers.IntegerField(source='user.id')
    username = serializers.CharField(source='user.username')
    role = serializers.CharField(source='user.role')
    avatar = serializers.CharField(source='user.avatar')
    
    class Meta:
        model = ProjectMember
        fields = ['id', 'username', 'role', 'avatar', 'joined_at']


class ProjectListSerializer(serializers.ModelSerializer):
    """Project list serializer."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    member_count = serializers.IntegerField(read_only=True)
    overdue_task_count = serializers.IntegerField(read_only=True)
    progress = serializers.FloatField(read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = Project
        fields = [
            'id', 'title', 'description', 'status', 'status_display',
            'progress', 'member_count', 'overdue_task_count',
            'is_archived', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProjectDetailSerializer(serializers.ModelSerializer):
    """Project detail serializer."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    member_count = serializers.IntegerField(read_only=True)
    progress = serializers.FloatField(read_only=True)
    task_stats = serializers.DictField(read_only=True)
    members = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id', 'title', 'description', 'status', 'status_display',
            'progress', 'member_count', 'task_stats',
            'is_archived', 'archived_at', 'start_date', 'end_date',
            'members', 'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'archived_at']
    
    def get_members(self, obj):
        """Get project members."""
        members = ProjectMember.objects.filter(
            project=obj,
            is_active=True
        ).select_related('user')
        return ProjectMemberSerializer(members, many=True).data
    
    def get_created_by(self, obj):
        """Get creator info."""
        if obj.created_by:
            return {
                'id': obj.created_by.id,
                'username': obj.created_by.username
            }
        return None


class ProjectCreateSerializer(serializers.ModelSerializer):
    """Project create serializer."""
    member_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        help_text='成员ID列表，至少1个'
    )
    
    class Meta:
        model = Project
        fields = [
            'title', 'description', 'status', 'start_date', 'end_date',
            'member_ids'
        ]
    
    def validate_member_ids(self, value):
        """Validate member ids."""
        if not value or len(value) == 0:
            raise serializers.ValidationError('项目必须至少有一个成员')
        
        # Check if all members belong to the team
        from apps.accounts.models import User
        team = self.context['request'].user.team
        team_member_ids = set(User.objects.filter(
            team=team,
            is_active=True
        ).values_list('id', flat=True))
        
        invalid_ids = set(value) - team_member_ids
        if invalid_ids:
            raise serializers.ValidationError(
                f'以下用户不是团队成员: {list(invalid_ids)}'
            )
        
        return value
    
    def create(self, validated_data):
        """Create project with members."""
        member_ids = validated_data.pop('member_ids')
        request = self.context['request']
        
        project = Project.objects.create(
            **validated_data,
            created_by=request.user,
            team=request.user.team
        )
        
        # Add members
        for user_id in member_ids:
            project.add_member_id(user_id)
        
        return project


class ProjectUpdateSerializer(serializers.ModelSerializer):
    """Project update serializer."""
    
    class Meta:
        model = Project
        fields = [
            'title', 'description', 'status', 'start_date', 'end_date'
        ]


class ProjectMemberUpdateSerializer(serializers.Serializer):
    """Project member update serializer."""
    member_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text='成员ID列表（覆盖式更新）'
    )
    
    def validate_member_ids(self, value):
        """Validate member ids."""
        if not value or len(value) == 0:
            raise serializers.ValidationError('项目必须至少有一个成员')
        
        from apps.accounts.models import User
        team = self.context['project'].team
        team_member_ids = set(User.objects.filter(
            team=team,
            is_active=True
        ).values_list('id', flat=True))
        
        invalid_ids = set(value) - team_member_ids
        if invalid_ids:
            raise serializers.ValidationError(
                f'以下用户不是团队成员: {list(invalid_ids)}'
            )
        
        return value


class ProjectProgressSerializer(serializers.Serializer):
    """Project progress serializer."""
    project_id = serializers.IntegerField()
    project_title = serializers.CharField()
    overall_progress = serializers.FloatField()
    main_tasks = serializers.DictField()
    member_progress = serializers.ListField()
    overdue_tasks = serializers.ListField()


# =============================================================================
# Document Serializers
# =============================================================================

class FolderSerializer(serializers.ModelSerializer):
    """Folder serializer."""
    document_count = serializers.IntegerField(read_only=True)
    created_by = serializers.SerializerMethodField()
    
    class Meta:
        model = Folder
        fields = ['id', 'name', 'sort_order', 'document_count', 'created_by', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_created_by(self, obj):
        """Get creator info."""
        if obj.created_by:
            return {
                'id': obj.created_by.id,
                'name': obj.created_by.username,
                'avatar': obj.created_by.avatar
            }
        return None


class FolderCreateSerializer(serializers.ModelSerializer):
    """Folder create serializer."""
    
    class Meta:
        model = Folder
        fields = ['name', 'sort_order']


class UploaderSerializer(serializers.Serializer):
    """Uploader info serializer."""
    id = serializers.IntegerField()
    name = serializers.CharField(source='username')
    avatar = serializers.CharField()


class DocumentListSerializer(serializers.ModelSerializer):
    """Document list serializer."""
    doc_type_display = serializers.CharField(source='get_doc_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    folder_name = serializers.CharField(source='folder.name', read_only=True, default=None)
    uploader = serializers.SerializerMethodField()
    can_edit = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = ProjectDocument
        fields = [
            'id', 'title', 'doc_type', 'doc_type_display', 'status', 'status_display',
            'folder_id', 'folder_name', 'file_name', 'file_size', 'can_edit',
            'uploader', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_uploader(self, obj):
        """Get uploader info."""
        if obj.uploaded_by:
            return UploaderSerializer(obj.uploaded_by).data
        return None


class DocumentDetailSerializer(serializers.ModelSerializer):
    """Document detail serializer."""
    type = serializers.CharField(source='doc_type', read_only=True)
    doc_type_display = serializers.CharField(source='get_doc_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    folder_name = serializers.CharField(source='folder.name', read_only=True, default=None)
    uploader = serializers.SerializerMethodField()
    can_edit = serializers.BooleanField(read_only=True)
    file_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    version = serializers.SerializerMethodField()
    version_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ProjectDocument
        fields = [
            'id', 'project_id', 'folder_id', 'folder_name',
            'title', 'type', 'doc_type', 'doc_type_display', 'status', 'status_display',
            'file_name', 'file_size', 'file_type', 'file_url', 'download_url',
            'content', 'can_edit', 'uploader', 'version', 'version_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_uploader(self, obj):
        """Get uploader info."""
        if obj.uploaded_by:
            return {
                'id': obj.uploaded_by.id,
                'name': obj.uploaded_by.username,
                'avatar': obj.uploaded_by.avatar
            }
        return None
    
    def get_file_url(self, obj):
        """Get file URL (for preview)."""
        if obj.file_key:
            from apps.files.storage import StorageFactory
            try:
                storage = StorageFactory.get_storage()
                return storage.get_file_url(obj.file_key)
            except:
                return None
        return None
    
    def get_download_url(self, obj):
        """Get download URL."""
        if obj.file_key:
            from apps.files.storage import StorageFactory
            try:
                storage = StorageFactory.get_storage()
                return storage.get_download_url(obj.file_key)
            except:
                return None
        return None
    
    def get_version(self, obj):
        """Get version string."""
        return "v1.0"
    
    def get_version_count(self, obj):
        """Get version count."""
        return 1
    
    def to_representation(self, instance):
        """Override to handle content field based on doc type."""
        ret = super().to_representation(instance)
        
        # For non-markdown types, set content to None
        if not instance.is_markdown:
            ret['content'] = None
        
        return ret


class MarkdownCreateSerializer(serializers.Serializer):
    """Markdown document create serializer."""
    title = serializers.CharField(max_length=200, required=True)
    folder_id = serializers.IntegerField(required=False, allow_null=True)
    content = serializers.CharField(required=False, allow_blank=True, default='')


class MarkdownUpdateSerializer(serializers.Serializer):
    """Markdown document update serializer."""
    title = serializers.CharField(max_length=200, required=False)
    content = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=DocumentStatus.choices, required=False)


class DocumentMoveSerializer(serializers.Serializer):
    """Document move serializer."""
    folder_id = serializers.IntegerField(required=False, allow_null=True)


class FileUploadSerializer(serializers.Serializer):
    """File upload serializer (for getting upload URL)."""
    file_name = serializers.CharField(max_length=255, required=True)
    file_type = serializers.CharField(max_length=100, required=True)
    file_size = serializers.IntegerField(required=True, min_value=1)
    folder_id = serializers.IntegerField(required=False, allow_null=True)
    title = serializers.CharField(max_length=200, required=False)


class FileConfirmSerializer(serializers.Serializer):
    """File upload confirm serializer."""
    file_key = serializers.CharField(max_length=500, required=True)
    file_name = serializers.CharField(max_length=255, required=True)
    file_type = serializers.CharField(max_length=100, required=True)
    file_size = serializers.IntegerField(required=True, min_value=1)
    folder_id = serializers.IntegerField(required=False, allow_null=True)
    title = serializers.CharField(max_length=200, required=False)


class DocumentCommentSerializer(serializers.ModelSerializer):
    """Document comment serializer."""
    author = serializers.SerializerMethodField()
    
    class Meta:
        model = DocumentComment
        fields = ['id', 'content', 'author', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_author(self, obj):
        """Get author info."""
        if obj.author:
            return {
                'id': obj.author.id,
                'name': obj.author.username,
                'avatar': obj.author.avatar
            }
        return None


class CommentCreateSerializer(serializers.Serializer):
    """Comment create serializer."""
    content = serializers.CharField(required=True, min_length=1, max_length=2000)


class DocumentStatisticsSerializer(serializers.Serializer):
    """Document statistics serializer."""
    total_documents = serializers.IntegerField()
    total_size = serializers.IntegerField()
    type_distribution = serializers.DictField(child=serializers.IntegerField())
    recent_uploads = serializers.IntegerField()
