from rest_framework.decorators import api_view, authentication_classes, permission_classes, parser_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from .models import DirectChat, GroupChat, GroupMember, Message, MyUser
from . import services
from chat_project.decoraters import login_required

# =====================================================
# 🔥 AUTH
# =====================================================

@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def login(request):
    data = request.data

    try:
        token, _ = services.login_user(
            username=data.get("username"),
            password=data.get("password"),
        )
    except ValueError as exc:
        code = str(exc)
        if code == "user_not_found":
            return Response({"error": "user not found go to register"}, status=404)
        if code == "wrong_password":
            return Response({"error": "wrong password"}, status=400)
        return Response({"error": "invalid credentials"}, status=400)

    return Response({"token": token}, status=200)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def signup(request):
    ok, payload = services.register_user(request.data)
    if ok:
        return Response(payload, status=201)
    return Response(payload, status=400)



# =====================================================
# 🔥 DIRECT CHAT
# =====================================================

def get_or_create_direct_chat(user1, user2):
    if user1.id > user2.id:
        user1, user2 = user2, user1

    chat, created = DirectChat.objects.get_or_create(
        user1=user1,
        user2=user2
    )
    return chat


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@login_required
def start_direct_chat(request):
    # Authenticated user is always one side of the chat
    user1_id = request.user.id
    # Body contains only the other user's ID (must exist in users table)
    user2_id = request.data.get("user_id")

    if not user2_id:
        return Response({"error": "user_id required"}, status=400)

    try:
        chat, messages = services.start_direct_chat_service(int(user1_id), int(user2_id))
    except ValueError as exc:
        if str(exc) == "user_not_found":
            return Response({"error": "user not found"}, status=404)
        raise

    data = []
    for m in messages:
        file_field = m.get("file")
        data.append(
            {
                "id": m["id"],
                "sender_id": m["sender_id"],
                "sender": m["sender"],
                "text": m["text"],
                "file_url": request.build_absolute_uri(file_field.url) if file_field else None,
                "created_at": m["created_at"],
            }
        )

    return Response({
        "chat_id": chat.id,
        "room_name": f"direct_{chat.id}",
        "receiver_id": int(user2_id),
        "messages": data,
    })

# LIST MY GROUPS (OLD)

@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
@login_required
def my_groups(request):

    user = request.user

    data = services.my_groups_service(user)

    return Response(data)


# LIST MY GROUPS (NEW, EXPLICITLY JWT-ONLY)

@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
@login_required
def user_groups_from_token(request):
    """Return all groups for the authenticated user, using only JWT (no body params)."""

    user = request.user  # set by JWT in Authorization header
    groups = services.my_groups_service(user)

    return Response(
        {
            "user_id": user.id,
            "username": user.username,
            "groups": groups,
        },
        status=200,
    )


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
@login_required
def group_chat_messages(request, group_id):
    """Return messages for a specific group chat if the requester is a member."""

    user = request.user
    group = get_object_or_404(GroupChat, id=group_id)

    ok, result = services.list_group_messages_service(user, group)
    if not ok:
        return Response({"error": result}, status=403)

    messages = []
    for m in result:
        file_field = m.get("file")
        messages.append(
            {
                "id": m["id"],
                "sender_id": m["sender_id"],
                "sender": m["sender"],
                "text": m["text"],
                "file_url": request.build_absolute_uri(file_field.url) if file_field else None,
                "created_at": m["created_at"],
            }
        )

    return Response(
        {
            "group_id": group.id,
            "group_name": group.name,
            "messages": messages,
        },
        status=200,
    )

@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
@login_required
def get_users(request):
    users = MyUser.objects.all()
    data = []
    for u in users:
        profile_pic_url = (
            request.build_absolute_uri(u.profile_pic.url)
            if u.profile_pic
            else None
        )
        data.append(
            {
                "id": u.id,
                "username": u.username,
                "profile_pic_url": profile_pic_url,
            }
        )

    return Response({"users": data}, status=200)


# =====================================================
# 🔥 GROUP CHAT
# =====================================================

# CREATE GROUP (CREATOR = ADMIN)

@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@login_required
def create_group(request):

    user = request.user
    name = request.data.get("name")

    if not name:
        return Response({"error": "Group name required"}, status=400)
    group = services.create_group_service(user, name)

    return Response({
        "message": "Group created successfully",
        "group_id": group.id,
        "group_name": group.name,
        "admin_id": user.id,
        "admin_username": user.username
    }, status=201)


# ADD USER TO GROUP (ADMIN ONLY)

@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@login_required
def add_user_to_group(request, group_id):

    admin = request.user
    user_ids = request.data.get("user_ids")
    user_id = request.data.get("user_id")

    group = get_object_or_404(GroupChat, id=group_id)

    # multiple users: expect a list in user_ids
    if user_ids is not None:
        if not isinstance(user_ids, list):
            return Response({"error": "user_ids must be a list"}, status=400)

        ok, result = services.add_users_to_group_service(admin, group, user_ids)
        if not ok:
            status_code = 403 if result in ("Only admins can add users", "Not allowed") else 400
            return Response({"error": result}, status=status_code)

        return Response({"results": result}, status=201)

    # single user fallback (backwards compatible)
    if not user_id:
        return Response({"error": "user_id or user_ids required"}, status=400)

    ok, msg = services.add_user_to_group_service(admin, group, user_id)
    if not ok:
        status_code = 403 if msg in ("Only admins can add users", "Not allowed") else 400
        if msg == "User not found":
            status_code = 404
        return Response({"error": msg}, status=status_code)

    return Response({"message": msg}, status=201)



@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
@login_required
def group_members(request, group_id):

    user = request.user
    group = get_object_or_404(GroupChat, id=group_id)

    ok, result = services.group_members_service(user, group)
    if not ok:
        return Response({"error": result}, status=403)

    return Response(result, status=200)


# =====================================================
# 🔥 PROFILE PHOTO
# =====================================================

@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@login_required
@parser_classes([MultiPartParser, FormParser])
def update_profile_photo(request):

    user = request.user
    file = request.FILES.get("profile_pic")

    if not file:
        return Response({"error": "profile_pic file required"}, status=400)

    user.profile_pic = file
    user.save()

    url = request.build_absolute_uri(user.profile_pic.url) if user.profile_pic else None

    return Response({
        "message": "Profile photo updated successfully",
        "profile_pic_url": url,
    }, status=200)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
@login_required
def get_profile(request):

    user = request.user

    profile_pic_url = (
        request.build_absolute_uri(user.profile_pic.url)
        if user.profile_pic
        else None
    )

    return Response(
        {
            "id": user.id,
            "username": user.username,
            "age": user.age,
            "gender": user.gender,
            "profile_pic_url": profile_pic_url,
        },
        status=200,
    )


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def test(request):
    objec = MyUser.objects.all()
    print(objec)
    return Response({"message": objec}, status=200)