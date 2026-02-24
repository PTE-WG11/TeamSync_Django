"""
File storage services for TeamSync.
Supports MinIO and Aliyun OSS.
"""
import uuid
import mimetypes
from datetime import timedelta
from django.conf import settings
from django.core.files.storage import default_storage


class BaseStorage:
    """Base storage class."""
    
    ALLOWED_EXTENSIONS = {
        'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico'],
        'document': [
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', 
            '.txt', '.md', '.markdown', '.csv', '.rtf'
        ],
        'archive': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'],
        'code': [
            '.py', '.js', '.html', '.css', '.json', '.xml', '.yaml', '.yml',
            '.ts', '.tsx', '.jsx', '.vue', '.java', '.c', '.cpp', '.h', '.hpp',
            '.go', '.rs', '.php', '.rb', '.sh', '.bat', '.ps1', '.sql',
            '.swift', '.kt', '.scala', '.r', '.m', '.mm', '.pl', '.pm'
        ],
        'video': ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm'],
        'audio': ['.mp3', '.wav', '.ogg', '.flac', '.aac', '.wma', '.m4a'],
        'data': ['.sql', '.db', '.sqlite', '.log', '.env', '.ini', '.conf', '.config'],
    }
    
    DEFAULT_MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
    
    # 设置为 True 则允许上传任意格式（只检查文件大小）
    ALLOW_ALL_EXTENSIONS = False
    
    @classmethod
    def get_max_file_size(cls):
        """Get max file size from settings or default."""
        from django.conf import settings
        max_size_mb = getattr(settings, 'FILE_MAX_SIZE_MB', 500)
        return max_size_mb * 1024 * 1024
    
    @classmethod
    def validate_file(cls, file_name, file_size, file_type):
        """Validate file."""
        from django.conf import settings
        
        max_file_size = cls.get_max_file_size()
        
        # Check file size
        if file_size > max_file_size:
            max_mb = max_file_size // 1024 // 1024
            raise ValueError(f'文件大小超过限制（最大{max_mb}MB）')
        
        # 检查是否允许所有格式（可通过 settings.FILE_ALLOW_ALL 配置）
        allow_all = getattr(settings, 'FILE_ALLOW_ALL', cls.ALLOW_ALL_EXTENSIONS)
        if allow_all:
            return True
        
        # Check file extension
        ext = '.' + file_name.split('.')[-1].lower() if '.' in file_name else ''
        allowed_exts = []
        for exts in cls.ALLOWED_EXTENSIONS.values():
            allowed_exts.extend(exts)
        
        if ext not in allowed_exts:
            raise ValueError(f'不支持的文件类型: {ext}')
        
        return True
    
    @classmethod
    def generate_file_key(cls, task_id, file_name):
        """Generate unique file key."""
        ext = '.' + file_name.split('.')[-1] if '.' in file_name else ''
        unique_id = str(uuid.uuid4())[:8]
        return f"tasks/{task_id}/{unique_id}{ext}"


class MinIOStorage(BaseStorage):
    """MinIO storage service."""
    
    def __init__(self):
        from minio import Minio
        
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self.bucket_name = settings.MINIO_BUCKET_NAME
        
        # Ensure bucket exists
        if not self.client.bucket_exists(self.bucket_name):
            self.client.make_bucket(self.bucket_name)
    
    def get_upload_url(self, file_key, file_type, expires=300):
        """Get presigned upload URL."""
        from minio.error import S3Error
        
        try:
            url = self.client.presigned_put_object(
                self.bucket_name,
                file_key,
                expires=timedelta(seconds=expires)
            )
            return url
        except S3Error as e:
            raise ValueError(f'生成上传URL失败: {e}')
    
    def get_download_url(self, file_key, expires=300):
        """Get presigned download URL."""
        from minio.error import S3Error
        
        try:
            url = self.client.presigned_get_object(
                self.bucket_name,
                file_key,
                expires=timedelta(seconds=expires)
            )
            return url
        except S3Error as e:
            raise ValueError(f'生成下载URL失败: {e}')
    
    def delete_file(self, file_key):
        """Delete file."""
        from minio.error import S3Error
        
        try:
            self.client.remove_object(self.bucket_name, file_key)
            return True
        except S3Error:
            return False
    
    def get_file_url(self, file_key):
        """Get public file URL."""
        protocol = 'https' if settings.MINIO_SECURE else 'http'
        return f"{protocol}://{settings.MINIO_ENDPOINT}/{self.bucket_name}/{file_key}"


class OSSStorage(BaseStorage):
    """Aliyun OSS storage service."""
    
    def __init__(self):
        import oss2
        
        self.auth = oss2.Auth(
            settings.OSS_ACCESS_KEY_ID,
            settings.OSS_ACCESS_KEY_SECRET
        )
        self.bucket = oss2.Bucket(
            self.auth,
            settings.OSS_ENDPOINT,
            settings.OSS_BUCKET_NAME
        )
    
    def get_upload_url(self, file_key, file_type, expires=300):
        """Get presigned upload URL."""
        try:
            url = self.bucket.sign_url(
                'PUT',
                file_key,
                expires,
                headers={'Content-Type': file_type}
            )
            return url
        except Exception as e:
            raise ValueError(f'生成上传URL失败: {e}')
    
    def get_download_url(self, file_key, expires=300):
        """Get presigned download URL."""
        try:
            url = self.bucket.sign_url('GET', file_key, expires)
            return url
        except Exception as e:
            raise ValueError(f'生成下载URL失败: {e}')
    
    def delete_file(self, file_key):
        """Delete file."""
        try:
            self.bucket.delete_object(file_key)
            return True
        except Exception:
            return False
    
    def get_file_url(self, file_key):
        """Get public file URL."""
        return f"https://{settings.OSS_BUCKET_NAME}.{settings.OSS_ENDPOINT}/{file_key}"


class StorageFactory:
    """Factory for creating storage instances."""
    
    @staticmethod
    def get_storage():
        """Get storage instance based on settings."""
        priority = settings.FILE_STORAGE_PRIORITY
        
        # Check OSS first if enabled
        if priority == 'oss' and settings.OSS_ENABLED:
            try:
                return OSSStorage()
            except Exception as e:
                print(f"OSS storage failed: {e}, falling back to MinIO")
        
        # Fall back to MinIO
        try:
            return MinIOStorage()
        except Exception as e:
            print(f"MinIO storage failed: {e}")
            raise ValueError('无法初始化存储服务')
