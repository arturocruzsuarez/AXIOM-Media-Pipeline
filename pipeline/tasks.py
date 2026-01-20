import subprocess
import os
from celery import shared_task
from django.conf import settings
from .models import Version

@shared_task(bind=True)
def process_video_task(self, version_id):
    try:
        # 1. Recuperar la instancia (Atomicidad)
        version = Version.objects.get(id=version_id)
        version.transcoding_status = Version.TranscodingStatus.PROCESSING
        version.save()

        input_path = version.original_file_path
        
        # Generar nombre para el proxy (ej: video_v1_proxy.mp4)
        base_name = os.path.basename(input_path)
        file_name, _ = os.path.splitext(base_name)
        output_filename = f"{file_name}_proxy.mp4"
        output_path = os.path.join(settings.MEDIA_ROOT, 'proxies', output_filename)

        # Asegurar que el directorio existe
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 2. Comando FFmpeg (Low-Level Manipulation)
        # Convertimos a H.264 ligero (720p) para web
        command = [
            'ffmpeg',
            '-y',                 # Sobreescribir si existe
            '-i', input_path,     # Input
            '-vf', 'scale=-2:720',# Escalar a 720p manteniendo aspect ratio
            '-c:v', 'libx264',    # Codec de video
            '-preset', 'fast',    # Velocidad de compresión
            '-crf', '23',         # Calidad visual
            '-c:a', 'aac',        # Codec de audio
            '-b:a', '128k',       # Bitrate de audio
            output_path
        ]

        # 3. Ejecución del Proceso (Subprocess)
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, # Capturamos logs técnicos de FFmpeg
            text=True
        )

        if result.returncode != 0:
            raise Exception(f"FFmpeg Error: {result.stderr}")

        # 4. Actualización de Estado (Success)
        version.proxy_file_path = output_path
        version.transcoding_status = Version.TranscodingStatus.COMPLETED
        version.save()
        
        return f"Version {version.version_number} processed successfully."

    except Exception as e:
        # 5. Manejo de Errores (Fail-safe)
        if 'version' in locals():
            version.transcoding_status = Version.TranscodingStatus.ERROR
            version.save()
        return f"Error processing version {version_id}: {str(e)}"