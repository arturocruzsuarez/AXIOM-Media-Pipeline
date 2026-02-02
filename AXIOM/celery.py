import os
from celery import Celery

# Seteamos las variables de entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AXIOM.settings')

app = Celery('AXIOM')

# Leemos la configuración de Celery desde los settings de Django
app.config_from_object('django.conf:settings', namespace='CELERY')

# Autodescubrimiento de tareas en tus apps (como pipeline/tasks.py)
app.autodiscover_tasks()