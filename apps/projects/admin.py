"""
Projects admin configuration.
"""
from django.contrib import admin
from .models import Project, ProjectMember


class ProjectMemberInline(admin.TabularInline):
    """Project member inline admin."""
    model = ProjectMember
    extra = 1
    autocomplete_fields = ['user']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """Project admin configuration."""
    list_display = [
        'title', 'status', 'team', 'member_count',
        'is_archived', 'progress', 'created_at'
    ]
    list_filter = ['status', 'is_archived', 'team', 'created_at']
    search_fields = ['title', 'description']
    ordering = ['-created_at']
    inlines = [ProjectMemberInline]
    
    fieldsets = (
        (None, {'fields': ('title', 'description')}),
        ('状态', {'fields': ('status', 'team', 'created_by')}),
        ('时间', {'fields': ('start_date', 'end_date')}),
        ('归档', {'fields': ('is_archived', 'archived_at')}),
    )
    readonly_fields = ['archived_at']


@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    """Project member admin configuration."""
    list_display = ['project', 'user', 'joined_at', 'is_active']
    list_filter = ['is_active', 'joined_at']
    search_fields = ['project__title', 'user__username']
    ordering = ['-joined_at']
