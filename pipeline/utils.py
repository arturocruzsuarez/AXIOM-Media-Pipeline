import hashlib
import os
from pymediainfo import MediaInfo

def calculate_sha256(file_path):
    """Calcula la huella digital criptográfica $SHA-256$."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def get_video_metadata(file_path):
    """Extrae metadatos técnicos reales del archivo de video."""
    media_info = MediaInfo.parse(file_path)
    metadata = {}
    for track in media_info.tracks:
        if track.track_type == "Video":
            # Extraemos lo esencial para el Pipeline
            metadata['width'] = int(track.width) if track.width else None
            metadata['height'] = int(track.height) if track.height else None
            metadata['fps'] = float(track.frame_rate) if track.frame_rate else None
            metadata['color_space'] = track.color_space if track.color_space else 'ACEScg'
    return metadata

def asset_version_path(instance, filename):
    """Genera la ruta profesional de MovieLabs."""
    project_slug = instance.asset.project.title.replace(" ", "_")
    asset_slug = instance.asset.name.replace(" ", "_")
    version_str = f"v{instance.version_number:03d}"
    return os.path.join('assets', project_slug, asset_slug, version_str, filename)