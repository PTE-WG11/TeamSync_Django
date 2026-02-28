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


# =============================================================================
# Project Document Models
# =============================================================================

class Folder(models.Model):
    """
    Document folder for project - flat structure (single level only).
    """
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='folders',
        verbose_name=_('所属项目')
    )
    name = models.CharField(_('文件夹名称'), max_length=100)
    sort_order = models.PositiveIntegerField(_('排序'), default=0)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_folders',
        verbose_name=_('创建者')
    )
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)

    class Meta:
        db_table = 'project_folders'
        verbose_name = _('项目文件夹')
        verbose_name_plural = _('项目文件夹')
        ordering = ['sort_order', '-created_at']
        indexes = [
            models.Index(fields=['project', 'sort_order']),
        ]

    def __str__(self):
        return f"{self.project.title} - {self.name}"

    @property
    def document_count(self):
        """Get document count in this folder."""
        return self.documents.count()


class DocumentType(models.TextChoices):
    """Document type choices."""
    MARKDOWN = 'markdown', _('Markdown')
    WORD = 'word', _('Word')
    EXCEL = 'excel', _('Excel')
    PPT = 'ppt', _('PPT')
    PDF = 'pdf', _('PDF')
    IMAGE = 'image', _('图片')
    OTHER = 'other', _('其他')


class DocumentStatus(models.TextChoices):
    """Document status choices."""
    EDITABLE = 'editable', _('可编辑')
    READONLY = 'readonly', _('只读')


class ProjectDocument(models.Model):
    """
    Project document model.
    - Markdown: supports create/edit online, content stored in DB
    - Other files: upload/download only, stored in MinIO/OSS
    """
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name=_('所属项目')
    )
    folder = models.ForeignKey(
        Folder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents',
        verbose_name=_('所属文件夹')
    )
    title = models.CharField(_('文档标题'), max_length=200)
    doc_type = models.CharField(
        _('文档类型'),
        max_length=20,
        choices=DocumentType.choices,
        default=DocumentType.OTHER
    )
    status = models.CharField(
        _('状态'),
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.EDITABLE
    )

    # File info (for uploaded files)
    file_key = models.CharField(_('文件Key'), max_length=500, blank=True, default='')
    file_name = models.CharField(_('文件名'), max_length=255, blank=True, default='')
    file_size = models.BigIntegerField(_('文件大小'), default=0)
    file_type = models.CharField(_('MIME类型'), max_length=100, blank=True, default='')

    # Content (for markdown only)
    content = models.TextField(_('内容'), blank=True, default='')

    # Uploader info
    uploaded_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_documents',
        verbose_name=_('上传者')
    )

    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)

    class Meta:
        db_table = 'project_documents'
        verbose_name = _('项目文档')
        verbose_name_plural = _('项目文档')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'folder', '-created_at']),
            models.Index(fields=['project', 'doc_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.title

    @property
    def is_markdown(self):
        """Check if document is markdown."""
        return self.doc_type == DocumentType.MARKDOWN

    @property
    def can_edit(self):
        """Check if document can be edited."""
        return self.is_markdown and self.status == DocumentStatus.EDITABLE

    @property
    def file_extension(self):
        """Get file extension."""
        if self.file_name and '.' in self.file_name:
            return self.file_name.split('.')[-1].lower()
        return ''

    def get_storage_file_key(self, file_name=None):
        """Generate storage file key for this document."""
        import uuid

        name = file_name or self.file_name
        if name and '.' in name:
            ext = '.' + name.split('.')[-1].lower()
        else:
            ext = '.md' if self.is_markdown else ''

        unique_id = str(uuid.uuid4())[:8]
        return f"projects/{self.project_id}/documents/{unique_id}{ext}"


class DocumentComment(models.Model):
    """
    Comment on project document.
    """
    document = models.ForeignKey(
        ProjectDocument,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name=_('文档')
    )
    content = models.TextField(_('评论内容'))
    author = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='document_comments',
        verbose_name=_('作者')
    )
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)

    class Meta:
        db_table = 'document_comments'
        verbose_name = _('文档评论')
        verbose_name_plural = _('文档评论')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['document', '-created_at']),
        ]

    def __str__(self):
        return f"{self.document.title} - {self.author.username}"
