import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from .models import DirectChat, GroupChat, MyUser
from . import services


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # always predefine attributes so disconnect() is safe
        print(self.scope["user"])
        self.room_name = None
        self.chat_type = None
        self.direct_chat_id = None
        self.group_id = None

        # User is set by JWTAuthMiddleware; require authentication
        self.user = self.scope.get("user")
        if not self.user:
            await self.close()
            return

        url_kwargs = self.scope["url_route"]["kwargs"]

        self.direct_chat_id = url_kwargs.get("direct_chat_id")
        self.group_id = url_kwargs.get("group_id")

        if self.direct_chat_id:
            self.chat_type = "direct"
            self.room_name = f"direct_{self.direct_chat_id}"

        elif self.group_id:
            self.chat_type = "group"
            self.room_name = f"group_{self.group_id}"

        else:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Only discard if we successfully joined a room
        if getattr(self, "room_name", None):
            await self.channel_layer.group_discard(self.room_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)

        # sender is always the authenticated WebSocket user
        if not self.user:
            await self.close()
            return

        text = data.get("text", "")
        try:
            message = await self.create_message(self.user.id, text)
        except PermissionError:
            # User is not allowed to post in this chat; close gracefully
            await self.close()
            return

        await self.channel_layer.group_send(
            self.room_name,
            {
                "type": "chat.message",
                "id": message.id,
                "sender_id": self.user.id,
                "sender": self.user.username,
                "text": message.text,
                "created_at": message.created_at.isoformat(),
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    # ---------------- DB ----------------

    @database_sync_to_async
    def create_message(self, sender_id, text):
        sender = MyUser.objects.get(id=sender_id)

        if self.chat_type == "direct":
            chat = DirectChat.objects.get(id=self.direct_chat_id)
            return services.send_direct_message_service(sender, chat, text, None)
        else:
            group = GroupChat.objects.get(id=self.group_id)
            return services.send_group_message_service(sender, group, text, None)


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # each connected user joins their personal notification group
        self.user = self.scope.get("user")
        if not self.user:
            await self.close()
            return

        self.room_name = f"user_{self.user.id}"
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if getattr(self, "room_name", None):
            await self.channel_layer.group_discard(self.room_name, self.channel_name)

    async def group_added(self, event):
        # push notification about being added to a group
        await self.send(text_data=json.dumps(event))

