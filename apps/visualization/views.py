"""
Visualization views for TeamSync.
"""
from rest_framework import generics, permissions
from rest_framework.response import Response
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta

from apps.projects.models import Project
from apps.tasks.models import Task
from apps.accounts.models import User
from config.permissions import IsAdminOrSuperAdmin, IsTeamMember
from config.exceptions import ResourceNotFound


class GanttDataView(generics.GenericAPIView):
    """Get Gantt chart data for a project."""
    permission_classes = [IsTeamMember]
    
    def get(self, request, project_id, *args, **kwargs):
        """Get Gantt data."""
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            raise ResourceNotFound('项目不存在')
        
        user = request.user
        is_admin = user.is_super_admin or user.is_team_admin
        
        # Get date range
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        view_mode = request.query_params.get('view_mode', 'day')
        
        # Build queryset
        if is_admin:
            # Admin sees all main tasks
            queryset = Task.objects.filter(project=project, level=1)
        else:
            # Member sees only their main tasks and subtasks
            queryset = Task.objects.filter(
                Q(project=project, level=1, assignee=user) |
                Q(project=project, level__gt=1, assignee=user)
            )
        
        # Apply date filter
        if start_date:
            queryset = queryset.filter(end_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(start_date__lte=end_date)
        
        # Get default date range if not specified
        if not start_date or not end_date:
            today = timezone.now().date()
            week_start = today - timedelta(days=today.weekday())
            week_end = week_start + timedelta(days=6)
            start_date = week_start.isoformat()
            end_date = week_end.isoformat()
        
        # Build task tree
        tasks_data = []
        member_colors = {}
        color_palette = ['#0D9488', '#0891B2', '#10B981', '#F59E0B', '#F43F5E', '#8B5CF6']
        
        for task in queryset.select_related('assignee'):
            # Assign color to member
            if task.assignee_id and task.assignee_id not in member_colors:
                member_colors[task.assignee_id] = color_palette[len(member_colors) % len(color_palette)]
            
            task_data = {
                'id': task.id,
                'title': task.title,
                'start': task.start_date.isoformat() if task.start_date else None,
                'end': task.end_date.isoformat() if task.end_date else None,
                'progress': 100 if task.status == 'completed' else (
                    50 if task.status == 'in_progress' else 0
                ),
                'status': task.status,
                'assignee': {
                    'id': task.assignee.id if task.assignee else None,
                    'username': task.assignee.username if task.assignee else None,
                    'color': member_colors.get(task.assignee_id)
                } if task.assignee else None,
                'level': task.level,
                'children': []
            }
            
            # Add children for member's own tasks
            if not is_admin and task.level == 1 and task.assignee_id == user.id:
                children = Task.objects.filter(parent=task, assignee=user)
                for child in children:
                    task_data['children'].append({
                        'id': child.id,
                        'title': child.title,
                        'start': child.start_date.isoformat() if child.start_date else None,
                        'end': child.end_date.isoformat() if child.end_date else None,
                        'progress': 100 if child.status == 'completed' else (
                            50 if child.status == 'in_progress' else 0
                        ),
                        'status': child.status,
                        'level': child.level,
                        'children': []
                    })
            
            tasks_data.append(task_data)
        
        # Build members list
        members = []
        for member_id, color in member_colors.items():
            try:
                member = User.objects.get(id=member_id)
                members.append({
                    'id': member.id,
                    'username': member.username,
                    'color': color
                })
            except User.DoesNotExist:
                pass
        
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'project_id': project.id,
                'view_mode': view_mode,
                'date_range': {
                    'start': start_date,
                    'end': end_date
                },
                'tasks': tasks_data,
                'members': members
            }
        })


