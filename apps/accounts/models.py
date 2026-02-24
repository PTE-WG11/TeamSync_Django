"""
Accounts models for TeamSync.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserRole(models.TextChoices):
    """User role choices."""
    SUPER_ADMIN = 'super_admin', _('超级管理员')
    TEAM_ADMIN = 'team_admin', _('团队管理员')
    MEMBER = 'member', _('团队成员')
    VISITOR = 'visitor', _('访客')


class User(AbstractUser):
    """
    Custom User model with team and role support.
    """
    email = models.EmailField(_('邮箱'), unique=True)
    role = models.CharField(
        _('角色'),
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.VISITOR
    )
    team = models.ForeignKey(
        'Team',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
        verbose_name=_('所属团队')
    )
    avatar = models.URLField(_('头像'), blank=True, default='')
    phone = models.CharField(_('手机号'), max_length=20, blank=True, default='')
    is_active = models.BooleanField(_('是否激活'), default=True)
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)
    last_login_ip = models.GenericIPAddressField(_('最后登录IP'), null=True, blank=True)

    class Meta:
        db_table = 'users'
        verbose_name = _('用户')
        verbose_name_plural = _('用户')
        ordering = ['-created_at']

    def __str__(self):
        return self.username

    @property
    def is_super_admin(self):
        """Check if user is super admin."""
        return self.role == UserRole.SUPER_ADMIN or self.is_superuser

    @property
    def is_team_admin(self):
        """Check if user is team admin."""
        return self.role == UserRole.TEAM_ADMIN

    @property
    def is_team_member(self):
        """Check if user is team member (admin or member)."""
        return self.role in [UserRole.TEAM_ADMIN, UserRole.MEMBER, UserRole.SUPER_ADMIN]

    @property
    def is_visitor(self):
        """Check if user is visitor."""
        return self.role == UserRole.VISITOR

    @property
    def role_display(self):
        """Get human-readable role name."""
        return self.get_role_display()

    def join_team(self, team, role=UserRole.MEMBER):
        """Join a team with specified role."""
        self.team = team
        self.role = role
        self.save(update_fields=['team', 'role'])

    def leave_team(self):
        """Leave current team and become visitor."""
        self.team = None
        self.role = UserRole.VISITOR
        self.save(update_fields=['team', 'role'])


class Team(models.Model):
    """
    Team model for organizing users.
    """
    name = models.CharField(_('团队名称'), max_length=100)
    description = models.TextField(_('团队描述'), blank=True, default='')
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='owned_teams',
        verbose_name=_('团队所有者')
    )
    is_active = models.BooleanField(_('是否激活'), default=True)
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)

    class Meta:
        db_table = 'teams'
        verbose_name = _('团队')
        verbose_name_plural = _('团队')
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def member_count(self):
        """Get team member count."""
        return self.members.filter(is_active=True).count()

    @property
    def admin_count(self):
        """Get team admin count."""
        return self.members.filter(role=UserRole.TEAM_ADMIN, is_active=True).count()

    def add_member(self, user, role=UserRole.MEMBER):
        """Add a member to the team."""
        user.join_team(self, role)

    def remove_member(self, user):
        """Remove a member from the team."""
        if user.team == self:
            user.leave_team()

    def has_member(self, user):
        """Check if user is a member of this team."""
        return user.team == self and user.is_active


class TeamInvitation(models.Model):
    """
    Team invitation record.
    """
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='invitations',
        verbose_name=_('团队')
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='team_invitations',
        verbose_name=_('被邀请用户')
    )
    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_invitations',
        verbose_name=_('邀请人')
    )
    role = models.CharField(
        _('角色'),
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.MEMBER
    )
    is_accepted = models.BooleanField(_('是否接受'), default=False)
    accepted_at = models.DateTimeField(_('接受时间'), null=True, blank=True)
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    expires_at = models.DateTimeField(_('过期时间'), null=True, blank=True)

    class Meta:
        db_table = 'team_invitations'
        verbose_name = _('团队邀请')
        verbose_name_plural = _('团队邀请')
        ordering = ['-created_at']
        unique_together = ['team', 'user']

    def __str__(self):
        return f"{self.team.name} -> {self.user.username}"

    def accept(self):
        """Accept the invitation."""
        from django.utils import timezone
        self.is_accepted = True
        self.accepted_at = timezone.now()
        self.save(update_fields=['is_accepted', 'accepted_at'])
        self.user.join_team(self.team, self.role)

    def reject(self):
        """Reject the invitation."""
        self.delete()
