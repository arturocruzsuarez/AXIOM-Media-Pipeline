import os 
from django.conf import settings 
from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404, render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

# Importamos los modelos y herramientas
from .models import Project, Asset, Version, SystemHealth
from .serializers import VersionSerializer
from .tasks import process_video_task 
from .divergence_engine import PipelineStabilityIndex 

# Inicializamos el motor a nivel de módulo como lo tenías
engine = PipelineStabilityIndex()

class VersionUploadView(APIView):
    """
    Vista de Ingesta (Ingest Stage).
    Recibe el archivo, asegura la existencia del Asset y dispara el Worker.
    """

    def post(self, request, project_id):
        # 1. Validación de Proyecto
        project = get_object_or_404(Project, pk=project_id)
        
        file_obj = request.FILES.get('video_file')
        asset_name = request.data.get('asset_name')

        if not file_obj or not asset_name:
            return Response(
                {"error": "Falta el archivo de video o el nombre del asset"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 2. Lógica de Asset (Mantenemos tu get_or_create)
            asset, created = Asset.objects.get_or_create(
                name=asset_name,
                project=project
            ) 
            # 3. Persistencia Física
            file_name = f"raw_{project.id}_{file_obj.name}"
            save_path = os.path.join('raw_uploads', file_name)
            path = default_storage.save(save_path, file_obj)
            full_path = default_storage.path(path)

            # 3. Atomic Versioning (Mantenemos tu lógica de cálculo)
            last_version = Version.objects.filter(asset=asset).order_by('-version_number').first()
            new_number = (last_version.version_number + 1) if last_version else 1

            # 4. Creación de la Versión 
            # IMPORTANTE: He re-incorporado 'parent_version' que es vital para tu árbol de versiones
            version = Version.objects.create(
                asset=asset,
                version_number=new_number,
                file=file_obj,
                uploaded_by=request.user if request.user.is_authenticated else None,
                parent_version=last_version, # <--- RECUPERADO
                transcoding_status=Version.TranscodingStatus.PENDING
            )

            # Sensor de storage reporta éxito
            engine.report_status('storage', success=True)

            # 5. Async Trigger (Celery)
            task = process_video_task.delay(version.id)

            serializer = VersionSerializer(version)
            return Response({
                "data": serializer.data,
                "task_id": task.id,
                "message": "Ingreso exitoso. Procesando en el Attractor Field."
            }, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            engine.report_status('storage', success=False)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# --- Vista del Dashboard ---
def dashboard_view(request):
    engine = PipelineStabilityIndex()
    telemetry = engine.get_diagnostics()
    
    # NUEVO: Traemos la salud persistente de la DB
    health, created = SystemHealth.objects.get_or_create(id=1)
    
    # NUEVO: Cálculo de Divergencia basado en la integridad real
    #integrity_penalty = (100 - health.integrity_score) * 0.001
    integrity_penalty = (100 - health.integrity_score) * 0.001
    divergence = 0.132336 + integrity_penalty
    
    context = {
        'psi': telemetry['psi_score'],
        'status': telemetry['status'],
        'world_line': telemetry['world_line'],
        'is_stable': telemetry['is_stable'],
        'sensors': telemetry['components'],
        'health': health,                  # <--- Para las barras de hardware
        'divergence_index': f"{divergence:.6f}", # <--- Para el medidor central
    }
    
    return render(request, 'pipeline/dashboard.html', context)