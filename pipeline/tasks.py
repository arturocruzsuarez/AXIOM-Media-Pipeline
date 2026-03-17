import subprocess
import os
import shutil
import logging
import traceback
from PIL import Image

from celery import shared_task
from django.conf import settings
from django.db import connection 
from django.utils.text import slugify
from .models import Version, SystemHealth
from .divergence_engine import PipelineStabilityIndex

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def process_version_task(self, version_id):
    """
    Tarea central de AXIOM (Procesa Footage y Stills con rutas estrictas).
    """
    engine = PipelineStabilityIndex()
    try:
        # 1. Recuperamos la versión y definimos su identidad
        version = Version.objects.get(id=version_id)
        input_path = version.file.path 
        ext = os.path.splitext(input_path)[1].lower()
        
        # Slugs para coherencia de SSOT
        p_slug = slugify(version.asset.project.title)
        a_slug = slugify(version.asset.name)
        v_str = f"v{version.version_number:03d}"
        base_name = os.path.splitext(os.path.basename(version.file.name))[0]
        
        # 2. Rutas Físicas (Donde FFmpeg/Pillow escribirán los archivos en el disco)
        final_dir = os.path.join(settings.MEDIA_ROOT, 'assets', p_slug, a_slug, v_str)
        os.makedirs(final_dir, exist_ok=True)
        
        # 3. Rutas Virtuales (Lo que se guarda en la base de datos de Django)
        # Usamos f-strings puros para evitar problemas con os.path.join y los FileFields
        base_db_path = f"assets/{p_slug}/{a_slug}/{v_str}"

        # --- RAMIFICACIÓN DE PROCESAMIENTO ---
        IMAGE_EXTS = ['.jpg', '.jpeg', '.png', '.tiff', '.psd', '.tga']
        
        if ext in IMAGE_EXTS:
            # ---> RUTA A: PROCESAMIENTO DE STILLS (Imagen) <---
            logger.info(f"🖼️ Procesando Still: {version.uuid}")
            thumb_filename = f"{base_name}_thumb.jpg"
            thumb_path = os.path.join(final_dir, thumb_filename)
            
            with Image.open(input_path) as img:
                img.thumbnail((480, 270)) 
                # Convertir a RGB por si es PNG para poder guardar como JPEG
                if img.mode in ('RGBA', 'P'): 
                    img = img.convert('RGB')
                img.save(thumb_path, "JPEG", quality=85)
            
            # Guardamos la ruta estricta en DB
            db_thumb_path = f"{base_db_path}/{thumb_filename}"
            version.thumbnail = db_thumb_path
            version.proxy_file_path = db_thumb_path
            version.transcoding_status = Version.TranscodingStatus.COMPLETED
            
            engine.report_status('integrity', success=True)
            
        else:
            # ---> RUTA B: PROCESAMIENTO DE FOOTAGE (Video) <---
            logger.info(f"🎞️ Procesando Footage: {version.uuid}")
            proxy_filename = f"{base_name}_proxy.mp4"
            thumb_filename = f"{base_name}_thumb.jpg"
            
            proxy_path = os.path.join(final_dir, proxy_filename)
            thumb_path = os.path.join(final_dir, thumb_filename)

            dept_label = version.get_department_display().upper()
            watermark = f"AXIOM | {version.asset.name} | {dept_label} | {v_str}"
            
            command = [
                'ffmpeg', '-y', '-i', input_path,
                '-vf', f"scale=-2:720,drawtext=text='{watermark}':x=10:y=H-45:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.4",
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '22', 
                '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                '-c:a', 'aac', '-b:a', '128k',
                proxy_path
            ]

            result = subprocess.run(command, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Restauramos el comando exacto que funcionaba antes (-update 1)
                subprocess.run(['ffmpeg', '-y', '-i', input_path, '-ss', '00:00:05', '-vframes', '1', '-update', '1', thumb_path], check=True)
                
                # Guardamos las rutas estrictas en DB
                version.proxy_file_path = f"{base_db_path}/{proxy_filename}"
                version.thumbnail = f"{base_db_path}/{thumb_filename}"
                version.transcoding_status = Version.TranscodingStatus.COMPLETED
                engine.report_status('ffmpeg', success=True)
            else:
                raise Exception(f"FFmpeg Error: {result.stderr}")

        # Guardado final unificado
        version.save(update_fields=['proxy_file_path', 'thumbnail', 'transcoding_status'])
        logger.info(f"✅ Versión {version.uuid} procesada con éxito.")

    except Exception as e:
        engine.report_status('ffmpeg', success=False)
        error_stack = traceback.format_exc()
        logger.error(f"🛑 Error crítico en Pipeline:\n{error_stack}")
        Version.objects.filter(pk=version_id).update(transcoding_status=Version.TranscodingStatus.ERROR)
        raise e

@shared_task
def run_system_diagnostic():
    """Diagnóstico de infraestructura SRE."""
    total, used, free = shutil.disk_usage("/")
    storage_val = (free / total) * 100

    try:
        connection.ensure_connection()
        db_val = 100.0
    except:
        db_val = 0.0

    try:
        res = subprocess.run(['ffmpeg', '-version'], capture_output=True)
        ffmpeg_val = 100.0 if res.returncode == 0 else 0.0
    except:
        ffmpeg_val = 0.0

    total_versions = Version.objects.count()
    if total_versions > 0:
        error_count = Version.objects.filter(transcoding_status='ERROR').count()
        integrity_val = ((total_versions - error_count) / total_versions) * 100
    else:
        integrity_val = 100.0

    health, _ = SystemHealth.objects.get_or_create(id=1)
    health.storage_score = storage_val
    health.database_score = db_val
    health.ffmpeg_score = ffmpeg_val
    health.integrity_score = integrity_val
    health.save()

    return f"Diagnostic: S:{storage_val:.1f}% | FF:{ffmpeg_val:.1f}% | I:{integrity_val:.1f}%"