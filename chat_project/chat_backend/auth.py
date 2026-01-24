import jwt
from rest_framework.response import Response
from chat_backend.models import MyUser

SECRET_KEY = "keys"   # 🔥 MUST MATCH YOUR LOGIN TOKEN SECRET


def get_authenticated_user(request):
    auth = request.headers.get("Authorization")

    if not auth:
        return None, Response({"error": "No Authorization header"}, status=401)

    try:
        # Expect: Bearer <token>
        
        token = auth.split(" ")[1]

        # 🔥 DECODE JWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])

        print("JWT PAYLOAD:", payload)   # DEBUG (remove later)

        # 🔥 GET USER ID FROM TOKEN
        user_id = payload.get("id")
        if not user_id:
            return None, Response({"error": "Token missing user id"}, status=401)

        # 🔥 LOAD USER
        user = MyUser.objects.get(id=user_id)

        return user, None

    except jwt.ExpiredSignatureError:
        return None, Response({"error": "Token expired"}, status=401)

    except jwt.InvalidTokenError as e:
        print("JWT ERROR:", e)
        return None, Response({"error": "Invalid token"}, status=401)

    except MyUser.DoesNotExist:
        return None, Response({"error": "User not found"}, status=401)
