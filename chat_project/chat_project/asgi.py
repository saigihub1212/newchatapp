import os

# Configure Django settings BEFORE importing anything that uses them
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chat_project.settings")
from django.core.asgi import get_asgi_application

# Initialize Django and load all apps BEFORE importing routing/consumers
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
import chat_backend.routing
from chat_backend.jwt_middleware import JWTAuthMiddleware

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTAuthMiddleware(
        URLRouter(
            chat_backend.routing.websocket_urlpatterns
        )
    ),
})