class KanbanDataView(generics.GenericAPIView):
    """Get Kanban board data for a project."""
    permission_classes = [IsTeamMember]
    
    def get(self, request, project_id, *args, **kwargs):
        """Get Kanban data."""
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            raise ResourceNotFound('项目不存在')
        
        user = request.user
        is_admin = user.is_super_admin or user.is_team_admin
        
        # Filter by assignee
        assignee = request.query_params.get('assignee', 'all')
        
        # Build queryset
        queryset = Task.objects.filter(project=project, level=1)
        
        if assignee == 'me':
            queryset = queryset.filter(assignee=user)
        elif assignee != 'all' and not is_admin:
            # Members can only see their own tasks unless specified
            queryset = queryset.filter(assignee=user)
        
        # Group by status
        columns = [
            {'id': 'planning', 'title': '规划中', 'color': '#94A3B8', 'tasks': []},
            {'id': 'pending', 'title': '待处理', 'color': '#F59E0B', 'tasks': []},
            {'id': 'in_progress', 'title': '进行中', 'color': '#0D9488', 'tasks': []},
            {'id': 'completed', 'title': '已完成', 'color': '#10B981', 'tasks': []},
        ]
        
        column_map = {col['id']: col for col in columns}
        
        for task in queryset.select_related('assignee'):
            task_data = {
                'id': task.id,
                'title': task.title,
                'priority': task.priority,
                'assignee': {
                    'id': task.assignee.id if task.assignee else None,
                    'username': task.assignee.username if task.assignee else None
                } if task.assignee else None,
                'end_date': task.end_date.isoformat() if task.end_date else None,
                'normal_flag': task.normal_flag
            }
            
            if task.status in column_map:
                column_map[task.status]['tasks'].append(task_data)
        
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'project_id': project.id,
                'columns': columns
            }
        })


class CalendarDataView(generics.GenericAPIView):
    """Get calendar data for a project."""
    permission_classes = [IsTeamMember]
    
    def get(self, request, project_id, *args, **kwargs):
        """Get calendar data."""
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            raise ResourceNotFound('项目不存在')
        
        user = request.user
        is_admin = user.is_super_admin or user.is_team_admin
        
        # Get year and month
        year = int(request.query_params.get('year', timezone.now().year))
        month = int(request.query_params.get('month', timezone.now().month))
        
        # Filter by assignee
        assignee = request.query_params.get('assignee', 'all')
        
        # Build queryset
        queryset = Task.objects.filter(project=project, level=1)
        
        if assignee == 'me':
            queryset = queryset.filter(assignee=user)
        elif assignee != 'all' and not is_admin:
            queryset = queryset.filter(assignee=user)
        
        # Filter by month
        from calendar import monthrange
        _, last_day = monthrange(year, month)
        month_start = f"{year}-{month:02d}-01"
        month_end = f"{year}-{month:02d}-{last_day}"
        
        queryset = queryset.filter(
            Q(start_date__lte=month_end, end_date__gte=month_start) |
            Q(start_date__isnull=True, end_date__gte=month_start) |
            Q(end_date__isnull=True, start_date__lte=month_end)
        )
        
        # Group by date
        days = {}
        for task in queryset.select_related('assignee'):
            # Get task dates
            start = task.start_date
            end = task.end_date
            
            if not start and not end:
                continue
            
            if not start:
                start = end
            if not end:
                end = start
            
            # Add task to each day in range
            current = start
            while current <= end:
                date_str = current.isoformat()
                if date_str not in days:
                    days[date_str] = []
                
                days[date_str].append({
                    'id': task.id,
                    'title': task.title,
                    'status': task.status,
                    'priority': task.priority,
                    'assignee': {
                        'id': task.assignee.id if task.assignee else None,
                        'username': task.assignee.username if task.assignee else None
                    } if task.assignee else None
                })
                
                current += timedelta(days=1)
        
        # Format response
        days_list = [
            {'date': date, 'tasks': tasks}
            for date, tasks in sorted(days.items())
        ]
        
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'project_id': project.id,
                'year': year,
                'month': month,
                'days': days_list
            }
        })


class GlobalKanbanView(generics.GenericAPIView):
    """Get global kanban data across projects."""
    permission_classes = [IsTeamMember]
    
    def get(self, request, *args, **kwargs):
        """Get global kanban data."""
        user = request.user
        is_admin = user.is_super_admin or user.is_team_admin
        
        # Filter by project
        project_id = request.query_params.get('project_id')
        
        # Build queryset
        if is_admin:
            queryset = Task.objects.filter(level=1)
        else:
            queryset = Task.objects.filter(level=1, assignee=user)
        
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        else:
            # Filter by user's projects
            queryset = queryset.filter(
                Q(project__team=user.team) |
                Q(project__members=user)
            )
        
        # Group by status
        columns = [
            {'id': 'planning', 'title': '规划中', 'color': '#94A3B8', 'tasks': []},
            {'id': 'pending', 'title': '待处理', 'color': '#F59E0B', 'tasks': []},
            {'id': 'in_progress', 'title': '进行中', 'color': '#0D9488', 'tasks': []},
            {'id': 'completed', 'title': '已完成', 'color': '#10B981', 'tasks': []},
        ]
        
        column_map = {col['id']: col for col in columns}
        
        for task in queryset.select_related('assignee', 'project'):
            task_data = {
                'id': task.id,
                'title': task.title,
                'priority': task.priority,
                'assignee': {
                    'id': task.assignee.id if task.assignee else None,
                    'username': task.assignee.username if task.assignee else None
                } if task.assignee else None,
                'project': {
                    'id': task.project.id,
                    'title': task.project.title
                },
                'end_date': task.end_date.isoformat() if task.end_date else None,
                'normal_flag': task.normal_flag
            }
            
            if task.status in column_map:
                column_map[task.status]['tasks'].append(task_data)
        
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'columns': columns
            }
        })


