"""
Celery tasks for task management.
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta


@shared_task
def check_overdue_tasks():
    """
    Check and mark overdue tasks.
    Run daily at 00:01.
    """
    from .models import Task, OverdueFlag
    from apps.notifications.models import Notification
    from apps.notifications.services import NotificationService
    
    today = timezone.now().date()
    
    # Find tasks that are overdue
    overdue_tasks = Task.objects.filter(
        end_date__lt=today,
        status__in=['planning', 'pending', 'in_progress'],
        normal_flag=OverdueFlag.NORMAL
    )
    
    count = 0
    for task in overdue_tasks:
        # Mark as overdue
        task.normal_flag = OverdueFlag.OVERDUE
        task.save(update_fields=['normal_flag'])
        
        # Send notification
        NotificationService.send_overdue_notification(task)
        
        count += 1
    
    return f"Marked {count} tasks as overdue"


@shared_task
def send_due_reminders():
    """
    Send due date reminders.
    Run daily at 07:00.
    """
    from .models import Task
    from apps.notifications.services import NotificationService
    
    today = timezone.now().date()
    
    # Find tasks due today
    due_tasks = Task.objects.filter(
        end_date=today,
        status__in=['planning', 'pending', 'in_progress'],
        is_due_notified=False
    )
    
    count = 0
    for task in due_tasks:
        # Send reminder
        NotificationService.send_due_reminder(task)
        
        # Mark as notified
        task.is_due_notified = True
        task.save(update_fields=['is_due_notified'])
        
        count += 1
    
    return f"Sent {count} due reminders"
