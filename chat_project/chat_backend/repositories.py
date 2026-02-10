from typing import List, Optional, Tuple

from django.db.models import QuerySet

from .models import MyUser, DirectChat, GroupChat, GroupMember, Message


# =========================
# USER REPOSITORY
# =========================


def get_user_by_username(username: str) -> Optional[MyUser]:
    return MyUser.objects.filter(username=username).first()


def get_user_by_id(user_id: int) -> MyUser:
    return MyUser.objects.get(id=user_id)


def list_users_basic() -> QuerySet:
    return MyUser.objects.all().values("id", "username")


# =========================
# DIRECT CHAT REPOSITORY
# =========================


def get_or_create_direct_chat(user1: MyUser, user2: MyUser) -> Tuple[DirectChat, bool]:
    # keep ordering stable so unique_together works as expected
    if user1.id > user2.id:
        user1, user2 = user2, user1

    chat, created = DirectChat.objects.get_or_create(user1=user1, user2=user2)
    return chat, created


def get_direct_chat_by_id(chat_id: int) -> DirectChat:
    return DirectChat.objects.get(id=chat_id)


def list_messages_for_direct_chat(chat: DirectChat) -> QuerySet:
    return Message.objects.filter(direct_chat=chat).order_by("created_at")


# =========================
# GROUP CHAT REPOSITORY
# =========================


def create_group(name: str) -> Tuple[GroupChat, bool]:
    """Create a group by name if it does not exist, or return the existing one.

    Returns (group, created).
    """
    return GroupChat.objects.get_or_create(name=name)


def get_group_by_id(group_id: int) -> GroupChat:
    return GroupChat.objects.get(id=group_id)


def add_group_member(group: GroupChat, user: MyUser, role: str = "member") -> Tuple[GroupMember, bool]:
    return GroupMember.objects.get_or_create(
        group_chat=group,
        user=user,
        defaults={"role": role},
    )


def is_group_admin(group: GroupChat, user: MyUser) -> bool:
    return GroupMember.objects.filter(group_chat=group, user=user, role="admin").exists()


def is_group_member(group: GroupChat, user: MyUser) -> bool:
    return GroupMember.objects.filter(group_chat=group, user=user).exists()


def list_group_members(group: GroupChat) -> QuerySet:
    return GroupMember.objects.filter(group_chat=group).select_related("user")


def list_groups_for_user(user: MyUser) -> QuerySet:
    return GroupChat.objects.filter(members__user=user)


# =========================
# MESSAGE REPOSITORY
# =========================


def create_direct_message(chat: DirectChat, sender: MyUser, text: str = "", file=None) -> Message:
    return Message.objects.create(
        direct_chat=chat,
        sender=sender,
        text=text,
        file=file,
    )


def create_group_message(group: GroupChat, sender: MyUser, text: str = "", file=None) -> Message:
    return Message.objects.create(
        group_chat=group,
        sender=sender,
        text=text,
        file=file,
    )


def list_messages_for_group_chat(group: GroupChat) -> QuerySet:
    return Message.objects.filter(group_chat=group).select_related("sender").order_by("created_at")
