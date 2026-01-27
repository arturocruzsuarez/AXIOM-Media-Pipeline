import hashlib
import os
import subprocess
from django.utils.text import slugify # Para nombres de carpetas limpios
from pymediainfo import MediaInfo

def calculate_sha256(file_path):
    """Calcula la huella digital criptográfica SHA-256 (El ADN del archivo)."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Leemos en bloques para no saturar la memoria RAM con archivos pesados
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def get_video_metadata(file_path):
    """Extrae metadatos técnicos reales (Resolución, FPS, Espacio de Color)."""
    media_info = MediaInfo.parse(file_path)
    metadata = {}
    for track in media_info.tracks:
        if track.track_type == "Video":
            metadata['width'] = int(track.width) if track.width else None
            metadata['height'] = int(track.height) if track.height else None
            metadata['fps'] = float(track.frame_rate) if track.frame_rate else None
            metadata['color_space'] = track.color_space if track.color_space else 'ACEScg'
    return metadata

def generate_proxy_and_thumb(input_path, output_proxy_path, output_thumb_path):
    """
    Ejecuta FFmpeg para generar un Proxy 720p y una Miniatura.
    Flujo: GenProxy -> GenThumb (Según tu diagrama de estados).
    """
    # Creamos las carpetas si no existen para evitar errores de FFmpeg
    os.makedirs(os.path.dirname(output_proxy_path), exist_ok=True)
    
    try:
        # 1. GenProxy: Convertir a 720p H.264 (MP4 ligero para revisión)
        proxy_cmd = [
            'ffmpeg', '-i', input_path,
            '-vf', 'scale=-1:720', # Escala proporcional a 720p
            '-c:v', 'libx264', '-crf', '23', '-preset', 'veryfast',
            '-y', output_proxy_path
        ]
        subprocess.run(proxy_cmd, check=True)

        # 2. GenThumb: Captura un frame en el segundo 00:00:00
        thumb_cmd = [
            'ffmpeg', '-i', input_path,
            '-ss', '00:00:00', '-vframes', '1',
            '-y', output_thumb_path
        ]
        subprocess.run(thumb_cmd, check=True)
        
        return True
    except Exception as e:
        print(f"Error crítico en FFmpeg: {e}")
        return False
    
def asset_version_path(instance, filename):
    """Genera la ruta profesional de almacenamiento (Estándar MovieLabs)."""
    # slugify convierte "Mi Proyecto Increíble" en "mi-proyecto-increible"
    project_slug = slugify(instance.asset.project.title)
    asset_slug = slugify(instance.asset.name)
    version_str = f"v{instance.version_number:03d}"
    
    # Ejemplo: assets/mi-proyecto/personaje-a/v001/video.mp4
    return os.path.join('assets', project_slug, asset_slug, version_str, filename)