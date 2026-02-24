"""
Notifications serializers for TeamSync.
"""
from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Notification serializer."""
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'type', 'type_display', 'title', 'content',
            'task_id', 'is_read', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class NotificationListSerializer(serializers.Serializer):
    """Notification list response serializer."""
    unread_count = serializers.IntegerField()
    items = NotificationSerializer(many=True)
