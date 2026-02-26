"""
Tasks views for TeamSync.
"""
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone

from .models import Task, TaskHistory, TaskAttachment, TaskDeleteLog
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
    """Delete task (super admin only, must delete subtasks first).
    
    Records deletion log before permanently deleting the task.
    """
    permission_classes = [permissions.IsAdminUser]  # Only super admin
    queryset = Task.objects.all()
    lookup_url_kwarg = 'pk'
    
    def destroy(self, request, *args, **kwargs):
        task = self.get_object()
        user = request.user
        
        # Check if has subtasks
        if task.children.exists():
            raise ValidationError('存在子任务，无法删除', code=3005)
        
        # Get deletion reason from request (optional)
        deletion_reason = request.data.get('reason', '')
        
        # Create deletion log before deleting
        self._create_delete_log(task, user, deletion_reason)
        
        # Perform actual deletion
        self.perform_destroy(task)
        
        return Response({
            'code': 204,
            'message': '任务已删除',
            'data': None
        })
    
    def _create_delete_log(self, task, deleted_by, deletion_reason):
        """Create a log entry for the deleted task."""
        # Build full task data as JSON for complete recovery if needed
        task_data = {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'project_id': task.project_id,
            'project_title': task.project.title if task.project else '',
            'assignee_id': task.assignee_id,
            'assignee_name': task.assignee.username if task.assignee else None,
            'assignee_avatar': task.assignee.avatar if task.assignee else None,
            'status': task.status,
            'priority': task.priority,
            'level': task.level,
            'parent_id': task.parent_id,
            'path': task.path,
            'start_date': task.start_date.isoformat() if task.start_date else None,
            'end_date': task.end_date.isoformat() if task.end_date else None,
            'normal_flag': task.normal_flag,
            'created_by_id': task.created_by_id,
            'created_by_name': task.created_by.username if task.created_by else None,
            'created_at': task.created_at.isoformat() if task.created_at else None,
            'updated_at': task.updated_at.isoformat() if task.updated_at else None,
        }
        
        TaskDeleteLog.objects.create(
            original_task_id=task.id,
            title=task.title,
            description=task.description,
            project_id=task.project_id,
            project_title=task.project.title if task.project else '',
            assignee_id=task.assignee_id,
            assignee_name=task.assignee.username if task.assignee else None,
            status=task.status,
            priority=task.priority,
            level=task.level,
            parent_id=task.parent_id,
            path=task.path,
            start_date=task.start_date,
            end_date=task.end_date,
            created_by_id=task.created_by_id,
            created_by_name=task.created_by.username if task.created_by else None,
            original_created_at=task.created_at,
            deleted_by=deleted_by,
            deleted_by_name=deleted_by.username if deleted_by else None,
            deletion_reason=deletion_reason,
            task_data_json=task_data
        )


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


class TaskCreateUnassignedView(generics.CreateAPIView):
    """
    Create a main task without assignee.
    Any team member can create unassigned tasks in kanban.
    """
    permission_classes = [IsTeamMember]
    
    def create(self, request, *args, **kwargs):
        from apps.projects.models import Project
        
        # Get project_id from request body
        project_id = request.data.get('project_id')
        if not project_id:
            raise ValidationError('项目ID不能为空', code=2001)
        
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            raise ResourceNotFound('项目不存在')
        
        # Check if user is project member
        user = request.user
        if not (user.is_super_admin or user.is_team_admin or project.has_member(user)):
            raise PermissionDenied('无权在此项目中创建任务', code=3004)
        
        # Check if project is archived
        if project.is_archived:
            raise ValidationError('项目已归档，无法创建任务', code=2004)
        
        # Validate and create task
        title = request.data.get('title', '').strip()
        if not title:
            raise ValidationError('任务标题不能为空', code=3007)
        
        description = request.data.get('description', '').strip()
        priority = request.data.get('priority', 'medium')
        
        # Validate priority
        valid_priorities = ['urgent', 'high', 'medium', 'low']
        if priority not in valid_priorities:
            priority = 'medium'
        
        # Create unassigned task (level=1, no assignee, status=planning)
        task = Task.objects.create(
            project=project,
            title=title,
            description=description,
            assignee=None,
            status='planning',
            priority=priority,
            level=1,
            parent=None,
            path='',
            created_by=user
        )
        
        return Response({
            'code': 201,
            'message': '任务创建成功',
            'data': {
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'assignee_id': None,
                'assignee_name': None,
                'status': task.status,
                'priority': task.priority,
                'level': task.level,
                'project_id': task.project_id,
                'start_date': None,
                'end_date': None,
                'created_at': task.created_at.isoformat() if task.created_at else None
            }
        }, status=status.HTTP_201_CREATED)


