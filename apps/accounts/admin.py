"""
Accounts admin configuration.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, Team, TeamInvitation


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """User admin configuration."""
    list_display = [
        'username', 'email', 'role', 'team', 'is_active',
        'created_at', 'last_login'
    ]
    list_filter = ['role', 'is_active', 'team', 'created_at']
    search_fields = ['username', 'email', 'phone']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('个人信息'), {'fields': ('email', 'avatar', 'phone')}),
        (_('团队信息'), {'fields': ('team', 'role')}),
        (_('权限'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('重要日期'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'team'),
        }),
    )


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    """Team admin configuration."""
    list_display = ['name', 'owner', 'member_count', 'admin_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {'fields': ('name', 'description')}),
        (_('状态'), {'fields': ('owner', 'is_active')}),
    )


@admin.register(TeamInvitation)
class TeamInvitationAdmin(admin.ModelAdmin):
    """Team invitation admin configuration."""
    list_display = ['team', 'user', 'invited_by', 'role', 'is_accepted', 'created_at']
    list_filter = ['is_accepted', 'role', 'created_at']
    search_fields = ['team__name', 'user__username', 'user__email']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {'fields': ('team', 'user', 'invited_by')}),
        (_('邀请信息'), {'fields': ('role', 'is_accepted', 'accepted_at')}),
        (_('时间'), {'fields': ('created_at', 'expires_at')}),
    )
    readonly_fields = ['created_at']
