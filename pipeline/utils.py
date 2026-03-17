import hashlib
import os
import subprocess
import json # <--- Nuevo import para leer la salida de ffprobe
from django.utils.text import slugify

def calculate_sha256(file_path):
    """ADN del archivo: SHA-256 por bloques."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def get_video_metadata(file_path):
    """Extrae metadatos técnicos usando FFprobe."""
    cmd = [
        'ffprobe', '-v', 'quiet', '-print_format', 'json', 
        '-show_streams', '-show_format', file_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        video_track = next((s for s in data['streams'] if s['codec_type'] == 'video'), None)
        if not video_track:
            return {}

        fps_raw = video_track.get('avg_frame_rate', '24/1')
        num, den = map(int, fps_raw.split('/'))
        fps = num / den if den != 0 else 24.0

        # Buscamos el timecode en los tags del stream o del formato
        tags = video_track.get('tags', {})
        format_tags = data.get('format', {}).get('tags', {})
        tc = tags.get('timecode') or format_tags.get('timecode') or "00:00:00:00"

        return {
            'width': int(video_track.get('width', 0)),
            'height': int(video_track.get('height', 0)),
            'fps': round(fps, 3),
            'duration': float(data['format'].get('duration', 0)),
            'color_space': video_track.get('color_space', 'ACEScg'),
            'timecode_start': tc, # <--- ¡Aquí está!
        }
    except Exception as e:
        print(f"❌ Error en FFprobe: {e}")
        return {}

def asset_version_path(instance, filename):
    """Estructura de carpetas profesional."""
    project_slug = slugify(instance.asset.project.title)
    asset_slug = slugify(instance.asset.name)
    version_str = f"v{instance.version_number:03d}"
    return os.path.join('assets', project_slug, asset_slug, version_str, filename)