"""
Projects serializers for TeamSync.
"""
from rest_framework import serializers
from .models import Project, ProjectMember, ProjectStatus


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
