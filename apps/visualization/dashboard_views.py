"""
Dashboard views for TeamSync.
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


class MemberDashboardView(generics.GenericAPIView):
    """Get member dashboard data."""
    permission_classes = [IsTeamMember]
    
    def get(self, request, *args, **kwargs):
        """Get member dashboard data."""
        user = request.user
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        # Today's tasks
        today_tasks = Task.objects.filter(
            assignee=user,
            end_date=today,
            status__in=['planning', 'pending', 'in_progress']
        ).select_related('project')
        
        today_data = {
            'total': today_tasks.count(),
            'tasks': [
                {
                    'id': task.id,
                    'title': task.title,
                    'project': task.project.title if task.project else None,
                    'status': task.status,
                    'end_date': task.end_date.isoformat() if task.end_date else None,
                    'is_overdue': task.normal_flag == 'overdue'
                }
                for task in today_tasks
            ]
        }
        
        # This week's tasks
        week_tasks = Task.objects.filter(
            assignee=user,
            end_date__gte=week_start,
            end_date__lte=week_end,
            status__in=['planning', 'pending', 'in_progress']
        ).exclude(end_date=today).select_related('project')
        
        week_data = {
            'total': week_tasks.count(),
            'tasks': [
                {
                    'id': task.id,
                    'title': task.title,
                    'project': task.project.title if task.project else None,
                    'status': task.status,
                    'end_date': task.end_date.isoformat() if task.end_date else None,
                    'is_overdue': task.normal_flag == 'overdue'
                }
                for task in week_tasks
            ]
        }
        
        # Overdue tasks
        overdue_tasks = Task.objects.filter(
            assignee=user,
            normal_flag='overdue',
            status__in=['planning', 'pending', 'in_progress']
        ).select_related('project')
        
        overdue_data = {
            'total': overdue_tasks.count(),
            'tasks': [
                {
                    'id': task.id,
                    'title': task.title,
                    'project': task.project.title if task.project else None,
                    'end_date': task.end_date.isoformat() if task.end_date else None,
                    'is_overdue': True
                }
                for task in overdue_tasks
            ]
        }
        
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'today': today_data,
                'this_week': week_data,
                'overdue': overdue_data
            }
        })


class AdminDashboardView(generics.GenericAPIView):
    """Get admin dashboard data."""
    permission_classes = [IsAdminOrSuperAdmin]
    
    def get(self, request, *args, **kwargs):
        """Get admin dashboard data."""
        user = request.user
        team = user.team
        
        if not team:
            return Response({
                'code': 200,
                'message': 'success',
                'data': {
                    'project_overview': {
                        'total': 0,
                        'active': 0,
                        'archived': 0,
                        'overdue_count': 0
                    },
                    'projects': [],
                    'member_workload': []
                }
            })
        
        # Project overview
        all_projects = Project.objects.filter(team=team)
        active_projects = all_projects.filter(is_archived=False)
        archived_projects = all_projects.filter(is_archived=True)
        
        overdue_count = Task.objects.filter(
            project__team=team,
            normal_flag='overdue',
            status__in=['planning', 'pending', 'in_progress']
        ).count()
        
        project_overview = {
            'total': all_projects.count(),
            'active': active_projects.count(),
            'archived': archived_projects.count(),
            'overdue_count': overdue_count
        }
        
        # Projects list
        projects = []
        for project in active_projects.order_by('-created_at')[:10]:
            projects.append({
                'id': project.id,
                'title': project.title,
                'progress': project.progress,
                'member_count': project.member_count,
                'overdue_task_count': project.overdue_task_count,
                'status': project.status
            })
        
        # Member workload
        member_workload = []
        for member in User.objects.filter(team=team, is_active=True):
            assigned_tasks = Task.objects.filter(
                project__team=team,
                level=1,
                assignee=member
            )
            
            member_workload.append({
                'user_id': member.id,
                'username': member.username,
                'assigned_tasks': assigned_tasks.count(),
                'completed_tasks': assigned_tasks.filter(status='completed').count(),
                'overdue_tasks': assigned_tasks.filter(normal_flag='overdue').count()
            })
        
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'project_overview': project_overview,
                'projects': projects,
                'member_workload': member_workload
            }
        })
