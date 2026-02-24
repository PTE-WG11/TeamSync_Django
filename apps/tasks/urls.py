"""
Tasks URL configuration.
"""
from django.urls import path
from . import views
from apps.visualization.views import (
    GlobalKanbanView, GlobalGanttView, 
    GlobalCalendarView, GlobalTaskListView
)

urlpatterns = [
    # Global task views
    path('kanban/', GlobalKanbanView.as_view(), name='global-kanban'),
    path('list/', GlobalTaskListView.as_view(), name='global-task-list'),
    path('gantt/', GlobalGanttView.as_view(), name='global-gantt'),
    path('calendar/', GlobalCalendarView.as_view(), name='global-calendar'),
    
    # Project tasks
    path('project/<int:project_id>/', views.ProjectTaskListView.as_view(), name='project-tasks'),
    path('project/<int:project_id>/create/', views.TaskCreateView.as_view(), name='task-create'),
    path('project/<int:project_id>/progress/', views.TaskProgressView.as_view(), name='task-progress'),
    
    # Task detail
    path('<int:pk>/', views.TaskDetailView.as_view(), name='task-detail'),
    path('<int:pk>/update/', views.TaskUpdateView.as_view(), name='task-update'),
    path('<int:pk>/status/', views.TaskStatusUpdateView.as_view(), name='task-status-update'),
    path('<int:pk>/delete/', views.TaskDeleteView.as_view(), name='task-delete'),
    path('<int:pk>/history/', views.TaskHistoryView.as_view(), name='task-history'),
    
    # Subtasks
    path('<int:pk>/subtasks/', views.SubtaskCreateView.as_view(), name='subtask-create'),
]
