"""
Accounts views for TeamSync.
"""
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from django.conf import settings
from datetime import timedelta

from .models import Team, TeamInvitation, UserRole
from .serializers import (
    UserSerializer, UserDetailSerializer, UserRegisterSerializer,
    UserLoginSerializer, TokenResponseSerializer, TeamSerializer,
    TeamMemberSerializer, TeamInvitationSerializer, InviteMemberSerializer,
    ChangeRoleSerializer, ChangePasswordSerializer, UserProfileUpdateSerializer,
    AvatarUploadSerializer
)
from config.permissions import IsAdminOrSuperAdmin, IsTeamMember
from config.exceptions import ValidationError, ResourceNotFound, ResourceConflict

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """User registration view."""
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'code': 201,
            'message': '注册成功',
            'data': {
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh),
                'expires_at': timezone.now() + refresh.access_token.lifetime,
                'user': UserSerializer(user).data
            }
        }, status=status.HTTP_201_CREATED)


class LoginView(generics.GenericAPIView):
    """User login view."""
    serializer_class = UserLoginSerializer
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        
        try:
            user = User.objects.get(
                Q(username=username) | Q(email=username)
            )
        except User.DoesNotExist:
            raise ValidationError('用户名或密码错误')
        
        if not user.check_password(password):
            raise ValidationError('用户名或密码错误')
        
        if not user.is_active:
            raise ValidationError('用户未激活', code=1004)
        
        # Update last login
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'code': 200,
            'message': '登录成功',
            'data': {
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh),
                'expires_at': timezone.now() + refresh.access_token.lifetime,
                'user': UserSerializer(user).data
            }
        })


class LogoutView(generics.GenericAPIView):
    """User logout view."""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass
        
        return Response({
            'code': 200,
            'message': '登出成功',
            'data': None
        })


class CustomTokenRefreshView(TokenRefreshView):
    """Custom token refresh view with standard response format."""
    
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        # Get access token lifetime from settings
        access_lifetime = settings.SIMPLE_JWT.get(
            'ACCESS_TOKEN_LIFETIME', 
            timedelta(minutes=15)
        )
        
        return Response({
            'code': 200,
            'message': '刷新成功',
            'data': {
                'access_token': response.data['access'],
                'expires_at': timezone.now() + access_lifetime
            }
        })


class CurrentUserView(generics.RetrieveAPIView):
    """Get current user info."""
    serializer_class = UserDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'code': 200,
            'message': 'success',
            'data': serializer.data
        })


class UpdateCurrentUserView(generics.UpdateAPIView):
    """Update current user info (supports avatar, username, email, phone)."""
    serializer_class = UserProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response({
            'code': 200,
            'message': '更新成功',
            'data': UserDetailSerializer(instance).data
        })


class ChangePasswordView(generics.GenericAPIView):
    """Change current user password."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChangePasswordSerializer
    
    def post(self, request, *args, **kwargs):
        user = request.user
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check old password
        old_password = serializer.validated_data['old_password']
        if not user.check_password(old_password):
            raise ValidationError('原密码错误')
        
        # Set new password
        new_password = serializer.validated_data['new_password']
        user.set_password(new_password)
        user.save(update_fields=['password'])
        
        return Response({
            'code': 200,
            'message': '密码修改成功',
            'data': None
        })


class AvatarUploadView(generics.GenericAPIView):
    """
    Update user avatar by URL.
    Accepts avatar URL directly.
    For direct file upload, use /me/avatar/upload/ endpoint.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AvatarUploadSerializer
    
    def post(self, request, *args, **kwargs):
        user = request.user
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        avatar_url = serializer.validated_data['avatar']
        user.avatar = avatar_url
        user.save(update_fields=['avatar'])
        
        return Response({
            'code': 200,
            'message': '头像更新成功',
            'data': {
                'avatar': user.avatar
            }
        })


