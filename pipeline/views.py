import os
from django.conf import settings
from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404, render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Max # <--- NUEVO: Para evitar race conditions

from .models import Project, Asset, Version, SystemHealth
from .serializers import VersionSerializer
from .divergence_engine import PipelineStabilityIndex

engine = PipelineStabilityIndex()

def get_category_from_extension(filename):
    """Detecta la categoría del archivo basado en su extensión."""
    ext = os.path.splitext(filename)[1].lower()
    if ext in ['.mp4', '.mov', '.avi', '.mkv']:
        return Asset.AssetCategory.VIDEO
    elif ext in ['.obj', '.fbx', '.blend', '.usd']:
        return Asset.AssetCategory.MODEL_3D
    elif ext in ['.py', '.sh', '.json', '.js']:
        return Asset.AssetCategory.CODE
    return Asset.AssetCategory.OTHER

class VersionUploadView(APIView):
    def post(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        
        # Aceptamos 'file' de forma genérica, o 'video_file' por retrocompatibilidad
        file_obj = request.FILES.get('file') or request.FILES.get('video_file')
        asset_name = request.data.get('asset_name')

        if not file_obj or not asset_name:
            return Response(
                {"error": "Falta el archivo o el nombre del asset"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 1. Determinamos la categoría dinámicamente
            detected_category = get_category_from_extension(file_obj.name)

            # 2. Lógica de Asset Agnóstico
            asset, created = Asset.objects.get_or_create(
                name=asset_name,
                project=project,
                defaults={'category': detected_category} # Solo se asigna si se crea nuevo
            )

            # 3. Persistencia Física
            file_name = f"raw_{project.id}_{file_obj.name}"
            save_path = os.path.join('raw_uploads', file_name)
            path = default_storage.save(save_path, file_obj)

            # 4. Atomic Versioning Seguro (Evita race conditions en subidas simultáneas)
            max_version = Version.objects.filter(asset=asset).aggregate(Max('version_number'))['version_number__max']
            new_number = (max_version + 1) if max_version else 1
            last_version = Version.objects.filter(asset=asset, version_number=max_version).first() if max_version else None

            # 5. Creación de la Versión
            version = Version.objects.create(
                asset=asset,
                version_number=new_number,
                file=file_obj,
                uploaded_by=request.user if request.user.is_authenticated else None,
                parent_version=last_version,
                transcoding_status=Version.TranscodingStatus.PENDING
            )

            engine.report_status('storage', success=True)

            # ELIMINAMOS EL DISPARO DE CELERY AQUÍ. 
            # El Signal se encargará de eso para mantener la responsabilidad única (SSOT).

            serializer = VersionSerializer(version)
            return Response({
                "data": serializer.data,
                "message": f"Ingreso exitoso ({detected_category}). Procesando en el Attractor Field."
            }, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            engine.report_status('storage', success=False)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 

# --- Vista del Dashboard ---
def dashboard_view(request):
    engine = PipelineStabilityIndex()
    telemetry = engine.get_diagnostics()
    
    # Traemos la salud persistente de la DB (Hardware)
    health, created = SystemHealth.objects.get_or_create(id=1)
    
    context = {
        'psi': telemetry['psi_score'],             # <-- El número de 6 decimales listo para usar
        'status': telemetry['status'],
        'world_line': telemetry['world_line'],
        'is_stable': telemetry['is_stable'],
        'sensors': telemetry['components'],
        'health': health,                          # <-- Barras de hardware
        'divergence_index': telemetry['psi_score'] # <-- Reutilizamos el PSI exacto para el medidor principal
    }
    
    return render(request, 'pipeline/dashboard.html', context)