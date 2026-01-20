import os
from django.conf import settings
from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Project, Version
from .serializers import VersionSerializer
from .tasks import process_video_task

class VersionUploadView(APIView):
    """
    Vista de Ingesta (Ingest Stage).
    Recibe el archivo, crea el registro inmutable y dispara el Worker.
    """

    def post(self, request, project_id):
        # 1. Validación
        project = get_object_or_404(Project, pk=project_id)
        
        file_obj = request.FILES.get('video_file')
        if not file_obj:
            return Response({"error": "No video file provided"}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Persistencia Física
        file_name = f"raw_{project.id}_{file_obj.name}"
        save_path = os.path.join(settings.MEDIA_ROOT, 'raw_uploads', file_name)
        path = default_storage.save(save_path, file_obj)
        full_path = default_storage.path(path)

        # 3. Atomic Versioning (Cálculo automático del ID)
        last_version = Version.objects.filter(project=project).order_by('-version_number').first()
        new_number = (last_version.version_number + 1) if last_version else 1

        # Creamos la versión. 
        # Nota: Aquí podríamos añadir lógica para setear 'parent_version' si el frontend lo enviara.
        version = Version.objects.create(
            project=project,
            version_number=new_number,
            original_file_path=full_path,
            uploaded_by=request.user if request.user.is_authenticated else None,
            parent_version=last_version, # Asumimos linaje lineal por defecto (v2 viene de v1)
            transcoding_status=Version.TranscodingStatus.PENDING
        )

        # 4. Async Trigger (Celery)
        task = process_video_task.delay(version.id)

        # 5. Respuesta Inmediata (202 Accepted)
        serializer = VersionSerializer(version)
        return Response({
            "data": serializer.data,
            "task_id": task.id,
            "message": "Ingest started. Transcoding in background."
        }, status=status.HTTP_202_ACCEPTED)