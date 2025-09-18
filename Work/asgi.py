import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from chat.routing import wsPattern
from Portal.routing import websocket_urlpatterns

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Work.settings")

http_response_app = get_asgi_application()

# Combine all websocket URL patterns
all_websocket_patterns = wsPattern + websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": http_response_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(all_websocket_patterns)
    ),
})
