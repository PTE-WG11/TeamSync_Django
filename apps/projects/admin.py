"""
Projects admin configuration.
"""
from django.contrib import admin
from .models import (
    Project, ProjectMember,
    Folder, ProjectDocument, DocumentComment
)


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


# =============================================================================
# Document Admin
# =============================================================================

@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    """Folder admin configuration."""
    list_display = ['name', 'project', 'sort_order', 'document_count', 'created_by', 'created_at']
    list_filter = ['project', 'created_at']
    search_fields = ['name', 'project__title']
    ordering = ['project', 'sort_order', '-created_at']
    autocomplete_fields = ['project', 'created_by']
    
    fieldsets = (
        (None, {'fields': ('project', 'name')}),
        ('排序', {'fields': ('sort_order',)}),
        ('创建信息', {'fields': ('created_by', 'created_at', 'updated_at')}),
    )
    readonly_fields = ['created_at', 'updated_at']


class DocumentCommentInline(admin.TabularInline):
    """Document comment inline admin."""
    model = DocumentComment
    extra = 0
    readonly_fields = ['created_at']
    autocomplete_fields = ['author']


@admin.register(ProjectDocument)
class ProjectDocumentAdmin(admin.ModelAdmin):
    """Project document admin configuration."""
    list_display = [
        'title', 'doc_type', 'status', 'project', 'folder',
        'file_size_display', 'uploaded_by', 'created_at'
    ]
    list_filter = ['doc_type', 'status', 'project', 'created_at']
    search_fields = ['title', 'file_name', 'project__title', 'content']
    ordering = ['-created_at']
    autocomplete_fields = ['project', 'folder', 'uploaded_by']
    inlines = [DocumentCommentInline]
    
    fieldsets = (
        (None, {
            'fields': ('project', 'folder', 'title')
        }),
        ('文档类型与状态', {
            'fields': ('doc_type', 'status')
        }),
        ('文件信息', {
            'fields': ('file_key', 'file_name', 'file_type', 'file_size'),
            'classes': ('collapse',)
        }),
        ('Markdown 内容', {
            'fields': ('content',),
            'classes': ('collapse',)
        }),
        ('上传信息', {
            'fields': ('uploaded_by', 'created_at', 'updated_at')
        }),
    )
    readonly_fields = ['created_at', 'updated_at']
    
    def file_size_display(self, obj):
        """Display file size in human readable format."""
        if obj.file_size < 1024:
            return f"{obj.file_size} B"
        elif obj.file_size < 1024 * 1024:
            return f"{obj.file_size / 1024:.1f} KB"
        else:
            return f"{obj.file_size / (1024 * 1024):.1f} MB"
    file_size_display.short_description = '文件大小'


@admin.register(DocumentComment)
class DocumentCommentAdmin(admin.ModelAdmin):
    """Document comment admin configuration."""
    list_display = ['document', 'author', 'content_preview', 'created_at']
    list_filter = ['created_at']
    search_fields = ['content', 'document__title', 'author__username']
    ordering = ['-created_at']
    autocomplete_fields = ['document', 'author']
    
    fieldsets = (
        (None, {'fields': ('document', 'author')}),
        ('评论内容', {'fields': ('content',)}),
        ('时间', {'fields': ('created_at', 'updated_at')}),
    )
    readonly_fields = ['created_at', 'updated_at']
    
    def content_preview(self, obj):
        """Preview comment content."""
        if len(obj.content) > 50:
            return obj.content[:50] + '...'
        return obj.content
    content_preview.short_description = '评论内容'
