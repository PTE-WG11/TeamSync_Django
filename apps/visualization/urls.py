"""
Visualization URL configuration.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Project visualization
    path('projects/<int:project_id>/gantt/', views.GanttDataView.as_view(), name='project-gantt'),
    path('projects/<int:project_id>/kanban/', views.KanbanDataView.as_view(), name='project-kanban'),
    path('projects/<int:project_id>/calendar/', views.CalendarDataView.as_view(), name='project-calendar'),
    
    # Global visualization
    path('kanban/', views.GlobalKanbanView.as_view(), name='global-kanban'),
    path('gantt/', views.GlobalGanttView.as_view(), name='global-gantt'),
    path('calendar/', views.GlobalCalendarView.as_view(), name='global-calendar'),
    path('list/', views.GlobalTaskListView.as_view(), name='global-task-list'),
]
