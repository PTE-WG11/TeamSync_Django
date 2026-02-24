"""
Projects models for TeamSync.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import Q


class ProjectStatus(models.TextChoices):
    """Project status choices."""
    PLANNING = 'planning', _('规划中')
    PENDING = 'pending', _('待处理')
    IN_PROGRESS = 'in_progress', _('进行中')
    COMPLETED = 'completed', _('已完成')


class Project(models.Model):
    """
    Project model for organizing tasks.
    """
    title = models.CharField(_('项目标题'), max_length=100)
    description = models.TextField(_('项目描述'), blank=True, default='')
    status = models.CharField(
        _('状态'),
        max_length=20,
        choices=ProjectStatus.choices,
        default=ProjectStatus.PLANNING
    )
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_projects',
        verbose_name=_('创建者')
    )
    team = models.ForeignKey(
        'accounts.Team',
        on_delete=models.CASCADE,
        related_name='projects',
        verbose_name=_('所属团队')
    )
    members = models.ManyToManyField(
        'accounts.User',
        related_name='projects',
        verbose_name=_('项目成员'),
        through='ProjectMember'
    )
    is_archived = models.BooleanField(_('是否归档'), default=False)
    archived_at = models.DateTimeField(_('归档时间'), null=True, blank=True)
    start_date = models.DateField(_('开始日期'), null=True, blank=True)
    end_date = models.DateField(_('结束日期'), null=True, blank=True)
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)

    class Meta:
        db_table = 'projects'
        verbose_name = _('项目')
        verbose_name_plural = _('项目')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['team', 'is_archived']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.title

    @property
    def member_count(self):
        """Get project member count."""
        return self.members.filter(is_active=True).count()

    @property
    def progress(self):
        """Calculate project progress based on main tasks."""
        from apps.tasks.models import Task
        main_tasks = Task.objects.filter(project=self, level=1)
        total = main_tasks.count()
        if total == 0:
            return 0.0
        completed = main_tasks.filter(status='completed').count()
        return round((completed / total) * 100, 2)

    @property
    def overdue_task_count(self):
        """Get overdue task count."""
        from apps.tasks.models import Task
        return Task.objects.filter(
            project=self,
            normal_flag='overdue',
            status__in=['planning', 'pending', 'in_progress']
        ).count()

    @property
    def task_stats(self):
        """Get task statistics."""
        from apps.tasks.models import Task
        main_tasks = Task.objects.filter(project=self, level=1)
        return {
            'total': main_tasks.count(),
            'planning': main_tasks.filter(status='planning').count(),
            'pending': main_tasks.filter(status='pending').count(),
            'in_progress': main_tasks.filter(status='in_progress').count(),
            'completed': main_tasks.filter(status='completed').count(),
            'overdue': self.overdue_task_count
        }

    def archive(self):
        """Archive the project."""
        from django.utils import timezone
        self.is_archived = True
        self.archived_at = timezone.now()
        self.save(update_fields=['is_archived', 'archived_at'])

    def unarchive(self):
        """Unarchive the project."""
        self.is_archived = False
        self.archived_at = None
        self.save(update_fields=['is_archived', 'archived_at'])

    def has_member(self, user):
        """Check if user is a member of this project."""
        return self.members.filter(id=user.id, is_active=True).exists()

    def add_member(self, user):
        """Add a member to the project."""
        ProjectMember.objects.get_or_create(project=self, user=user)

    def add_member_id(self, user_id):
        """Add a member to the project by user ID."""
        ProjectMember.objects.get_or_create(project=self, user_id=user_id)

    def remove_member(self, user):
        """Remove a member from the project."""
        ProjectMember.objects.filter(project=self, user=user).delete()

    def set_members(self, user_ids):
        """Set project members (replace existing)."""
        current_members = set(self.members.values_list('id', flat=True))
        new_members = set(user_ids)
        
        # Remove members not in new list
        to_remove = current_members - new_members
        ProjectMember.objects.filter(project=self, user_id__in=to_remove).delete()
        
        # Add new members
        to_add = new_members - current_members
        for user_id in to_add:
            ProjectMember.objects.get_or_create(project=self, user_id=user_id)


class ProjectMember(models.Model):
    """
    Project membership model.
    """
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='project_members',
        verbose_name=_('项目')
    )
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='project_memberships',
        verbose_name=_('用户')
    )
    joined_at = models.DateTimeField(_('加入时间'), auto_now_add=True)
    is_active = models.BooleanField(_('是否激活'), default=True)

    class Meta:
        db_table = 'project_members'
        verbose_name = _('项目成员')
        verbose_name_plural = _('项目成员')
        unique_together = ['project', 'user']
        ordering = ['-joined_at']

    def __str__(self):
        return f"{self.project.title} - {self.user.username}"
