import os
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.text import slugify # Necesario para la ruta de la miniatura
from .models import Version
from .utils import generate_proxy_and_thumb

@receiver(post_save, sender=Version)
def axiom_processing_engine(sender, instance, created, **kwargs):
    """
    Sensor de AXIOM: Ingesta (Hash/Meta) + Transcoding (Proxy/Thumb) + Registro de Media.
    """
    if created and instance.file:
        # 1. INGESTA (Hash y Metadatos)
        archivo_fisico = instance.file.path
        ingesta_exitosa = instance.ingest_and_verify(archivo_fisico)
        
        if not ingesta_exitosa:
            print(f"⚠️ AXIOM: Ingesta omitida (archivo duplicado o error).")

        # 2. PREPARACIÓN DE RUTAS
        # Extraemos el nombre base (ej: 'clip01.mp4' -> 'clip01')
        base_name = os.path.splitext(os.path.basename(instance.file.name))[0]
        directory = os.path.dirname(instance.file.path)
        
        # Nombres de los archivos procesados
        proxy_filename = f"{base_name}_proxy.mp4"
        thumb_filename = f"{base_name}_thumb.jpg"
        
        # Rutas absolutas para que FFmpeg sepa dónde escribir
        proxy_path = os.path.join(directory, proxy_filename)
        thumb_path = os.path.join(directory, thumb_filename)

        # 3. TRANSCODING (FFmpeg)
        Version.objects.filter(pk=instance.pk).update(transcoding_status='PROCESSING')
        print(f"🎬 AXIOM: Iniciando FFmpeg para {instance}...")

        exito_ffmpeg = generate_proxy_and_thumb(archivo_fisico, proxy_path, thumb_path)

        if exito_ffmpeg:
            # IMPORTANTE: Reconstruimos la ruta RELATIVA para el ImageField de Django
            # assets/nombre-proyecto/nombre-asset/v001/archivo_thumb.jpg
            project_slug = slugify(instance.asset.project.title)
            asset_slug = slugify(instance.asset.name)
            version_str = f"v{instance.version_number:03d}"
            
            # Esta es la ruta que Django guardará en la base de datos
            rel_thumb_path = os.path.join('assets', project_slug, asset_slug, version_str, thumb_filename)

            # 4. CIERRE DEL FLUJO: Registro en Base de Datos
            Version.objects.filter(pk=instance.pk).update(
                proxy_file_path=proxy_path,
                thumbnail=rel_thumb_path, # <--- Ahora sí, la miniatura se registra
                transcoding_status='COMPLETED'
            )
            print(f"✅ AXIOM: Transcoding y Thumbnail registrados para {instance}.")
        else:
            Version.objects.filter(pk=instance.pk).update(transcoding_status='ERROR')
            print(f"❌ AXIOM: Fallo crítico en FFmpeg.")