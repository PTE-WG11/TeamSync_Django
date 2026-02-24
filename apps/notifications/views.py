"""
Notifications views for TeamSync.
"""
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone

from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(generics.ListAPIView):
    """List notifications for current user."""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Filter by read status
        is_read = request.query_params.get('is_read')
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == 'true')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        
        # Get unread count
        unread_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'unread_count': unread_count,
                'items': serializer.data
            }
        })


class NotificationMarkReadView(generics.GenericAPIView):
    """Mark notification as read."""
    permission_classes = [permissions.IsAuthenticated]
    
    def patch(self, request, pk, *args, **kwargs):
        try:
            notification = Notification.objects.get(
                id=pk,
                recipient=request.user
            )
        except Notification.DoesNotExist:
            return Response({
                'code': 404,
                'message': '通知不存在',
                'errors': {}
            }, status=status.HTTP_404_NOT_FOUND)
        
        notification.mark_as_read()
        
        return Response({
            'code': 200,
            'message': '已标记为已读',
            'data': {
                'id': notification.id,
                'is_read': True
            }
        })


class NotificationMarkAllReadView(generics.GenericAPIView):
    """Mark all notifications as read."""
    permission_classes = [permissions.IsAuthenticated]
    
    def patch(self, request, *args, **kwargs):
        notifications = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        )
        
        count = notifications.count()
        notifications.update(is_read=True, read_at=timezone.now())
        
        return Response({
            'code': 200,
            'message': '全部标记为已读',
            'data': {
                'marked_count': count
            }
        })


class NotificationDeleteView(generics.DestroyAPIView):
    """Delete notification."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        try:
            notification = Notification.objects.get(
                id=kwargs.get('pk'),
                recipient=request.user
            )
        except Notification.DoesNotExist:
            return Response({
                'code': 404,
                'message': '通知不存在',
                'errors': {}
            }, status=status.HTTP_404_NOT_FOUND)
        
        self.perform_destroy(notification)
        
        return Response({
            'code': 204,
            'message': '通知已删除',
            'data': None
        })