class GlobalGanttView(generics.GenericAPIView):
    """Get global Gantt data across projects."""
    permission_classes = [IsTeamMember]
    
    def get(self, request, *args, **kwargs):
        """Get global Gantt data."""
        user = request.user
        is_admin = user.is_super_admin or user.is_team_admin
        
        # Get date range
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        view_mode = request.query_params.get('view_mode', 'day')
        project_id = request.query_params.get('project_id')
        
        # Build queryset
        if is_admin:
            queryset = Task.objects.filter(level=1)
        else:
            queryset = Task.objects.filter(level=1, assignee=user)
        
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        else:
            queryset = queryset.filter(
                Q(project__team=user.team) |
                Q(project__members=user)
            )
        
        # Apply date filter
        if start_date:
            queryset = queryset.filter(end_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(start_date__lte=end_date)
        
        # Get default date range
        if not start_date or not end_date:
            today = timezone.now().date()
            week_start = today - timedelta(days=today.weekday())
            week_end = week_start + timedelta(days=6)
            start_date = week_start.isoformat()
            end_date = week_end.isoformat()
        
        # Build task list
        tasks_data = []
        project_colors = {}
        color_palette = ['#0D9488', '#0891B2', '#10B981', '#F59E0B', '#F43F5E', '#8B5CF6']
        
        for task in queryset.select_related('assignee', 'project'):
            # Assign color to project
            if task.project_id not in project_colors:
                project_colors[task.project_id] = color_palette[len(project_colors) % len(color_palette)]
            
            tasks_data.append({
                'id': task.id,
                'title': task.title,
                'start': task.start_date.isoformat() if task.start_date else None,
                'end': task.end_date.isoformat() if task.end_date else None,
                'progress': 100 if task.status == 'completed' else (
                    50 if task.status == 'in_progress' else 0
                ),
                'status': task.status,
                'assignee': {
                    'id': task.assignee.id if task.assignee else None,
                    'username': task.assignee.username if task.assignee else None
                } if task.assignee else None,
                'project': {
                    'id': task.project.id,
                    'title': task.project.title
                },
                'level': task.level,
                'children': []
            })
        
        # Build projects list
        projects = []
        for project_id, color in project_colors.items():
            try:
                project = Project.objects.get(id=project_id)
                projects.append({
                    'id': project.id,
                    'title': project.title,
                    'color': color
                })
            except Project.DoesNotExist:
                pass
        
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'view_mode': view_mode,
                'date_range': {
                    'start': start_date,
                    'end': end_date
                },
                'tasks': tasks_data,
                'projects': projects
            }
        })


