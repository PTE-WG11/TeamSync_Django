"""
Management command to setup CORS policy for MinIO bucket.
"""
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    """Setup CORS policy for storage bucket."""
    
    help = 'Setup CORS policy for MinIO/OSS bucket to allow cross-origin requests'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--origins',
            type=str,
            nargs='+',
            help='List of allowed origins (e.g., http://localhost:3000 https://example.com)'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Allow all origins (*)' 
        )
    
    def handle(self, *args, **options):
        from apps.files.storage import StorageFactory
        
        origins = options.get('origins')
        allow_all = options.get('all')
        
        if allow_all:
            origins = ['*']
        elif not origins:
            # Try to get from settings
            origins = getattr(settings, 'MINIO_CORS_ORIGINS', ['*'])
            if isinstance(origins, str):
                origins = [origins]
        
        self.stdout.write(f"Setting up CORS policy...")
        self.stdout.write(f"Allowed origins: {origins}")
        
        try:
            storage = StorageFactory.get_storage()
            
            if hasattr(storage, 'setup_cors'):
                success = storage.setup_cors(origins)
                if success:
                    self.stdout.write(
                        self.style.SUCCESS(f"CORS policy updated successfully!")
                    )
                    self.stdout.write("Allowed methods: GET, PUT, POST, DELETE, HEAD")
                    self.stdout.write("Allowed headers: *")
                else:
                    self.stdout.write(
                        self.style.ERROR("Failed to update CORS policy")
                    )
            else:
                self.stdout.write(
                    self.style.WARNING("Current storage does not support CORS configuration")
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error: {e}")
            )
