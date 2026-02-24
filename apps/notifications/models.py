"""
Notifications models for TeamSync.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _


class NotificationType(models.TextChoices):
    """Notification type choices."""
    TASK_ASSIGNED = 'task_assigned', _('任务分配')
    STATUS_CHANGED = 'status_changed', _('状态变更')
    DUE_REMINDER = 'due_reminder', _('截止提醒')
    OVERDUE = 'overdue', _('逾期通知')
    MEMBER_INVITED = 'member_invited', _('成员邀请')


class Notification(models.Model):
    """
    Notification model for storing notifications.
    """
    recipient = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('接收者')
    )
    type = models.CharField(
        _('类型'),
        max_length=30,
        choices=NotificationType.choices
    )
    title = models.CharField(_('标题'), max_length=200)
    content = models.TextField(_('内容'))
    task = models.ForeignKey(
        'tasks.Task',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name=_('相关任务')
    )
    is_read = models.BooleanField(_('是否已读'), default=False)
    read_at = models.DateTimeField(_('阅读时间'), null=True, blank=True)
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    
    # WebSocket delivery tracking
    ws_delivered = models.BooleanField(_('WS已送达'), default=False)
    ws_delivered_at = models.DateTimeField(_('WS送达时间'), null=True, blank=True)

    class Meta:
        db_table = 'notifications'
        verbose_name = _('通知')
        verbose_name_plural = _('通知')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['recipient', 'created_at']),
            models.Index(fields=['type']),
        ]

    def __str__(self):
        return f"{self.recipient.username} - {self.title}"

    @property
    def type_display(self):
        """Get human-readable type name."""
        return self.get_type_display()

    def mark_as_read(self):
        """Mark notification as read."""
        from django.utils import timezone
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=['is_read', 'read_at'])

    def mark_ws_delivered(self):
        """Mark WebSocket as delivered."""
        from django.utils import timezone
        self.ws_delivered = True
        self.ws_delivered_at = timezone.now()
        self.save(update_fields=['ws_delivered', 'ws_delivered_at'])

    def to_dict(self):
        """Convert to dictionary for WebSocket."""
        return {
            'id': self.id,
            'type': self.type,
            'title': self.title,
            'content': self.content,
            'task_id': self.task_id,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat(),
        }