class AvatarDirectUploadView(generics.GenericAPIView):
    """
    Direct upload avatar file.
    One-step upload: file -> MinIO/OSS -> update user avatar.
    
    Accepts multipart/form-data with 'avatar' field.
    Supports: jpg, jpeg, png, gif, webp
    Max size: 5MB
    """
    permission_classes = [permissions.IsAuthenticated]
    
    # Allowed image types
    ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/jpg']
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    
    def post(self, request, *args, **kwargs):
        user = request.user
        
        # Check if file is provided
        if 'avatar' not in request.FILES:
            raise ValidationError('请选择要上传的头像文件', code=4001)
        
        file = request.FILES['avatar']
        
        # Validate file type
        if file.content_type not in self.ALLOWED_IMAGE_TYPES:
            raise ValidationError(
                f'不支持的图片格式: {file.content_type}。仅支持: JPG, PNG, GIF, WebP',
                code=4002
            )
        
        # Validate file size
        if file.size > self.MAX_FILE_SIZE:
            max_size_mb = self.MAX_FILE_SIZE // 1024 // 1024
            raise ValidationError(f'图片大小不能超过 {max_size_mb}MB', code=4003)
        
        # Generate file key for avatar
        import uuid
        ext = file.name.split('.')[-1].lower() if '.' in file.name else 'png'
        file_key = f"avatars/{user.id}/{uuid.uuid4().hex[:8]}.{ext}"
        
        # Upload to storage
        try:
            from apps.files.storage import StorageFactory
            storage = StorageFactory.get_storage()
            
            # Upload file content
            file_content = file.read()
            
            # For MinIO, we need to use put_object
            if hasattr(storage, 'client'):
                # MinIO storage
                from io import BytesIO
                storage.client.put_object(
                    storage.bucket_name,
                    file_key,
                    BytesIO(file_content),
                    length=len(file_content),
                    content_type=file.content_type
                )
                # Get public URL
                avatar_url = storage.get_file_url(file_key)
            else:
                # OSS or other storage - use presigned URL approach
                upload_url = storage.get_upload_url(file_key, file.content_type, expires=300)
                import requests
                requests.put(upload_url, data=file_content, headers={'Content-Type': file.content_type})
                avatar_url = storage.get_file_url(file_key)
                
        except Exception as e:
            raise ValidationError(f'头像上传失败: {str(e)}', code=5001)
        
        # Delete old avatar file if exists (optional, can be disabled)
        old_avatar = user.avatar
        if old_avatar and hasattr(storage, 'delete_file'):
            try:
                # Extract file key from URL
                old_key = old_avatar.split('/')[-1]
                if old_key:
                    storage.delete_file(f"avatars/{user.id}/{old_key}")
            except:
                pass  # Ignore deletion errors
        
        # Update user avatar
        user.avatar = avatar_url
        user.save(update_fields=['avatar'])
        
        return Response({
            'code': 200,
            'message': '头像上传成功',
            'data': {
                'avatar': user.avatar,
                'user': UserDetailSerializer(user).data
            }
        })


# Team Management Views
class TeamMemberListView(generics.ListAPIView):
    """List team members."""
    serializer_class = TeamMemberSerializer
    permission_classes = [IsAdminOrSuperAdmin]
    
    def get_queryset(self):
        team = self.request.user.team
        if not team:
            return User.objects.none()
        return User.objects.filter(
            team=team,
            is_active=True
        ).exclude(role=UserRole.SUPER_ADMIN)
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Apply role filter
        role = request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        
        # Apply search filter
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search)
            )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'items': serializer.data
            }
        })


