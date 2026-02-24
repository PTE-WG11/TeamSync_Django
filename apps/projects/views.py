"""
Projects views for TeamSync.
"""
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone

from .models import Project, ProjectMember
from .serializers import (
    ProjectListSerializer, ProjectDetailSerializer,
    ProjectCreateSerializer, ProjectUpdateSerializer,
    ProjectMemberUpdateSerializer, ProjectProgressSerializer
)
from config.permissions import IsAdminOrSuperAdmin, IsTeamMember
from config.exceptions import ValidationError, ResourceNotFound, PermissionDenied


class ProjectListView(generics.ListCreateAPIView):
    """List and create projects."""
    serializer_class = ProjectListSerializer
    permission_classes = [IsTeamMember]
    
    def get_permissions(self):
        """Allow team members to list, but only admins to create."""
        if self.request.method == 'POST':
            return [IsAdminOrSuperAdmin()]
        return [IsTeamMember()]
    
    def get_serializer_class(self):
        """Use different serializer for list and create."""
        if self.request.method == 'POST':
            return ProjectCreateSerializer
        return ProjectListSerializer
    
    def get_queryset(self):
        user = self.request.user
        queryset = Project.objects.filter(
            Q(team=user.team) | Q(members=user),
            is_archived=False
        ).distinct()
        
        # Filter by status
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        
        # Filter by archived
        include_archived = self.request.query_params.get('is_archived', 'false').lower() == 'true'
        if not include_archived:
            queryset = queryset.filter(is_archived=False)
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset.select_related('created_by').prefetch_related('members')
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'items': serializer.data
            }
        })
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = serializer.save()
        
        return Response({
            'code': 201,
            'message': '项目创建成功',
            'data': ProjectDetailSerializer(project).data
        }, status=status.HTTP_201_CREATED)


class ProjectCreateView(generics.CreateAPIView):
    """Create project."""
    serializer_class = ProjectCreateSerializer
    permission_classes = [IsAdminOrSuperAdmin]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = serializer.save()
        
        return Response({
            'code': 201,
            'message': '项目创建成功',
            'data': ProjectDetailSerializer(project).data
        }, status=status.HTTP_201_CREATED)


class ProjectDetailView(generics.RetrieveAPIView):
    """Get project detail."""
    serializer_class = ProjectDetailSerializer
    permission_classes = [IsTeamMember]
    queryset = Project.objects.all()
    lookup_url_kwarg = 'pk'
    
    def get_queryset(self):
        user = self.request.user
        return Project.objects.filter(
            Q(team=user.team) | Q(members=user)
        ).distinct()
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'code': 200,
            'message': 'success',
            'data': serializer.data
        })


class ProjectUpdateView(generics.UpdateAPIView):
    """Update project."""
    serializer_class = ProjectUpdateSerializer
    permission_classes = [IsAdminOrSuperAdmin]
    queryset = Project.objects.all()
    lookup_url_kwarg = 'pk'
    
    def get_queryset(self):
        return Project.objects.filter(team=self.request.user.team)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Check if project is archived
        if instance.is_archived:
            raise ValidationError('项目已归档，无法修改', code=2004)
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response({
            'code': 200,
            'message': '项目更新成功',
            'data': ProjectDetailSerializer(instance).data
        })


class ProjectArchiveView(generics.GenericAPIView):
    """Archive project."""
    permission_classes = [IsAdminOrSuperAdmin]
    queryset = Project.objects.all()
    lookup_url_kwarg = 'pk'
    
    def get_queryset(self):
        return Project.objects.filter(team=self.request.user.team)
    
    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        
        if instance.is_archived:
            raise ValidationError('项目已归档')
        
        instance.archive()
        
        return Response({
            'code': 200,
            'message': '项目已归档',
            'data': {
                'id': instance.id,
                'is_archived': True,
                'archived_at': instance.archived_at
            }
        })


