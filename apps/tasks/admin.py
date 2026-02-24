"""
Tasks admin configuration.
"""
from django.contrib import admin
from .models import Task, TaskHistory, TaskAttachment


class TaskHistoryInline(admin.TabularInline):
    """Task history inline admin."""
    model = TaskHistory
    extra = 0
    readonly_fields = ['changed_by', 'field_name', 'old_value', 'new_value', 'changed_at']
    can_delete = False


class TaskAttachmentInline(admin.TabularInline):
    """Task attachment inline admin."""
    model = TaskAttachment
    extra = 0
    readonly_fields = ['file_name', 'file_type', 'file_size', 'uploaded_by', 'created_at']


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """Task admin configuration."""
    list_display = [
        'title', 'project', 'assignee', 'status', 'priority',
        'level', 'normal_flag', 'end_date', 'created_at'
    ]
    list_filter = ['status', 'priority', 'level', 'normal_flag', 'project']
    search_fields = ['title', 'description']
    ordering = ['-created_at']
    inlines = [TaskHistoryInline, TaskAttachmentInline]
    
    fieldsets = (
        (None, {'fields': ('title', 'description')}),
        ('归属', {'fields': ('project', 'assignee')}),
        ('状态', {'fields': ('status', 'priority')}),
        ('层级', {'fields': ('level', 'parent', 'path')}),
        ('时间', {'fields': ('start_date', 'end_date')}),
        ('逾期', {'fields': ('normal_flag', 'is_overdue_notified', 'is_due_notified')}),
    )


@admin.register(TaskHistory)
class TaskHistoryAdmin(admin.ModelAdmin):
    """Task history admin configuration."""
    list_display = ['task', 'field_name', 'old_value', 'new_value', 'changed_by', 'changed_at']
    list_filter = ['field_name', 'changed_at']
    search_fields = ['task__title']
    ordering = ['-changed_at']
    readonly_fields = ['changed_at']


@admin.register(TaskAttachment)
class TaskAttachmentAdmin(admin.ModelAdmin):
    """Task attachment admin configuration."""
    list_display = ['file_name', 'task', 'file_type', 'file_size', 'uploaded_by', 'created_at']
    list_filter = ['file_type', 'created_at']
    search_fields = ['file_name', 'task__title']
    ordering = ['-created_at']
