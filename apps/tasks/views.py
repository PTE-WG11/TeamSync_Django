"""
Tasks views for TeamSync.
"""
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone

from .models import Task, TaskHistory, TaskAttachment
from .serializers import (
    TaskListSerializer, TaskTreeSerializer, TaskDetailSerializer,
    MaskedTaskSerializer, TaskCreateSerializer, SubtaskCreateSerializer,
    TaskUpdateSerializer, TaskStatusUpdateSerializer, TaskHistorySerializer,
    TaskProgressSerializer
)
from config.permissions import (
    IsAdminOrSuperAdmin, IsTeamMember, IsTaskAssigneeOrAdmin
)
from config.exceptions import ValidationError, ResourceNotFound, PermissionDenied


class ProjectTaskListView(generics.ListAPIView):
    """List tasks in a project."""
    serializer_class = TaskListSerializer
    permission_classes = [IsTeamMember]
    
    def get_queryset(self):
        from apps.projects.models import Project
        project_id = self.kwargs.get('project_id')
        
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Task.objects.none()
        
        user = self.request.user
        
        # Check permission
        if not (user.is_super_admin or user.is_team_admin or project.has_member(user)):
            return Task.objects.none()
        
        queryset = Task.objects.filter(project=project)
        
        # Filter by view type
        view_type = self.request.query_params.get('view', 'flat')
        if view_type == 'tree':
            # Only main tasks in tree view
            queryset = queryset.filter(level=1)
        
        # Filter by assignee
        assignee = self.request.query_params.get('assignee')
        if assignee == 'me':
            queryset = queryset.filter(assignee=user)
        elif assignee and assignee != 'all':
            try:
                queryset = queryset.filter(assignee_id=int(assignee))
            except ValueError:
                pass
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            statuses = status_filter.split(',')
            queryset = queryset.filter(status__in=statuses)
        
        # Filter by level
        level = self.request.query_params.get('level')
        if level:
            queryset = queryset.filter(level=int(level))
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset.select_related('assignee', 'project')
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        view_type = request.query_params.get('view', 'flat')
        user = request.user
        
        if view_type == 'tree':
            # Tree view - return hierarchical structure
            serializer = TaskTreeSerializer(queryset, many=True, context={'request': request})
            return Response({
                'code': 200,
                'message': 'success',
                'data': {
                    'items': serializer.data
                }
            })
        
        # Flat view - apply permission filtering
        results = []
        for task in queryset:
            # Check if user can view full details
            if (user.is_super_admin or 
                user.is_team_admin or 
                task.assignee_id == user.id):
                results.append(task)
            else:
                # Add masked task
                results.append(task)
        
        page = self.paginate_queryset(results)
        if page is not None:
            # Serialize with permission check
            data = []
            for task in page:
                if (user.is_super_admin or 
                    user.is_team_admin or 
                    task.assignee_id == user.id):
                    data.append(TaskListSerializer(task, context={'request': request}).data)
                else:
                    data.append(MaskedTaskSerializer(task).data)
            return self.get_paginated_response(data)
        
        data = []
        for task in results:
            if (user.is_super_admin or 
                user.is_team_admin or 
                task.assignee_id == user.id):
                data.append(TaskListSerializer(task, context={'request': request}).data)
            else:
                data.append(MaskedTaskSerializer(task).data)
        
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'items': data
            }
        })


