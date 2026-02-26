"""
Tasks models for TeamSync.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import Q


class TaskStatus(models.TextChoices):
    """Task status choices."""
    PLANNING = 'planning', _('规划中')
    PENDING = 'pending', _('待处理')
    IN_PROGRESS = 'in_progress', _('进行中')
    COMPLETED = 'completed', _('已完成')


class TaskPriority(models.TextChoices):
    """Task priority choices."""
    URGENT = 'urgent', _('紧急')
    HIGH = 'high', _('高')
    MEDIUM = 'medium', _('中')
    LOW = 'low', _('低')


class OverdueFlag(models.TextChoices):
    """Overdue flag choices."""
    NORMAL = 'normal', _('正常')
    OVERDUE = 'overdue', _('已逾期')


class Task(models.Model):
    """
    Task model with hierarchical structure (max 3 levels).
    """
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name=_('所属项目')
    )
    title = models.CharField(_('任务标题'), max_length=200)
    description = models.TextField(_('任务描述'), blank=True, default='')
    assignee = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='assigned_tasks',
        verbose_name=_('负责人')
    )
    status = models.CharField(
        _('状态'),
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.PLANNING
    )
    priority = models.CharField(
        _('优先级'),
        max_length=20,
        choices=TaskPriority.choices,
        default=TaskPriority.MEDIUM
    )
    # Hierarchical fields
    level = models.PositiveSmallIntegerField(
        _('层级'),
        default=1,
        help_text=_('1=主任务, 2=子任务, 3=孙任务')
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name=_('父任务')
    )
    path = models.CharField(
        _('路径'),
        max_length=255,
        blank=True,
        default='',
        help_text=_('路径枚举，如 9/12')
    )
    # Date fields
    start_date = models.DateTimeField(_('开始时间'), null=True, blank=True)
    end_date = models.DateTimeField(_('截止时间'), null=True, blank=True)
    # Overdue tracking
    normal_flag = models.CharField(
        _('正常标识'),
        max_length=20,
        choices=OverdueFlag.choices,
        default=OverdueFlag.NORMAL
    )
    is_overdue_notified = models.BooleanField(_('已发送逾期提醒'), default=False)
    is_due_notified = models.BooleanField(_('已发送截止提醒'), default=False)
    # Metadata
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_tasks',
        verbose_name=_('创建者')
    )

    class Meta:
        db_table = 'tasks'
        verbose_name = _('任务')
        verbose_name_plural = _('任务')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'level']),
            models.Index(fields=['assignee', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['end_date']),
            models.Index(fields=['normal_flag']),
            models.Index(fields=['path']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(level__in=[1, 2, 3]),
                name='valid_task_level'
            ),
        ]

    def __str__(self):
        return self.title

    @property
    def subtask_count(self):
        """Get subtask count."""
        return self.children.count()

    @property
    def completed_subtask_count(self):
        """Get completed subtask count."""
        return self.children.filter(status='completed').count()

    @property
    def is_overdue(self):
        """Check if task is overdue."""
        return self.normal_flag == OverdueFlag.OVERDUE

    @property
    def can_have_subtasks(self):
        """Check if task can have subtasks."""
        return self.level < 3

    @property
    def full_path(self):
        """Get full path including self."""
        if self.path:
            return f"{self.path}/{self.id}"
        return str(self.id)

    def get_ancestors(self):
        """Get all ancestor tasks."""
        if not self.path:
            return Task.objects.none()
        ancestor_ids = [int(id) for id in self.path.strip('/').split('/') if id]
        return Task.objects.filter(id__in=ancestor_ids)

    def get_descendants(self):
        """Get all descendant tasks."""
        return Task.objects.filter(path__startswith=self.full_path)

    def create_subtask(self, **kwargs):
        """Create a subtask under this task."""
        if not self.can_have_subtasks:
            raise ValueError('已达到最大层级深度（3层）')
        
        kwargs['project'] = self.project
        kwargs['level'] = self.level + 1
        kwargs['parent'] = self
        kwargs['path'] = self.full_path
        kwargs['assignee'] = self.assignee  # Inherit assignee
        
        return Task.objects.create(**kwargs)

    def update_status(self, new_status, changed_by=None):
        """Update task status and record history."""
        old_status = self.status
        if old_status != new_status:
            self.status = new_status
            self.save(update_fields=['status', 'updated_at'])
            
            # Record history
            TaskHistory.objects.create(
                task=self,
                changed_by=changed_by,
                field_name='status',
                old_value=old_status,
                new_value=new_status
            )

    def check_overdue(self):
        """Check and update overdue status."""
        from django.utils import timezone
        
        if self.status == 'completed':
            return False
        
        # Compare date part only (ignore time)
        if self.end_date and self.end_date.date() < timezone.now().date():
            if self.normal_flag != OverdueFlag.OVERDUE:
                self.normal_flag = OverdueFlag.OVERDUE
                self.save(update_fields=['normal_flag'])
            return True
        
        return False

    def to_tree_dict(self, include_children=True):
        """Convert to tree dictionary."""
        data = {
            'id': self.id,
            'project_id': self.project_id,
            'title': self.title,
            'description': self.description,
            'assignee_id': self.assignee_id,
            'assignee_name': self.assignee.username if self.assignee else None,
            'assignee_avatar': self.assignee.avatar if self.assignee else None,
            'status': self.status,
            'priority': self.priority,
            'level': self.level,
            'parent_id': self.parent_id,
            'path': self.path,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'normal_flag': self.normal_flag,
            'subtask_count': self.subtask_count,
            'completed_subtask_count': self.completed_subtask_count,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
        
        if include_children and self.can_have_subtasks:
            data['children'] = [
                child.to_tree_dict(include_children=True)
                for child in self.children.all()
            ]
        else:
            data['children'] = []
        
        return data


class TaskHistory(models.Model):
    """
    Task change history for audit.
    """
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='histories',
        verbose_name=_('任务')
    )
    changed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='task_changes',
        verbose_name=_('修改人')
    )
    field_name = models.CharField(_('字段名'), max_length=50)
    old_value = models.CharField(_('旧值'), max_length=255, blank=True, default='')
    new_value = models.CharField(_('新值'), max_length=255, blank=True, default='')
    changed_at = models.DateTimeField(_('修改时间'), auto_now_add=True)

    class Meta:
        db_table = 'task_history'
        verbose_name = _('任务变更历史')
        verbose_name_plural = _('任务变更历史')
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['task', 'changed_at']),
        ]

    def __str__(self):
        return f"{self.task.title} - {self.field_name}"


class TaskAttachment(models.Model):
    """
    Task attachment model.
    """
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name=_('任务')
    )
    file_key = models.CharField(_('文件Key'), max_length=500)
    file_name = models.CharField(_('文件名'), max_length=255)
    file_type = models.CharField(_('文件类型'), max_length=100)
    file_size = models.BigIntegerField(_('文件大小'))
    url = models.URLField(_('文件URL'))
    uploaded_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_attachments',
        verbose_name=_('上传者')
    )
    created_at = models.DateTimeField(_('上传时间'), auto_now_add=True)

    class Meta:
        db_table = 'task_attachments'
        verbose_name = _('任务附件')
        verbose_name_plural = _('任务附件')
        ordering = ['-created_at']

    def __str__(self):
        return self.file_name


class TaskDeleteLog(models.Model):
    """
    Task delete log for audit.
    Records who deleted what task and when.
    """
    # Original task info (snapshot at deletion time)
    original_task_id = models.IntegerField(_('原任务ID'), db_index=True)
    title = models.CharField(_('任务标题'), max_length=200)
    description = models.TextField(_('任务描述'), blank=True, default='')
    project_id = models.IntegerField(_('项目ID'), db_index=True)
    project_title = models.CharField(_('项目标题'), max_length=100, blank=True)
    assignee_id = models.IntegerField(_('负责人ID'), null=True, blank=True)
    assignee_name = models.CharField(_('负责人名称'), max_length=150, blank=True)
    status = models.CharField(_('状态'), max_length=20)
    priority = models.CharField(_('优先级'), max_length=20)
    level = models.PositiveSmallIntegerField(_('层级'), default=1)
    parent_id = models.IntegerField(_('父任务ID'), null=True, blank=True)
    path = models.CharField(_('路径'), max_length=255, blank=True, default='')
    start_date = models.DateTimeField(_('开始时间'), null=True, blank=True)
    end_date = models.DateTimeField(_('截止时间'), null=True, blank=True)
    created_by_id = models.IntegerField(_('创建者ID'), null=True, blank=True)
    created_by_name = models.CharField(_('创建者名称'), max_length=150, blank=True)
    original_created_at = models.DateTimeField(_('原创建时间'), null=True, blank=True)
    
    # Deletion info
    deleted_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='deleted_tasks',
        verbose_name=_('删除人')
    )
    deleted_by_name = models.CharField(_('删除人名称'), max_length=150, blank=True)
    deleted_at = models.DateTimeField(_('删除时间'), auto_now_add=True, db_index=True)
    deletion_reason = models.TextField(_('删除原因'), blank=True, default='')
    
    # Optional: store full task data as JSON for complete recovery if needed
    task_data_json = models.JSONField(_('任务完整数据'), null=True, blank=True)

    class Meta:
        db_table = 'task_delete_logs'
        verbose_name = _('任务删除日志')
        verbose_name_plural = _('任务删除日志')
        ordering = ['-deleted_at']
        indexes = [
            models.Index(fields=['project_id', 'deleted_at']),
            models.Index(fields=['deleted_by', 'deleted_at']),
        ]

    def __str__(self):
        return f"{self.title} (deleted by {self.deleted_by_name})"
