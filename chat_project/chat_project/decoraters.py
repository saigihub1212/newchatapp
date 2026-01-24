from functools import wraps
import jwt
from rest_framework.response import Response
from chat_backend.models import MyUser


def login_required(function):
    @wraps(function)
    def wrap(request, *args, **kwargs):

        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return Response({"error": "unauthenticated"}, status=401)

        try:
            token = auth_header.split(" ")[1]
            payload = jwt.decode(token, "keys", algorithms=["HS256"])

            user = MyUser.objects.get(id=payload["id"])

            # 🔥 SET USER MANUALLY (CRITICAL)
            request.user = user
            request._request.user = user   # prevents DRF touching auth

        except Exception:
            return Response({"error": "unauthenticated"}, status=401)

        return function(request, *args, **kwargs)

    return wrap