class ProjectUnarchiveView(generics.GenericAPIView):
    """Unarchive project."""
    permission_classes = [IsAdminOrSuperAdmin]
    queryset = Project.objects.all()
    lookup_url_kwarg = 'pk'
    
    def get_queryset(self):
        return Project.objects.filter(team=self.request.user.team)
    
    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        
        if not instance.is_archived:
            raise ValidationError('项目未归档')
        
        instance.unarchive()
        
        return Response({
            'code': 200,
            'message': '项目已取消归档',
            'data': {
                'id': instance.id,
                'is_archived': False
            }
        })


class ProjectDeleteView(generics.DestroyAPIView):
    """Delete project (hard delete, only for super admin and archived projects)."""
    permission_classes = [permissions.IsAdminUser]  # Only super admin
    queryset = Project.objects.all()
    lookup_url_kwarg = 'pk'
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        if not instance.is_archived:
            raise ValidationError('项目未归档，无法删除', code=2005)
        
        self.perform_destroy(instance)
        
        return Response({
            'code': 204,
            'message': '项目已删除',
            'data': None
        })


class ProjectProgressView(generics.GenericAPIView):
    """Get project progress."""
    permission_classes = [IsAdminOrSuperAdmin]
    queryset = Project.objects.all()
    lookup_url_kwarg = 'pk'
    
    def get(self, request, *args, **kwargs):
        project = self.get_object()
        
        from apps.tasks.models import Task
        from apps.accounts.models import User
        
        # Main task statistics
        main_tasks = Task.objects.filter(project=project, level=1)
        total = main_tasks.count()
        completed = main_tasks.filter(status='completed').count()
        in_progress = main_tasks.filter(status='in_progress').count()
        pending = main_tasks.filter(status='pending').count()
        planning = main_tasks.filter(status='planning').count()
        
        # Member progress
        member_progress = []
        for member in project.members.filter(is_active=True):
            assigned_tasks = Task.objects.filter(
                project=project,
                level=1,
                assignee=member
            )
            member_total = assigned_tasks.count()
            member_completed = assigned_tasks.filter(status='completed').count()
            
            member_progress.append({
                'user_id': member.id,
                'username': member.username,
                'assigned_tasks': member_total,
                'completed_tasks': member_completed,
                'completion_rate': round((member_completed / member_total) * 100, 2) if member_total > 0 else 0
            })
        
        # Overdue tasks
        overdue_tasks = []
        for task in Task.objects.filter(
            project=project,
            normal_flag='overdue',
            status__in=['planning', 'pending', 'in_progress']
        ):
            overdue_tasks.append({
                'id': task.id,
                'title': task.title,
                'assignee': task.assignee.username if task.assignee else None,
                'end_date': task.end_date
            })
        
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'project_id': project.id,
                'project_title': project.title,
                'overall_progress': project.progress,
                'main_tasks': {
                    'total': total,
                    'completed': completed,
                    'in_progress': in_progress,
                    'pending': pending,
                    'planning': planning
                },
                'member_progress': member_progress,
                'overdue_tasks': overdue_tasks
            }
        })


class ProjectMemberUpdateView(generics.UpdateAPIView):
    """Update project members."""
    serializer_class = ProjectMemberUpdateSerializer
    permission_classes = [IsAdminOrSuperAdmin]
    queryset = Project.objects.all()
    lookup_url_kwarg = 'pk'
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['project'] = self.get_object()
        return context
    
    def update(self, request, *args, **kwargs):
        project = self.get_object()
        
        # Check if project is archived
        if project.is_archived:
            raise ValidationError('项目已归档，无法修改成员', code=2004)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        member_ids = serializer.validated_data['member_ids']
        project.set_members(member_ids)
        
        return Response({
            'code': 200,
            'message': '成员更新成功',
            'data': {
                'project_id': project.id,
                'members': [
                    {'id': m.user.id, 'username': m.user.username}
                    for m in ProjectMember.objects.filter(project=project, is_active=True)
                ]
            }
        })
