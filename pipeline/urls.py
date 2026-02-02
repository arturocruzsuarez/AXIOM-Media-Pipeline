from django.urls import path
from .views import VersionUploadView
from .views import dashboard_view, VersionUploadView

urlpatterns = [
    # Endpoint: POST /api/projects/1/upload/
    path('projects/<int:project_id>/upload/', VersionUploadView.as_view(), name='version-upload'),
    
    # NUEVA RUTA: El Medidor de Divergencia
    path('dashboard/', dashboard_view, name='divergence-dashboard'),
]