class GlobalCalendarView(generics.GenericAPIView):
    """Get global calendar data across projects."""
    permission_classes = [IsTeamMember]
    
    def get(self, request, *args, **kwargs):
        """Get global calendar data."""
        user = request.user
        is_admin = user.is_super_admin or user.is_team_admin
        
        # Get year and month
        year = int(request.query_params.get('year', timezone.now().year))
        month = int(request.query_params.get('month', timezone.now().month))
        project_id = request.query_params.get('project_id')
        
        # Build queryset
        if is_admin:
            queryset = Task.objects.filter(level=1)
        else:
            queryset = Task.objects.filter(level=1, assignee=user)
        
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        else:
            queryset = queryset.filter(
                Q(project__team=user.team) |
                Q(project__members=user)
            )
        
        # Filter by month
        from calendar import monthrange
        _, last_day = monthrange(year, month)
        month_start = f"{year}-{month:02d}-01"
        month_end = f"{year}-{month:02d}-{last_day}"
        
        queryset = queryset.filter(
            Q(start_date__lte=month_end, end_date__gte=month_start) |
            Q(start_date__isnull=True, end_date__gte=month_start) |
            Q(end_date__isnull=True, start_date__lte=month_end)
        )
        
        # Group by date
        days = {}
        for task in queryset.select_related('assignee', 'project'):
            start = task.start_date
            end = task.end_date
            
            if not start and not end:
                continue
            
            if not start:
                start = end
            if not end:
                end = start
            
            current = start
            while current <= end:
                date_str = current.isoformat()
                if date_str not in days:
                    days[date_str] = []
                
                days[date_str].append({
                    'id': task.id,
                    'title': task.title,
                    'status': task.status,
                    'priority': task.priority,
                    'assignee': {
                        'id': task.assignee.id if task.assignee else None,
                        'username': task.assignee.username if task.assignee else None
                    } if task.assignee else None,
                    'project': {
                        'id': task.project.id,
                        'title': task.project.title
                    }
                })
                
                current += timedelta(days=1)
        
        # Format response
        days_list = [
            {'date': date, 'tasks': tasks}
            for date, tasks in sorted(days.items())
        ]
        
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'year': year,
                'month': month,
                'days': days_list
            }
        })


class GlobalTaskListView(generics.GenericAPIView):
    """Get global task list across projects."""
    permission_classes = [IsTeamMember]
    
    def get(self, request, *args, **kwargs):
        """Get global task list."""
        user = request.user
        is_admin = user.is_super_admin or user.is_team_admin
        
        # Filters
        project_id = request.query_params.get('project_id')
        status = request.query_params.get('status')
        priority = request.query_params.get('priority')
        assignee = request.query_params.get('assignee')
        search = request.query_params.get('search')
        sort_by = request.query_params.get('sort_by', 'created_at')
        sort_order = request.query_params.get('sort_order', 'desc')
        
        # Build queryset
        if is_admin:
            queryset = Task.objects.filter(level=1)
        else:
            queryset = Task.objects.filter(level=1, assignee=user)
        
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        else:
            queryset = queryset.filter(
                Q(project__team=user.team) |
                Q(project__members=user)
            )
        
        # Apply filters
        if status:
            statuses = status.split(',')
            queryset = queryset.filter(status__in=statuses)
        
        if priority:
            queryset = queryset.filter(priority=priority)
        
        if assignee == 'me':
            queryset = queryset.filter(assignee=user)
        elif assignee and assignee != 'all':
            queryset = queryset.filter(assignee_id=assignee)
        
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )
        
        # Apply sorting
        order_prefix = '-' if sort_order == 'desc' else ''
        queryset = queryset.order_by(f"{order_prefix}{sort_by}")
        
        # Paginate
        from config.pagination import StandardPagination
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset.select_related('assignee', 'project'), request)
        
        if page is not None:
            data = []
            for task in page:
                data.append({
                    'id': task.id,
                    'title': task.title,
                    'status': task.status,
                    'priority': task.priority,
                    'level': task.level,
                    'assignee': {
                        'id': task.assignee.id if task.assignee else None,
                        'username': task.assignee.username if task.assignee else None
                    } if task.assignee else None,
                    'project': {
                        'id': task.project.id,
                        'title': task.project.title
                    },
                    'start_date': task.start_date.isoformat() if task.start_date else None,
                    'end_date': task.end_date.isoformat() if task.end_date else None,
                    'normal_flag': task.normal_flag,
                    'created_at': task.created_at.isoformat()
                })
            return paginator.get_paginated_response(data)
        
        # No pagination
        data = []
        for task in queryset.select_related('assignee', 'project'):
            data.append({
                'id': task.id,
                'title': task.title,
                'status': task.status,
                'priority': task.priority,
                'level': task.level,
                'assignee': {
                    'id': task.assignee.id if task.assignee else None,
                    'username': task.assignee.username if task.assignee else None
                } if task.assignee else None,
                'project': {
                    'id': task.project.id,
                    'title': task.project.title
                },
                'start_date': task.start_date.isoformat() if task.start_date else None,
                'end_date': task.end_date.isoformat() if task.end_date else None,
                'normal_flag': task.normal_flag,
                'created_at': task.created_at.isoformat()
            })
        
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'items': data
            }
        })
