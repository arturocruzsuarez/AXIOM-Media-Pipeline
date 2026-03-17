import os
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Version, Asset
# Actualizamos el nombre de la tarea importada
from .tasks import process_version_task 

@receiver(post_save, sender=Version)
def axiom_processing_trigger(sender, instance, created, **kwargs):
    """
    Sensor de AXIOM: Disparador del Pipeline.
    """
    # 1. Filtro de seguridad: Solo si es nuevo, tiene archivo y no se ha disparado
    if created and instance.file and not getattr(instance, '_is_processing_triggered', False):
        
        archivo_fisico = instance.file.path
        
        # 2. INGESTA RÁPIDA (Cálculo de ADN / SHA-256 y Metadatos iniciales)
        ingesta_ok = instance.ingest_and_verify(archivo_fisico)
        
        if ingesta_ok:
            instance._is_processing_triggered = True # Previene doble ejecución
            
            # 3. ENRUTAMIENTO INTELIGENTE
            # Mandamos a Celery tanto Videos (Footage) como Imágenes (Stills)
            # para que ambos tengan su thumbnail procesado.
            needs_processing = [
                Asset.AssetCategory.VIDEO, 
                Asset.AssetCategory.IMAGE # <--- Agregamos imágenes al flujo de Celery
            ]

            if instance.asset.category in needs_processing:
                # Delegamos la tarea (transcodificación o redimensionado)
                process_version_task.delay(instance.pk)
                
                # Actualizamos status a PROCESSING
                Version.objects.filter(pk=instance.pk).update(transcoding_status='PROCESSING')
                print(f"🚀 AXIOM: {instance.asset.category} detectado para {instance}. Tarea delegada.")
            
            elif instance.asset.category == Asset.AssetCategory.CODE:
                # Scripts de Blender/Python no requieren procesamiento visual
                Version.objects.filter(pk=instance.pk).update(transcoding_status='COMPLETED')
                print(f"⚡ AXIOM: Script registrado. No requiere procesamiento.")
            
            else:
                # Otros formatos (PDFs de guion, Docs, etc.)
                Version.objects.filter(pk=instance.pk).update(transcoding_status='COMPLETED')
                print(f"✅ AXIOM: Activo genérico registrado.")

        else:
            # Si el SHA-256 falla o el archivo está corrupto
            Version.objects.filter(pk=instance.pk).update(transcoding_status='ERROR')
            print(f"⚠️ AXIOM: Divergencia detectada en ingesta inicial.")