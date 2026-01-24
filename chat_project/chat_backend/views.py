from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.contrib.auth.hashers import check_password
from datetime import datetime, timedelta
import jwt

from .models import *
from .serializers import RegisterSerializer
from chat_project.decoraters import login_required


# =====================================================
# 🔥 AUTH
# =====================================================

@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def login(request):
    data = request.data  

    user = MyUser.objects.filter(username=data.get("username")).first()
    if not user:
        return Response({"error": "user not found go to register"}, status=404)

    if not check_password(data.get("password"), user.password):
        return Response({"error": "wrong password"}, status=400)

    token = jwt.encode(
        {"id": user.id, "exp": datetime.utcnow() + timedelta(hours=24)},
        "keys",
        algorithm="HS256"
    )

    return Response({"token": token}, status=200)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()
        return Response({"message": "User registered successfully"}, status=201)

    return Response(serializer.errors, status=400)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
@login_required
def welcome(request):
    return Response({"message": "welcome"}, status=200)


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
    user1_id = request.data.get("user1")
    user2_id = request.data.get("user2")

    if not user1_id or not user2_id:
        return Response({"error": "user1 and user2 required"}, status=400)

    user1 = MyUser.objects.get(id=user1_id)
    user2 = MyUser.objects.get(id=user2_id)

    chat = get_or_create_direct_chat(user1, user2)

    messages = Message.objects.filter(direct_chat=chat).order_by("created_at")

    data = []
    for m in messages:
        data.append({
            "id": m.id,
            "sender_id": m.sender.id,
            "sender": m.sender.username,
            "text": m.text,
            "created_at": m.created_at,
        })

    return Response({
        "chat_id": chat.id,
        "messages": data
    })


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
@login_required
def get_users(request):
    users = MyUser.objects.all().values("id", "username")
    return Response({"users": list(users)}, status=200)


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

    group = GroupChat.objects.create(name=name)

    # add creator as admin
    GroupMember.objects.create(
        group_chat=group,
        user=user,
        role="admin"
    )

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
    user_id = request.data.get("user_id")

    if not user_id:
        return Response({"error": "user_id required"}, status=400)

    group = get_object_or_404(GroupChat, id=group_id)

    # check admin
    is_admin = GroupMember.objects.filter(
        group_chat=group,
        user=admin,
        role="admin"
    ).exists()

    if not is_admin:
        return Response({"error": "Only admins can add users"}, status=403)

    try:
        new_user = MyUser.objects.get(id=user_id)
    except MyUser.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    member, created = GroupMember.objects.get_or_create(
        group_chat=group,
        user=new_user,
        defaults={"role": "member"}
    )

    if not created:
        return Response({"error": "User already in group"}, status=400)

    return Response({"message": "User added successfully"}, status=201)



@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
@login_required
def group_members(request, group_id):

    user = request.user
    group = get_object_or_404(GroupChat, id=group_id)

    is_member = GroupMember.objects.filter(
        group_chat=group,
        user=user
    ).exists()

    if not is_member:
        return Response({"error": "Not allowed"}, status=403)

    members = GroupMember.objects.filter(group_chat=group).select_related("user")

    data = [
        {
            "id": m.user.id,
            "username": m.user.username,
            "role": m.role
        }
        for m in members
    ]

    return Response(data)


# LIST MY GROUPS

@api_view(["GET"])

@authentication_classes([])
@permission_classes([AllowAny])
@login_required
def my_groups(request):

    user = request.user

    groups = GroupChat.objects.filter(members__user=user)

    data = [{"id": g.id, "name": g.name} for g in groups]

    return Response(data)
