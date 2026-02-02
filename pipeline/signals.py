import os
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Version
from .tasks import process_video_task

@receiver(post_save, sender=Version)
def axiom_processing_trigger(sender, instance, created, **kwargs):
    """
    Sensor de AXIOM: Disparador del Pipeline.
    Detecta la creación de una versión y activa el motor asíncrono.
    """
    if created and instance.file:
        # 1. INGESTA RÁPIDA (Metadatos y Hash)
        # Se queda aquí porque es una operación de base de datos veloz.
        archivo_fisico = instance.file.path
        ingesta_ok = instance.ingest_and_verify(archivo_fisico)
        
        if ingesta_ok:
            # 2. DISPARO ASÍNCRONO (Delegación a Celery)
            # Esto envía el ID a la tarea que ya configuramos en tasks.py
            process_video_task.delay(instance.pk)
            
            # Actualizamos el estado para que el Dashboard se mueva
            Version.objects.filter(pk=instance.pk).update(transcoding_status='PROCESSING')
            
            print(f"🚀 AXIOM: Pipeline activado para {instance}. Tarea delegada a Celery.")
        else:
            print(f"⚠️ AXIOM: Error en ingesta inicial. Pipeline abortado.")