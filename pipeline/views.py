# pipeline/views.py
from rest_framework import viewsets
from .models import Project
from .serializers import ProjectSerializer

class ProjectViewSet(viewsets.ModelViewSet):
    # 1. ¿Qué datos va a manejar este gerente?
    queryset = Project.objects.all()
    
    # 2. ¿Qué traductor va a usar?
    serializer_class = ProjectSerializer