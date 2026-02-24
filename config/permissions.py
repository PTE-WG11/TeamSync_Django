"""
Custom permissions for TeamSync.
"""
from rest_framework import permissions


class IsSuperAdmin(permissions.BasePermission):
    """Permission to only allow super admin users."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_superuser


class IsTeamAdmin(permissions.BasePermission):
    """Permission to only allow team admin users."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_team_admin


class IsAdminOrSuperAdmin(permissions.BasePermission):
    """Permission to allow team admin or super admin users."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_team_admin


class IsTeamMember(permissions.BasePermission):
    """Permission to only allow team members (not visitors)."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_team_member


class IsTaskAssignee(permissions.BasePermission):
    """Permission to only allow task assignee."""
    def has_object_permission(self, request, view, obj):
        return obj.assignee_id == request.user.id


class IsTaskAssigneeOrAdmin(permissions.BasePermission):
    """Permission to allow task assignee or admin users."""
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser or request.user.is_team_admin:
            return True
        return obj.assignee_id == request.user.id