class TaskClaimView(generics.GenericAPIView):
    """
    Claim and activate a planning task.
    When user drags a task from 'planning' to 'pending' or 'in_progress',
    this endpoint assigns the task to current user and sets dates.
    """
    permission_classes = [IsTeamMember]
    
    def post(self, request, pk, *args, **kwargs):
        try:
            task = Task.objects.get(id=pk, level=1)
        except Task.DoesNotExist:
            raise ResourceNotFound('任务不存在')
        
        # Check if project is archived
        if task.project.is_archived:
            raise ValidationError('项目已归档，无法修改任务', code=3006)
        
        user = request.user
        
        # Validate request data
        new_status = request.data.get('status')
        end_date = request.data.get('end_date')
        
        if not new_status:
            raise ValidationError('目标状态不能为空', code=3008)
        
        if new_status not in ['pending', 'in_progress']:
            raise ValidationError('无效的目标状态，只能是 pending 或 in_progress', code=3008)
        
        if not end_date:
            raise ValidationError('结束时间不能为空', code=3009)
        
        # Validate task status - can only claim planning tasks
        if task.status != 'planning':
            raise ValidationError('只能领取状态为"规划中"的任务', code=3010)
        
        # Check if task already has an assignee (someone else claimed it)
        if task.assignee_id is not None and task.assignee_id != user.id:
            raise PermissionDenied('该任务已被其他人领取', code=3011)
        
        # Update task
        from datetime import datetime
        try:
            # Parse end_date - support both date and datetime format
            if isinstance(end_date, str):
                # Try datetime format first, then date format
                try:
                    end_date = datetime.strptime(end_date, '%Y-%m-%dT%H:%M:%S')
                except ValueError:
                    try:
                        end_date = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        # Fallback to date only, set time to end of day
                        end_date = datetime.strptime(end_date, '%Y-%m-%d')
                        end_date = end_date.replace(hour=23, minute=59, second=59)
        except ValueError:
            raise ValidationError('结束时间格式错误，应为 YYYY-MM-DDTHH:mm:ss 或 YYYY-MM-DD', code=3009)
        
        # Set start_date to current datetime
        now = timezone.now()
        
        # Validate end_date is not before today (compare date part only)
        if end_date.date() < now.date():
            raise ValidationError('结束时间不能早于今天', code=3009)
        
        # Update task fields
        task.assignee = user
        task.status = new_status
        task.start_date = now
        task.end_date = end_date
        task.save(update_fields=['assignee', 'status', 'start_date', 'end_date', 'updated_at'])
        
        # Record history
        TaskHistory.objects.create(
            task=task,
            changed_by=user,
            field_name='claim',
            old_value='planning/unassigned',
            new_value=f'{new_status}/user_{user.id}'
        )
        
        return Response({
            'code': 200,
            'message': '任务领取成功',
            'data': {
                'id': task.id,
                'title': task.title,
                'assignee_id': user.id,
                'assignee_name': user.username,
                'status': task.status,
                'priority': task.priority,
                'level': task.level,
                'project_id': task.project_id,
                'start_date': task.start_date.isoformat() if task.start_date else None,
                'end_date': task.end_date.isoformat() if task.end_date else None,
                'updated_at': task.updated_at.isoformat() if task.updated_at else None
            }
        })



class TaskDeleteLogListView(generics.ListAPIView):
    """List task deletion logs (admin only)."""
    permission_classes = [IsAdminOrSuperAdmin]
    
    def get_queryset(self):
        queryset = TaskDeleteLog.objects.all()
        
        # Filter by project
        project_id = self.request.query_params.get('project_id')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        # Filter by deleted_by
        deleted_by = self.request.query_params.get('deleted_by')
        if deleted_by:
            queryset = queryset.filter(deleted_by_id=deleted_by)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(deleted_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(deleted_at__date__lte=end_date)
        
        # Search by title
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(title__icontains=search)
        
        return queryset.select_related('deleted_by')
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Pagination
        from config.pagination import StandardPagination
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        
        data = []
        for log in (page if page is not None else queryset):
            data.append({
                'id': log.id,
                'original_task_id': log.original_task_id,
                'title': log.title,
                'description': log.description,
                'project': {
                    'id': log.project_id,
                    'title': log.project_title
                },
                'assignee': {
                    'id': log.assignee_id,
                    'username': log.assignee_name
                } if log.assignee_id else None,
                'created_by': {
                    'id': log.created_by_id,
                    'username': log.created_by_name
                } if log.created_by_id else None,
                'status': log.status,
                'priority': log.priority,
                'level': log.level,
                'start_date': log.start_date.isoformat() if log.start_date else None,
                'end_date': log.end_date.isoformat() if log.end_date else None,
                'original_created_at': log.original_created_at.isoformat() if log.original_created_at else None,
                'deleted_by': {
                    'id': log.deleted_by.id if log.deleted_by else None,
                    'username': log.deleted_by_name
                },
                'deleted_at': log.deleted_at.isoformat(),
                'deletion_reason': log.deletion_reason
            })
        
        if page is not None:
            return paginator.get_paginated_response(data)
        
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'items': data
            }
        })


class TaskDeleteLogDetailView(generics.RetrieveAPIView):
    """Get task deletion log detail (admin only)."""
    permission_classes = [IsAdminOrSuperAdmin]
    
    def get_object(self):
        log_id = self.kwargs.get('pk')
        try:
            return TaskDeleteLog.objects.get(id=log_id)
        except TaskDeleteLog.DoesNotExist:
            raise ResourceNotFound('删除日志不存在')
    
    def retrieve(self, request, *args, **kwargs):
        log = self.get_object()
        
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'id': log.id,
                'original_task_id': log.original_task_id,
                'title': log.title,
                'description': log.description,
                'project': {
                    'id': log.project_id,
                    'title': log.project_title
                },
                'assignee': {
                    'id': log.assignee_id,
                    'username': log.assignee_name
                } if log.assignee_id else None,
                'created_by': {
                    'id': log.created_by_id,
                    'username': log.created_by_name
                } if log.created_by_id else None,
                'status': log.status,
                'priority': log.priority,
                'level': log.level,
                'parent_id': log.parent_id,
                'path': log.path,
                'start_date': log.start_date.isoformat() if log.start_date else None,
                'end_date': log.end_date.isoformat() if log.end_date else None,
                'original_created_at': log.original_created_at.isoformat() if log.original_created_at else None,
                'deleted_by': {
                    'id': log.deleted_by.id if log.deleted_by else None,
                    'username': log.deleted_by_name
                },
                'deleted_at': log.deleted_at.isoformat(),
                'deletion_reason': log.deletion_reason,
                'task_data_json': log.task_data_json  # Full task data for potential recovery
            }
        })
