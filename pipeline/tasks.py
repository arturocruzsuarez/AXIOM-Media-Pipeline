import subprocess
import os
import shutil
from celery import shared_task
from django.conf import settings
from django.db import connection 
from django.utils.text import slugify
from .models import Version, SystemHealth
from .divergence_engine import PipelineStabilityIndex

@shared_task(bind=True)
def process_video_task(self, version_id):
    engine = PipelineStabilityIndex()
    try:
        version = Version.objects.get(id=version_id)
        version.ingest_and_verify(version.file.path)
        version.transcoding_status = Version.TranscodingStatus.PROCESSING
        version.save()

        input_path = version.file.path 
        directory = os.path.dirname(input_path)
        base_name = os.path.splitext(os.path.basename(version.file.name))[0]
        
        proxy_path = os.path.join(directory, f"{base_name}_proxy.mp4")
        thumb_path = os.path.join(directory, f"{base_name}_thumb.jpg")

        # Comando único con Watermark
        watermark = f"AXIOM | {version.asset.project.title} | v{version.version_number:03d}"
        command = [
            'ffmpeg', '-y', '-i', input_path,
            '-vf', f"scale=-2:720,drawtext=text='{watermark}':x=10:y=H-45:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.4",
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23', '-c:a', 'aac', '-b:a', '128k',
            proxy_path
        ]

        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            # Generar miniatura
            subprocess.run(['ffmpeg', '-y', '-i', input_path, '-ss', '00:00:05', '-vframes', '1', '-update', '1', thumb_path], check=True)
            
            engine.report_status('ffmpeg', success=True)
            
            # Guardar rutas relativas para evitar el DataError
            p_slug = slugify(version.asset.project.title)
            a_slug = slugify(version.asset.name)
            v_str = f"v{version.version_number:03d}"
            
            version.proxy_file_path = os.path.join('assets', p_slug, a_slug, v_str, f"{base_name}_proxy.mp4")
            version.thumbnail = os.path.join('assets', p_slug, a_slug, v_str, f"{base_name}_thumb.jpg")
            version.transcoding_status = Version.TranscodingStatus.COMPLETED
            version.save()
        else:
            engine.report_status('ffmpeg', success=False)
            raise Exception(result.stderr)

    except Exception as e:
        engine.report_status('ffmpeg', success=False)
        Version.objects.filter(pk=version_id).update(transcoding_status=Version.TranscodingStatus.ERROR)
        return str(e)

@shared_task
def run_system_diagnostic():
    """NUEVO: La tarea que hace que el Punto 2 y 3 no sean 'promesas vacías'."""
    # 1. Medir STORAGE (Espacio real en disco)
    total, used, free = shutil.disk_usage("/")
    storage_val = (free / total) * 100

    # 2. Medir DATABASE (Latencia/Conexión)
    try:
        connection.ensure_connection()
        db_val = 100.0
    except:
        db_val = 0.0

    # 3. Medir FFMPEG (Disponibilidad del binario)
    try:
        res = subprocess.run(['ffmpeg', '-version'], capture_output=True)
        ffmpeg_val = 100.0 if res.returncode == 0 else 0.0
    except:
        ffmpeg_val = 0.0

    # 4. Medir INTEGRIDAD (Basado en el historial de QC)
    # Calculamos qué porcentaje de las versiones totales pasaron el QC
    total_versions = Version.objects.count()
    if total_versions > 0:
        # Aquí asumimos que tienes un campo 'qc_passed' o similar, 
        # si no, filtramos por las que NO tengan errores.
        passed_versions = Version.objects.filter(approval_status='APPROVED').count()
        integrity_val = (passed_versions / total_versions) * 100
    else:
        integrity_val = 100.0

    # GUARDAR EN LA BASE DE DATOS
    health, _ = SystemHealth.objects.get_or_create(id=1)
    health.storage_score = storage_val
    health.database_score = db_val
    health.ffmpeg_score = ffmpeg_val
    health.integrity_score = integrity_val
    health.save()

    return f"Diagnostic Success: S:{storage_val:.1f}% | I:{integrity_val:.1f}%"