class InviteMemberView(generics.CreateAPIView):
    """Invite member to team."""
    serializer_class = InviteMemberSerializer
    permission_classes = [IsAdminOrSuperAdmin]
    
    def create(self, request, *args, **kwargs):
        team = request.user.team
        if not team:
            raise ValidationError('您不属于任何团队')
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        invited_user = serializer.context['invited_user']
        role = serializer.validated_data['role']
        
        # Check if invitation already exists
        if TeamInvitation.objects.filter(
            team=team,
            user=invited_user,
            is_accepted=False
        ).exists():
            raise ResourceConflict('该用户已被邀请')
        
        # Create invitation
        invitation = TeamInvitation.objects.create(
            team=team,
            user=invited_user,
            invited_by=request.user,
            role=role,
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        # Auto-accept invitation (as per requirement)
        invitation.accept()
        
        return Response({
            'code': 200,
            'message': '邀请成功',
            'data': {
                'user_id': invited_user.id,
                'username': invited_user.username,
                'role': role,
                'invited_at': invitation.created_at
            }
        })


class ChangeMemberRoleView(generics.UpdateAPIView):
    """Change member role."""
    serializer_class = ChangeRoleSerializer
    permission_classes = [IsAdminOrSuperAdmin]
    queryset = User.objects.all()
    lookup_url_kwarg = 'pk'
    
    def update(self, request, *args, **kwargs):
        team = request.user.team
        user = self.get_object()
        
        if user.team != team:
            raise ValidationError('该用户不属于您的团队')
        
        # Cannot change own role
        if user == request.user:
            raise ValidationError('不能修改自己的角色')
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        new_role = serializer.validated_data['role']
        user.role = new_role
        user.save(update_fields=['role'])
        
        return Response({
            'code': 200,
            'message': '角色修改成功',
            'data': {
                'user_id': user.id,
                'username': user.username,
                'role': new_role,
                'updated_at': timezone.now()
            }
        })


class RemoveMemberView(generics.DestroyAPIView):
    """Remove member from team."""
    permission_classes = [IsAdminOrSuperAdmin]
    queryset = User.objects.all()
    lookup_url_kwarg = 'pk'
    
    def destroy(self, request, *args, **kwargs):
        team = request.user.team
        user = self.get_object()
        
        if user.team != team:
            raise ValidationError('该用户不属于您的团队')
        
        if user == request.user:
            raise ValidationError('不能移除自己')
        
        user.leave_team()
        
        return Response({
            'code': 204,
            'message': '成员已移除',
            'data': None
        })


class CheckUserInviteView(generics.GenericAPIView):
    """Check if a user can be invited to the team."""
    permission_classes = [IsAdminOrSuperAdmin]
    
    def get(self, request, *args, **kwargs):
        username = request.query_params.get('username')
        
        if not username:
            raise ValidationError('请提供用户名')
        
        team = request.user.team
        if not team:
            raise ValidationError('您不属于任何团队')
        
        # Check if user exists
        try:
            user = User.objects.get(username=username)
            user_exists = True
        except User.DoesNotExist:
            user_exists = False
        
        if not user_exists:
            return Response({
                'code': 200,
                'message': 'success',
                'data': {
                    'exists': False,
                    'available': False,
                    'message': '用户不存在'
                }
            })
        
        # Check if user is already in the team
        if user.team == team:
            return Response({
                'code': 200,
                'message': 'success',
                'data': {
                    'exists': True,
                    'available': False,
                    'message': '用户已在团队中'
                }
            })
        
        # User exists and is not in the team
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'exists': True,
                'available': True,
                'message': '用户可以邀请'
            }
        })


# Visitor waiting view
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def visitor_status(request):
    """Get visitor status."""
    user = request.user
    
    if not user.is_visitor:
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'is_visitor': False,
                'role': user.role,
                'team': user.team.name if user.team else None
            }
        })
    
    # Check for pending invitations
    invitations = TeamInvitation.objects.filter(
        user=user,
        is_accepted=False,
        expires_at__gt=timezone.now()
    )
    
    return Response({
        'code': 200,
        'message': 'success',
        'data': {
            'is_visitor': True,
            'message': '您已注册成功，请联系团队管理员将您加入团队以开始协作',
            'pending_invitations': TeamInvitationSerializer(
                invitations, many=True
            ).data
        }
    })
