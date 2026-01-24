from django.db import models
from django.core.exceptions import ValidationError


class MyUser(models.Model):
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=256)
    
    def __str__(self):
        return self.username


class DirectChat(models.Model):
    user1 = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name="chats1")
    user2 = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name="chats2")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user1", "user2")

    def __str__(self):
        return f"{self.user1} & {self.user2}"


# -------- GROUP MODELS FIRST --------

class GroupChat(models.Model):
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class GroupMember(models.Model):
    ROLE_CHOICES = (
        ("admin", "Admin"),
        ("member", "Member"),
    )

    group_chat = models.ForeignKey(
        GroupChat, on_delete=models.CASCADE, related_name="members"
    )
    user = models.ForeignKey(
        MyUser, on_delete=models.CASCADE, related_name="group_memberships"
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="member")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("group_chat", "user")

    def __str__(self):
        return f"{self.user} in {self.group_chat} ({self.role})"


# -------- MESSAGE MODEL LAST --------

class Message(models.Model):
    direct_chat = models.ForeignKey(
        DirectChat, on_delete=models.CASCADE, null=True, blank=True, related_name="messages"
    )
    group_chat = models.ForeignKey(
        GroupChat, on_delete=models.CASCADE, null=True, blank=True, related_name="messages"
    )
    sender = models.ForeignKey(MyUser, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        # Exactly one of direct_chat or group_chat must be set
        if bool(self.direct_chat) == bool(self.group_chat):
            raise ValidationError(
                "Message must belong to exactly one of direct_chat or group_chat."
            )

    def __str__(self):
        return f"Message {self.id}"
