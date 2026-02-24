"""
Accounts serializers for TeamSync.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import models
from .models import Team, TeamInvitation, UserRole

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """User serializer for basic info."""
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    team_name = serializers.CharField(source='team.name', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'role', 'role_display',
            'team_id', 'team_name', 'avatar', 'phone',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserDetailSerializer(serializers.ModelSerializer):
    """User serializer with detailed info."""
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    team = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'role', 'role_display',
            'team', 'avatar', 'phone', 'is_active',
            'permissions', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_team(self, obj):
        """Get team info."""
        if obj.team:
            return {
                'id': obj.team.id,
                'name': obj.team.name
            }
        return None
    
    def get_permissions(self, obj):
        """Get user permissions based on role."""
        permissions = []
        if obj.is_super_admin:
            permissions = ['*']  # All permissions
        elif obj.is_team_admin:
            permissions = [
                'view_project', 'create_project', 'edit_project', 'archive_project',
                'view_task', 'create_task', 'edit_task', 'delete_task',
                'view_team', 'manage_team_member', 'invite_member',
                'view_progress', 'view_gantt_all', 'view_kanban_all'
            ]
        elif obj.is_team_member:
            permissions = [
                'view_project', 'view_task', 'edit_own_task',
                'create_subtask', 'view_gantt_own', 'view_kanban_own'
            ]
        return permissions


class UserRegisterSerializer(serializers.ModelSerializer):
    """User registration serializer."""
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )
    password_confirm = serializers.CharField(write_only=True, required=True)
    join_type = serializers.ChoiceField(
        choices=[('create', '创建团队'), ('join', '加入团队')],
        required=True,
        write_only=True
    )
    team_name = serializers.CharField(required=False, allow_blank=True, write_only=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'join_type', 'team_name'
        ]
    
    def validate(self, attrs):
        """Validate password match and team name."""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError(
                {'password_confirm': '两次密码输入不一致'}
            )
        
        if attrs['join_type'] == 'create' and not attrs.get('team_name'):
            raise serializers.ValidationError(
                {'team_name': '创建团队时团队名称不能为空'}
            )
        
        return attrs
    
    def create(self, validated_data):
        """Create user and handle team."""
        join_type = validated_data.pop('join_type')
        team_name = validated_data.pop('team_name', None)
        validated_data.pop('password_confirm')
        
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=UserRole.VISITOR  # Default to visitor
        )
        
        # Create team if needed
        if join_type == 'create' and team_name:
            team = Team.objects.create(
                name=team_name,
                owner=user
            )
            user.join_team(team, UserRole.TEAM_ADMIN)
        
        return user


class UserLoginSerializer(serializers.Serializer):
    """User login serializer."""
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class TokenResponseSerializer(serializers.Serializer):
    """Token response serializer."""
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    expires_at = serializers.DateTimeField()
    user = UserSerializer()


class TeamSerializer(serializers.ModelSerializer):
    """Team serializer."""
    member_count = serializers.IntegerField(read_only=True)
    admin_count = serializers.IntegerField(read_only=True)
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    
    class Meta:
        model = Team
        fields = [
            'id', 'name', 'description', 'owner', 'owner_name',
            'member_count', 'admin_count', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TeamMemberSerializer(serializers.ModelSerializer):
    """Team member serializer."""
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    task_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'role', 'role_display',
            'avatar', 'task_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_task_count(self, obj):
        """Get user's task count."""
        from apps.tasks.models import Task
        return Task.objects.filter(assignee=obj).count()


class TeamInvitationSerializer(serializers.ModelSerializer):
    """Team invitation serializer."""
    team_name = serializers.CharField(source='team.name', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    invited_by_name = serializers.CharField(source='invited_by.username', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = TeamInvitation
        fields = [
            'id', 'team', 'team_name', 'user', 'user_name',
            'invited_by', 'invited_by_name', 'role', 'role_display',
            'is_accepted', 'accepted_at', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'accepted_at']


class InviteMemberSerializer(serializers.Serializer):
    """Invite member serializer."""
    username = serializers.CharField(required=True, help_text='用户名或邮箱')
    role = serializers.ChoiceField(
        choices=[UserRole.TEAM_ADMIN, UserRole.MEMBER],
        default=UserRole.MEMBER
    )
    
    def validate_username(self, value):
        """Validate user exists."""
        try:
            user = User.objects.get(
                models.Q(username=value) | models.Q(email=value)
            )
        except User.DoesNotExist:
            raise serializers.ValidationError('用户不存在，请先注册账号')
        
        if user.team:
            raise serializers.ValidationError('该用户已是团队成员')
        
        self.context['invited_user'] = user
        return value


class ChangeRoleSerializer(serializers.Serializer):
    """Change member role serializer."""
    role = serializers.ChoiceField(
        choices=[UserRole.TEAM_ADMIN, UserRole.MEMBER]
    )
