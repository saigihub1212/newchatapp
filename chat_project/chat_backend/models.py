from django.db import models
from django.core.exceptions import ValidationError


class MyUser(models.Model):
    GENDER_CHOICES = (
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
    )

    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=256)

    # optional profile info
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    # userprofile = models.TextField(null=True, blank=True)
    # profile photo
    profile_pic = models.ImageField(upload_to="profile_pics/", null=True, blank=True)

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
    # text is optional now, because a message can be only media
    text = models.TextField(blank=True)
    # optional uploaded file (image, video, document, etc.)
    file = models.FileField(upload_to="chat_media/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        # Exactly one of direct_chat or group_chat must be set
        if bool(self.direct_chat) == bool(self.group_chat):
            raise ValidationError(
                "Message must belong to exactly one of direct_chat or group_chat."
            )

        # At least one of text or file must be present
        if not self.text and not self.file:
            raise ValidationError(
                "Message must contain text or a file."
            )

    def __str__(self):
        return f"Message {self.id}"
