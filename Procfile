web: gunicorn hotel_sync.wsgi --log-file -
worker: celery -A hotel_sync worker --loglevel=error
beat: celery -A hotel_sync beat --loglevel=error
