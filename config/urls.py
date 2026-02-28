"""
URL configuration for TeamSync project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from apps.projects.document_views import GlobalDocumentDetailView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.accounts.urls')),
    path('api/projects/', include('apps.projects.urls')),
    path('api/tasks/', include('apps.tasks.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/files/', include('apps.files.urls')),
    path('api/visualization/', include('apps.visualization.urls')),
    path('api/team/', include('apps.accounts.team_urls')),
    path('api/dashboard/', include('apps.visualization.dashboard_urls')),
    
    # Global document detail endpoint
    path('api/documents/<int:id>/', GlobalDocumentDetailView.as_view(), name='global-document-detail'),

    # 导出 Schema 文件 (YAML)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # Swagger UI:
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # Redoc UI (另一种风格):
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
