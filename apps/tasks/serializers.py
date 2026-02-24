"""
Tasks serializers for TeamSync.
"""
from rest_framework import serializers
from .models import Task, TaskHistory, TaskAttachment, TaskStatus, TaskPriority


class TaskAttachmentSerializer(serializers.ModelSerializer):
    """Task attachment serializer."""
    uploaded_by_name = serializers.CharField(source='uploaded_by.username', read_only=True)
    
    class Meta:
        model = TaskAttachment
        fields = [
            'id', 'file_name', 'file_type', 'file_size',
            'url', 'uploaded_by', 'uploaded_by_name', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TaskHistorySerializer(serializers.ModelSerializer):
    """Task history serializer."""
    changed_by_name = serializers.CharField(source='changed_by.username', read_only=True)
    
    class Meta:
        model = TaskHistory
        fields = [
            'id', 'field_name', 'old_value', 'new_value',
            'changed_by', 'changed_by_name', 'changed_at'
        ]
        read_only_fields = ['id', 'changed_at']


class TaskListSerializer(serializers.ModelSerializer):
    """Task list serializer."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    assignee_name = serializers.CharField(source='assignee.username', read_only=True)
    assignee_avatar = serializers.CharField(source='assignee.avatar', read_only=True)
    can_view = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'status', 'status_display',
            'priority', 'priority_display', 'level',
            'assignee', 'assignee_name', 'assignee_avatar',
            'start_date', 'end_date', 'normal_flag',
            'subtask_count', 'completed_subtask_count',
            'can_view', 'can_edit', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_can_view(self, obj):
        """Check if user can view task details."""
        request = self.context.get('request')
        if not request:
            return False
        user = request.user
        return (
            user.is_super_admin or
            user.is_team_admin or
            obj.assignee_id == user.id
        )
    
    def get_can_edit(self, obj):
        """Check if user can edit task."""
        request = self.context.get('request')
        if not request:
            return False
        user = request.user
        
        # Check if project is archived
        if obj.project.is_archived:
            return False
        
        return (
            user.is_super_admin or
            user.is_team_admin or
            obj.assignee_id == user.id
        )


class TaskTreeSerializer(serializers.ModelSerializer):
    """Task tree serializer."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    assignee_name = serializers.CharField(source='assignee.username', read_only=True)
    assignee_avatar = serializers.CharField(source='assignee.avatar', read_only=True)
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = [
            'id', 'project_id', 'title', 'description',
            'assignee_id', 'assignee_name', 'assignee_avatar',
            'status', 'status_display', 'priority', 'priority_display',
            'level', 'parent_id', 'path', 'start_date', 'end_date',
            'normal_flag', 'subtask_count', 'completed_subtask_count',
            'children', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_children(self, obj):
        """Get child tasks."""
        if obj.level >= 3:
            return []
        
        # Filter by permission
        request = self.context.get('request')
        user = request.user if request else None
        
        children = obj.children.all()
        
        # For members, only show their own subtasks
        if user and not (user.is_super_admin or user.is_team_admin):
            children = children.filter(assignee=user)
        
        return TaskTreeSerializer(children, many=True, context=self.context).data


class TaskDetailSerializer(serializers.ModelSerializer):
    """Task detail serializer."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    assignee = serializers.SerializerMethodField()
    attachments = TaskAttachmentSerializer(many=True, read_only=True)
    subtask_count = serializers.IntegerField(read_only=True)
    can_view = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = [
            'id', 'project_id', 'title', 'description',
            'assignee', 'status', 'status_display',
            'priority', 'priority_display', 'level',
            'parent_id', 'path', 'start_date', 'end_date',
            'normal_flag', 'is_overdue_notified',
            'attachments', 'subtask_count',
            'can_view', 'can_edit',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_assignee(self, obj):
        """Get assignee info."""
        if obj.assignee:
            return {
                'id': obj.assignee.id,
                'username': obj.assignee.username,
                'avatar': obj.assignee.avatar
            }
        return None
    
    def get_can_view(self, obj):
        """Check if user can view task details."""
        request = self.context.get('request')
        if not request:
            return False
        user = request.user
        return (
            user.is_super_admin or
            user.is_team_admin or
            obj.assignee_id == user.id
        )
    
    def get_can_edit(self, obj):
        """Check if user can edit task."""
        request = self.context.get('request')
        if not request:
            return False
        user = request.user
        
        # Check if project is archived
        if obj.project.is_archived:
            return False
        
        return (
            user.is_super_admin or
            user.is_team_admin or
            obj.assignee_id == user.id
        )


class MaskedTaskSerializer(serializers.ModelSerializer):
    """Masked task serializer for unauthorized users."""
    can_view = serializers.BooleanField(default=False)
    message = serializers.CharField(default='该任务未分配给您，无权查看详情')
    
    class Meta:
        model = Task
        fields = ['id', 'title', 'status', 'level', 'can_view', 'message']
    
    def to_representation(self, instance):
        """Override to mask sensitive data."""
        return {
            'id': instance.id,
            'title': instance.title,
            'status': 'private',
            'level': instance.level,
            'assignee': '🔒 私有任务',
            'can_view': False,
            'message': '该任务未分配给您，无权查看详情'
        }


class TaskCreateSerializer(serializers.ModelSerializer):
    """Task create serializer."""
    assignee_id = serializers.IntegerField(required=True)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    
    class Meta:
        model = Task
        fields = [
            'title', 'description', 'assignee_id',
            'status', 'priority', 'start_date', 'end_date'
        ]
    
    def validate_assignee_id(self, value):
        """Validate assignee is a team member."""
        from apps.accounts.models import User
        from apps.projects.models import Project
        
        project_id = self.context.get('project_id')
        if not project_id:
            raise serializers.ValidationError('项目ID不能为空')
        
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            raise serializers.ValidationError('项目不存在')
        
        try:
            user = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError('负责人不存在')
        
        if not project.has_member(user):
            raise serializers.ValidationError('负责人不是项目成员')
        
        return value


class SubtaskCreateSerializer(serializers.ModelSerializer):
    """Subtask create serializer."""
    
    class Meta:
        model = Task
        fields = [
            'title', 'description', 'status',
            'priority', 'start_date', 'end_date'
        ]


class TaskUpdateSerializer(serializers.ModelSerializer):
    """Task update serializer."""
    
    class Meta:
        model = Task
        fields = [
            'title', 'description', 'status',
            'priority', 'start_date', 'end_date'
        ]


class TaskStatusUpdateSerializer(serializers.Serializer):
    """Task status update serializer."""
    status = serializers.ChoiceField(choices=TaskStatus.choices)


class TaskProgressSerializer(serializers.Serializer):
    """Task progress serializer."""
    total = serializers.IntegerField()
    planning = serializers.IntegerField()
    pending = serializers.IntegerField()
    in_progress = serializers.IntegerField()
    completed = serializers.IntegerField()
    overdue = serializers.IntegerField()
