"""
Celery configuration for hotel_sync project.
"""
import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotel_sync.settings')

app = Celery('hotel_sync')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Schedule (per sincronizzazioni automatiche future)
app.conf.beat_schedule = {
    'sync-suppliers-daily': {
        'task': 'sync.tasks.sync_all_suppliers',
        'schedule': 86400.0,  # 24 hours
    },
}
app.conf.timezone = 'Europe/Rome'

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
