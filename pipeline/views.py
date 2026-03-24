import os
from django.shortcuts import get_object_or_404, render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser

from .models import Project, Asset, Version, SystemHealth
from .serializers import VersionSerializer
from .divergence_engine import PipelineStabilityIndex

# Inicializamos el motor de estabilidad
engine = PipelineStabilityIndex()

def get_category_from_extension(filename):
    """Detecta la categoría del archivo basado en su extensión."""
    ext = os.path.splitext(filename)[1].lower()
    mapping = {
        '.mp4': Asset.AssetCategory.VIDEO, '.mov': Asset.AssetCategory.VIDEO,
        '.obj': Asset.AssetCategory.MODEL_3D, '.fbx': Asset.AssetCategory.MODEL_3D,
        '.usd': Asset.AssetCategory.MODEL_3D, '.abc': Asset.AssetCategory.MODEL_3D,
        '.py': Asset.AssetCategory.CODE, '.json': Asset.AssetCategory.CODE,
    }
    return mapping.get(ext, Asset.AssetCategory.OTHER)

# --- 1. Vista de Subida (API para Sony/DCCs) ---
class VersionUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        file_obj = request.FILES.get('file')
        asset_name = request.data.get('asset_name')
        department = request.data.get('department', 'GEN')

        if not file_obj or not asset_name:
            return Response(
                {"error": "Faltan datos críticos: 'file' o 'asset_name'"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            detected_category = get_category_from_extension(file_obj.name)
            asset, _ = Asset.objects.get_or_create(
                name=asset_name,
                project=project,
                defaults={'category': detected_category}
            )

            version = Version(
                asset=asset,
                file=file_obj,
                department=department,
                uploaded_by=request.user,
                transcoding_status=Version.TranscodingStatus.PENDING
            )

            # Ejecuta el clean() del modelo (Validación de SHA-256)
            version.full_clean() 
            version.save()

            engine.report_status('storage', success=True)

            serializer = VersionSerializer(version)
            return Response({
                "data": serializer.data,
                "message": f"Ingreso exitoso en {department}. Hash verificado."
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            engine.report_status('integrity', success=False)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

# --- 2. Vista del Dashboard (El Medidor de Divergencia) ---
def dashboard_view(request):
    telemetry = engine.get_diagnostics()
    
    # Traemos la salud persistente de la DB (Hardware)
    health, created = SystemHealth.objects.get_or_create(id=1)
    
    context = {
        'psi': telemetry['psi_score'],
        'status': telemetry['status'],
        'world_line': telemetry['world_line'],
        'is_stable': telemetry['is_stable'],
        'sensors': telemetry['components'],
        'health': health,
        'divergence_index': telemetry['psi_score']
    }
    
    return render(request, 'pipeline/dashboard.html', context)