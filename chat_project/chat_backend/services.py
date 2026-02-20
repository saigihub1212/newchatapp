from typing import Dict, List, Tuple

import jwt
from datetime import datetime, timedelta
from django.contrib.auth.hashers import check_password
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import MyUser, DirectChat, GroupChat, GroupMember, Message
from .serializers import RegisterSerializer
from . import repositories as repo


JWT_SECRET = "keys"
JWT_ALGORITHM = "HS256"


# =========================
# AUTH / USER SERVICES
# =========================


def login_user(username: str, password: str) -> Tuple[str, MyUser]:
    """Validate credentials and return (token, user) or raise ValueError."""
    user = repo.get_user_by_username(username)
    if not user:
        raise ValueError("user_not_found")

    if not check_password(password, user.password):
        raise ValueError("wrong_password")

    token = jwt.encode(
        {"id": user.id, "exp": datetime.utcnow() + timedelta(hours=24)},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    return token, user


def register_user(data) -> Tuple[bool, Dict]:
    """Register a new user using DRF serializer; returns (success, payload)."""
    serializer = RegisterSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return True, {"message": "User registered successfully"}
    return False, serializer.errors


def list_users() -> List[Dict]:
    return list(repo.list_users_basic())


# =========================
# DIRECT CHAT SERVICES
# =========================


def start_direct_chat_service(user1_id: int, user2_id: int) -> Tuple[DirectChat, List[Dict]]:
    """Create or fetch a direct chat between two users and return chat + messages."""
    try:
        user1 = repo.get_user_by_id(user1_id)
        user2 = repo.get_user_by_id(user2_id)
    except MyUser.DoesNotExist:
        # Let the view decide how to map this to an HTTP response
        raise ValueError("user_not_found")

    chat, _ = repo.get_or_create_direct_chat(user1, user2)

    messages = repo.list_messages_for_direct_chat(chat)
    data: List[Dict] = []
    for m in messages:
        data.append(
            {
                "id": m.id,
                "sender_id": m.sender.id,
                "sender": m.sender.username,
                "text": m.text,
                "file": m.file,  # caller builds absolute URL if needed
                "created_at": m.created_at,
            }
        )

    return chat, data


# =========================
# GROUP CHAT SERVICES
# =========================

def my_groups_service(user: MyUser) -> List[Dict]:
    groups = repo.list_groups_for_user(user)
    data = [{"id": g.id, "name": g.name} for g in groups]
    return data


def list_group_messages_service(user: MyUser, group: GroupChat) -> Tuple[bool, List[Dict] | str]:
    """Return (ok, data_or_error). Only members (including admins) can view messages."""
    if not repo.is_group_member(group, user):
        return False, "Not allowed"

    messages_qs = repo.list_messages_for_group_chat(group)
    data: List[Dict] = []
    for m in messages_qs:
        data.append(
            {
                "id": m.id,
                "sender_id": m.sender.id,
                "sender": m.sender.username,
                "text": m.text,
                "file": m.file,  # caller builds absolute URL if needed
                "created_at": m.created_at,
            }
        )

    return True, data


def create_group_service(creator: MyUser, name: str) -> GroupChat:
    group, created = repo.create_group(name)
    # add creator as admin (idempotent; unique_together on GroupMember prevents duplicates)
    repo.add_group_member(group, creator, role="admin")
    return group


def add_user_to_group_service(admin: MyUser, group: GroupChat, user_id: int) -> Tuple[bool, str]:
    """Return (success, error_message_if_any)."""
    if not repo.is_group_admin(group, admin):
        return False, "Only admins can add users"

    try:
        new_user = repo.get_user_by_id(user_id)
    except MyUser.DoesNotExist:
        return False, "User not found"

    member, created = repo.add_group_member(group, new_user)
    if not created:
        return False, "User already in group"

    # Notify the added user via WebSocket (if connected)
    channel_layer = get_channel_layer()
    if channel_layer is not None:
        async_to_sync(channel_layer.group_send)(
            f"user_{new_user.id}",
            {
            "group_id": group.id,
                "group_name": group.name,
                "added_by_id": admin.id,
                "added_by_username": admin.username,
            },
        )

    return True, "User added successfully"


def add_users_to_group_service(admin: MyUser, group: GroupChat, user_ids: List[int]) -> Tuple[bool, List[Dict] | str]:
    """Add multiple users to a group.

    Returns (ok, details_or_error).
    """
    if not repo.is_group_admin(group, admin):
        return False, "Only admins can add users"

    channel_layer = get_channel_layer()
    results: List[Dict] = []

    for raw_id in user_ids:
        try:
            uid = int(raw_id)
        except (TypeError, ValueError):
            results.append({"user_id": raw_id, "status": "invalid_id"})
            continue

        try:
            new_user = repo.get_user_by_id(uid)
        except MyUser.DoesNotExist:
            results.append({"user_id": uid, "status": "not_found"})
            continue

        member, created = repo.add_group_member(group, new_user)
        if not created:
            results.append({"user_id": uid, "status": "already_in_group"})
            continue

        # send notification per successfully added user
        if channel_layer is not None:
            async_to_sync(channel_layer.group_send)(
                f"user_{new_user.id}",
                {
                    "type": "group.added",
                    "event": "group_added",
                    "group_id": group.id,
                    "group_name": group.name,
                    "added_by_id": admin.id,
                    "added_by_username": admin.username,
                },
            )

        results.append({"user_id": uid, "status": "added"})

    return True, results


def group_members_service(user: MyUser, group: GroupChat) -> Tuple[bool, List[Dict] | str]:
    if not repo.is_group_member(group, user):
        return False, "Not allowed"

    members = repo.list_group_members(group)
    data = [{"group_id": group.id},{"name":group.name}] + [
        {
            "id": m.user.id,
            "username": m.user.username,
            "role": m.role,
        }
        for m in members
    ]
    return True, data



# =========================
# MESSAGE SERVICES
# =========================


def send_direct_message_service(user: MyUser, chat: DirectChat, text: str, file) -> Message:
    # Ensure user is a participant in the chat
    if user.id not in (chat.user1_id, chat.user2_id):
        raise PermissionError("not_allowed")

    # create the message in DB
    message = repo.create_direct_message(chat, user, text=text, file=file)

    # Notify the other participant via the user's notification group (if connected)
    try:
        other_user_id = chat.user2_id if user.id == chat.user1_id else chat.user1_id
    except Exception:
        other_user_id = None

    channel_layer = get_channel_layer()
    if channel_layer is not None and other_user_id is not None:
        async_to_sync(channel_layer.group_send)(
            f"user_{other_user_id}",
            {
                "type": "message.received",
                "event": "message_received",
                "chat_type": "direct",
                "chat_id": chat.id,
                "message_id": message.id,
                "sender_id": user.id,
                "sender": user.username,
                "text": message.text,
                "created_at": message.created_at.isoformat(),
            },
        )

    return message


def send_group_message_service(user: MyUser, group: GroupChat, text: str, file) -> Message:
    if not repo.is_group_member(group, user):
        raise PermissionError("not_allowed")

    return repo.create_group_message(group, user, text=text, file=file)
