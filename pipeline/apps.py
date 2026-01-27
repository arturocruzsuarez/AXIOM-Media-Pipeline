from django.apps import AppConfig

class PipelineConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pipeline'

    def ready(self):
        # Este import es vital. Registra los sensores (signals) 
        # en cuanto el servidor se enciende.
        import pipeline.signals