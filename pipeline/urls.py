from django.urls import path
from .views import VersionUploadView

urlpatterns = [
    # Endpoint: POST /api/projects/1/upload/
    path('projects/<int:project_id>/upload/', VersionUploadView.as_view(), name='version-upload'),
]