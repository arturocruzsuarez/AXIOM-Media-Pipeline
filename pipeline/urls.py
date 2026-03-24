from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token # <-- Importante
from .views import dashboard_view, VersionUploadView

urlpatterns = [
    # API: Endpoint para subir versiones
    path('projects/<int:project_id>/upload/', VersionUploadView.as_view(), name='version-upload'),
    
    # API: Endpoint para obtener tu Token (Login vía API)
    path('api-token-auth/', obtain_auth_token, name='api_token_auth'),
    
    # UI: El Medidor de Divergencia (Dashboard)
    path('dashboard/', dashboard_view, name='divergence-dashboard'),
]