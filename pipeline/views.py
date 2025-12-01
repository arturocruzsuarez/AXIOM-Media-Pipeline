from rest_framework import viewsets
# Importamos modelos y serializers
from .models import Project, Version, Comment, License
from .serializers import ProjectSerializer, VersionSerializer, CommentSerializer, LicenseSerializer

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

# --- NUEVOS VIEWSETS ---

class VersionViewSet(viewsets.ModelViewSet):
    queryset = Version.objects.all()
    serializer_class = VersionSerializer

class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer

class LicenseViewSet(viewsets.ModelViewSet):
    queryset = License.objects.all()
    serializer_class = LicenseSerializer