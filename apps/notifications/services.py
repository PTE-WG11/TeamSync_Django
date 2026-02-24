"""
Notification services for TeamSync.
"""
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone

from .models import Notification, NotificationType


class NotificationService:
    """Service for handling notifications."""
    
    @staticmethod
    def create_notification(recipient, notification_type, title, content, task=None):
        """Create a notification and send via WebSocket."""
        notification = Notification.objects.create(
            recipient=recipient,
            type=notification_type,
            title=title,
            content=content,
            task=task
        )
        
        # Send via WebSocket
        NotificationService.send_ws_notification(notification)
        
        return notification
    
    @staticmethod
    def send_ws_notification(notification):
        """Send notification via WebSocket."""
        channel_layer = get_channel_layer()
        
        try:
            async_to_sync(channel_layer.group_send)(
                f"user_{notification.recipient.id}",
                {
                    'type': 'notification_message',
                    'message': notification.to_dict()
                }
            )
            notification.mark_ws_delivered()
        except Exception as e:
            # Log error but don't fail
            print(f"Failed to send WebSocket notification: {e}")
    
    @staticmethod
    def send_task_assigned_notification(task):
        """Send notification when task is assigned."""
        if not task.assignee:
            return
        
        NotificationService.create_notification(
            recipient=task.assignee,
            notification_type=NotificationType.TASK_ASSIGNED,
            title='新任务分配',
            content=f'您被分配了新任务：{task.title}',
            task=task
        )
    
    @staticmethod
    def send_status_changed_notification(task, old_status, new_status, changed_by):
        """Send notification when task status changes."""
        if not task.assignee:
            return
        
        # Don't notify if user changed their own task
        if task.assignee == changed_by:
            return
        
        status_map = {
            'planning': '规划中',
            'pending': '待处理',
            'in_progress': '进行中',
            'completed': '已完成'
        }
        
        NotificationService.create_notification(
            recipient=task.assignee,
            notification_type=NotificationType.STATUS_CHANGED,
            title='任务状态变更',
            content=f'任务"{task.title}"状态变为{status_map.get(new_status, new_status)}',
            task=task
        )
    
    @staticmethod
    def send_due_reminder(task):
        """Send due date reminder."""
        if not task.assignee:
            return
        
        NotificationService.create_notification(
            recipient=task.assignee,
            notification_type=NotificationType.DUE_REMINDER,
            title='今日截止提醒',
            content=f'任务"{task.title}"今日截止，请及时处理',
            task=task
        )
    
    @staticmethod
    def send_overdue_notification(task):
        """Send overdue notification."""
        if not task.assignee:
            return
        
        NotificationService.create_notification(
            recipient=task.assignee,
            notification_type=NotificationType.OVERDUE,
            title='任务已逾期',
            content=f'任务"{task.title}"已逾期，请尽快处理',
            task=task
        )
    
    @staticmethod
    def send_member_invited_notification(user, team, invited_by):
        """Send member invited notification."""
        NotificationService.create_notification(
            recipient=user,
            notification_type=NotificationType.MEMBER_INVITED,
            title='团队邀请',
            content=f'您被{invited_by.username}邀请加入团队"{team.name}"',
        )
