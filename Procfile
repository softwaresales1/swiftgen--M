# This line runs your Django app with Gunicorn for handling HTTP requests
web: gunicorn Work.wsgi --log-file -

# This line runs Daphne for handling WebSocket connections
daphne -u /tmp/daphne.sock Work.asgi:application

# This line runs the Channels worker for handling background tasks
# worker: python manage.py runworker
worker: python manage.py runworker -v2 channels
