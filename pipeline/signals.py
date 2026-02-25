import os
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Version, Asset
from .tasks import process_video_task

@receiver(post_save, sender=Version)
def axiom_processing_trigger(sender, instance, created, **kwargs):
    """
    Sensor de AXIOM: Disparador del Pipeline.
    """
    # Usamos un flag 'is_processing_triggered' para evitar bucles infinitos 
    # si el post_save se llama de nuevo al actualizar el status.
    if created and instance.file and not getattr(instance, '_is_processing_triggered', False):
        
        archivo_fisico = instance.file.path
        
        # 1. INGESTA RÁPIDA (ADN y Metadatos)
        ingesta_ok = instance.ingest_and_verify(archivo_fisico)
        
        if ingesta_ok:
            instance._is_processing_triggered = True # Previene doble ejecución
            
            # 2. ENRUTAMIENTO INTELIGENTE (Agnóstico)
            if instance.asset.category == Asset.AssetCategory.VIDEO:
                # Si es video, va a la fábrica de Proxies
                process_video_task.delay(instance.pk)
                Version.objects.filter(pk=instance.pk).update(transcoding_status='PROCESSING')
                print(f"🚀 AXIOM: Video detectado para {instance}. Tarea delegada a Celery.")
            
            elif instance.asset.category == Asset.AssetCategory.CODE:
                # Si es código (ej. un script de Blender), no hay transcodificación
                Version.objects.filter(pk=instance.pk).update(transcoding_status='COMPLETED')
                print(f"⚡ AXIOM: Script {instance} registrado. No requiere Celery.")
            
            else:
                # Otros formatos
                Version.objects.filter(pk=instance.pk).update(transcoding_status='COMPLETED')
                print(f"✅ AXIOM: Archivo genérico {instance} registrado en la línea de tiempo.")

        else:
            Version.objects.filter(pk=instance.pk).update(transcoding_status='ERROR')
            print(f"⚠️ AXIOM: Divergencia detectada. Error en ingesta inicial.")