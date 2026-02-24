"""
Notifications admin configuration.
"""
from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Notification admin configuration."""
    list_display = [
        'recipient', 'type', 'title', 'is_read',
        'ws_delivered', 'created_at'
    ]
    list_filter = ['type', 'is_read', 'ws_delivered', 'created_at']
    search_fields = ['recipient__username', 'title', 'content']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'read_at', 'ws_delivered_at']
    
    fieldsets = (
        (None, {'fields': ('recipient', 'type', 'title', 'content')}),
        ('关联', {'fields': ('task',)}),
        ('状态', {'fields': ('is_read', 'read_at', 'ws_delivered', 'ws_delivered_at')}),
        ('时间', {'fields': ('created_at',)}),
    )
