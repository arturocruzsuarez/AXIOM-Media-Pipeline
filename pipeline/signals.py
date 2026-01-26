from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Version

@receiver(post_save, sender=Version)
def auto_ingest_logic(sender, instance, created, **kwargs):
    """
    Este sensor detecta cuando se sube un archivo y:
    1. Calcula su hash SHA-256.
    2. Lo guarda en el Asset padre para cumplir con MovieLabs.
    """
    if created and instance.file:
        # Llamamos a la función que definimos en tu modelo Version
        archivo_fisico = instance.file.path
        exito = instance.ingest_and_verify(archivo_fisico)
        
        if exito:
            print(f"🚀 AXIOM: Asset '{instance.asset.name}' actualizado con éxito.")
        else:
            print(f"⚠️ AXIOM: El hash ya estaba registrado o el archivo es idéntico.")