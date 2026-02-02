from django.apps import AppConfig

class PipelineConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pipeline'

    def ready(self):
        # Este import dentro de ready() es lo que "enciende" las señales
        import pipeline.signals