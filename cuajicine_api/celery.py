import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cuajicine_api.settings')

app = Celery('cuajicine_api')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()