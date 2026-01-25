import jwt
from urllib.parse import parse_qs

from channels.db import database_sync_to_async

from chat_backend.models import MyUser


JWT_SECRET = "keys"  # must match login() and login_required decorator
JWT_ALGORITHM = "HS256"


@database_sync_to_async
def get_user_from_token(token: str):
    if not token:
        return None

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("id")
        if not user_id:
            return None
        return MyUser.objects.get(id=user_id)
    except Exception:
        # invalid token, expired, or user not found
        return None


class JWTAuthMiddleware:
    """Simple JWT auth middleware for Django Channels.

    ASGI-style middleware: awaits the inner app with (scope, receive, send).
    Expects token in the WebSocket query string as ?token=<jwt>.
    Sets scope["user"] to a MyUser instance or None.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        scope = dict(scope)

        query_string = scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string)
        token = query_params.get("token", [None])[0]

        user = await get_user_from_token(token)
        scope["user"] = user

        return await self.app(scope, receive, send)
