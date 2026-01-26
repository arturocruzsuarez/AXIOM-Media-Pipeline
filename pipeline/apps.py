from django.apps import AppConfig

class PipelineConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pipeline'

    def ready(self):
        # Esta línea es vital para que el sensor se encienda
        import pipeline.signals