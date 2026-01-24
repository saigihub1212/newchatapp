import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import DirectChat, GroupChat, Message, MyUser



class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = None   # 🔥 IMPORTANT: always define first

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
        # 🔥 ONLY DISCARD IF room_name EXISTS
        if self.room_name:
            await self.channel_layer.group_discard(self.room_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)

        sender_id = data["sender_id"]   # ⚠️ insecure, we’ll fix later
        text = data["text"]

        message = await self.create_message(sender_id, text)

        await self.channel_layer.group_send(
            self.room_name,
            {
                "type": "chat.message",
                "id": message.id,
                "sender_id": sender_id,
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
            return Message.objects.create(
                direct_chat=chat,
                sender=sender,
                text=text,
            )
        else:
            group = GroupChat.objects.get(id=self.group_id)
            return Message.objects.create(
                group_chat=group,
                sender=sender,
                text=text,
            )