class TaskCreateView(generics.CreateAPIView):
    """Create main task (level=1)."""
    serializer_class = TaskCreateSerializer
    permission_classes = [IsAdminOrSuperAdmin]
    
    def create(self, request, *args, **kwargs):
        from apps.projects.models import Project
        project_id = kwargs.get('project_id')
        
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            raise ResourceNotFound('项目不存在')
        
        # Check if project is archived
        if project.is_archived:
            raise ValidationError('项目已归档，无法创建任务', code=2004)
        
        serializer = self.get_serializer(
            data=request.data,
            context={'project_id': project_id, 'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        task = Task.objects.create(
            **serializer.validated_data,
            project=project,
            level=1,
            parent=None,
            path='',
            created_by=request.user
        )
        
        return Response({
            'code': 201,
            'message': '任务创建成功',
            'data': TaskDetailSerializer(task, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)


class SubtaskCreateView(generics.CreateAPIView):
    """Create subtask under a task."""
    serializer_class = SubtaskCreateSerializer
    permission_classes = [IsTeamMember]
    
    def create(self, request, *args, **kwargs):
        task_id = kwargs.get('pk')
        
        try:
            parent_task = Task.objects.get(id=task_id)
        except Task.DoesNotExist:
            raise ResourceNotFound('任务不存在')
        
        # Check if project is archived
        if parent_task.project.is_archived:
            raise ValidationError('项目已归档，无法创建子任务', code=2004)
        
        # Check if user is the assignee of parent task
        if parent_task.assignee_id != request.user.id:
            raise PermissionDenied('只能为自己的任务创建子任务', code=3003)
        
        # Check level limit
        if parent_task.level >= 3:
            raise ValidationError('已达到最大层级深度（3层）', code=3002)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        subtask = parent_task.create_subtask(
            **serializer.validated_data,
            created_by=request.user
        )
        
        return Response({
            'code': 201,
            'message': '子任务创建成功',
            'data': TaskDetailSerializer(subtask, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)


class TaskDetailView(generics.RetrieveAPIView):
    """Get task detail."""
    serializer_class = TaskDetailSerializer
    permission_classes = [IsTeamMember]
    queryset = Task.objects.all()
    lookup_url_kwarg = 'pk'
    
    def retrieve(self, request, *args, **kwargs):
        task = self.get_object()
        user = request.user
        
        # Check permission
        can_view_full = (
            user.is_super_admin or
            user.is_team_admin or
            task.assignee_id == user.id
        )
        
        if not can_view_full:
            # Return masked data
            return Response({
                'code': 200,
                'message': 'success',
                'data': MaskedTaskSerializer(task).data
            })
        
        serializer = self.get_serializer(task, context={'request': request})
        return Response({
            'code': 200,
            'message': 'success',
            'data': serializer.data
        })


class TaskUpdateView(generics.UpdateAPIView):
    """Update task."""
    serializer_class = TaskUpdateSerializer
    permission_classes = [IsTeamMember]
    queryset = Task.objects.all()
    lookup_url_kwarg = 'pk'
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        task = self.get_object()
        user = request.user
        
        # Check if project is archived
        if task.project.is_archived:
            raise ValidationError('项目已归档，无法修改任务', code=3006)
        
        # Check permission
        can_edit = (
            user.is_super_admin or
            user.is_team_admin or
            task.assignee_id == user.id
        )
        
        if not can_edit:
            raise PermissionDenied('无权修改此任务', code=3004)
        
        # Store old values for history
        old_values = {
            'title': task.title,
            'description': task.description,
            'status': task.status,
            'priority': task.priority,
            'start_date': task.start_date,
            'end_date': task.end_date,
        }
        
        serializer = self.get_serializer(task, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        # Update task
        for field, value in serializer.validated_data.items():
            setattr(task, field, value)
        task.save()
        
        # Record history for changed fields
        for field, new_value in serializer.validated_data.items():
            old_value = old_values.get(field)
            if old_value != new_value:
                TaskHistory.objects.create(
                    task=task,
                    changed_by=user,
                    field_name=field,
                    old_value=str(old_value) if old_value else '',
                    new_value=str(new_value) if new_value else ''
                )
        
        return Response({
            'code': 200,
            'message': '任务更新成功',
            'data': TaskDetailSerializer(task, context={'request': request}).data
        })


class TaskStatusUpdateView(generics.UpdateAPIView):
    """Update task status."""
    serializer_class = TaskStatusUpdateSerializer
    permission_classes = [IsTeamMember]
    queryset = Task.objects.all()
    lookup_url_kwarg = 'pk'
    
    def update(self, request, *args, **kwargs):
        task = self.get_object()
        user = request.user
        
        # Check if project is archived
        if task.project.is_archived:
            raise ValidationError('项目已归档，无法修改任务状态', code=3006)
        
        # Check permission
        can_edit = (
            user.is_super_admin or
            user.is_team_admin or
            task.assignee_id == user.id
        )
        
        if not can_edit:
            raise PermissionDenied('无权修改此任务状态', code=3004)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        new_status = serializer.validated_data['status']
        task.update_status(new_status, changed_by=user)
        
        return Response({
            'code': 200,
            'message': '状态更新成功',
            'data': {
                'id': task.id,
                'status': task.status,
                'updated_at': task.updated_at
            }
        })


class TaskDeleteView(generics.DestroyAPIView):
    """Delete task (super admin only, must delete subtasks first)."""
    permission_classes = [permissions.IsAdminUser]  # Only super admin
    queryset = Task.objects.all()
    lookup_url_kwarg = 'pk'
    
    def destroy(self, request, *args, **kwargs):
        task = self.get_object()
        
        # Check if has subtasks
        if task.children.exists():
            raise ValidationError('存在子任务，无法删除', code=3005)
        
        self.perform_destroy(task)
        
        return Response({
            'code': 204,
            'message': '任务已删除',
            'data': None
        })


class TaskHistoryView(generics.ListAPIView):
    """Get task change history."""
    serializer_class = TaskHistorySerializer
    permission_classes = [IsTeamMember]
    
    def get_queryset(self):
        task_id = self.kwargs.get('pk')
        return TaskHistory.objects.filter(task_id=task_id)
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        # Check if user can view task
        try:
            task = Task.objects.get(id=self.kwargs.get('pk'))
        except Task.DoesNotExist:
            raise ResourceNotFound('任务不存在')
        
        user = request.user
        can_view = (
            user.is_super_admin or
            user.is_team_admin or
            task.assignee_id == user.id
        )
        
        if not can_view:
            raise PermissionDenied('无权查看此任务历史', code=3004)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'task_id': task.id,
                'histories': serializer.data
            }
        })


class TaskProgressView(generics.GenericAPIView):
    """Get task progress statistics."""
    permission_classes = [IsAdminOrSuperAdmin]
    
    def get(self, request, project_id, *args, **kwargs):
        from apps.projects.models import Project
        
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            raise ResourceNotFound('项目不存在')
        
        main_tasks = Task.objects.filter(project=project, level=1)
        
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'total': main_tasks.count(),
                'planning': main_tasks.filter(status='planning').count(),
                'pending': main_tasks.filter(status='pending').count(),
                'in_progress': main_tasks.filter(status='in_progress').count(),
                'completed': main_tasks.filter(status='completed').count(),
                'overdue': main_tasks.filter(normal_flag='overdue').count()
            }
        })
