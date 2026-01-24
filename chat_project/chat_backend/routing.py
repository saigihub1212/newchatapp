from django.urls import re_path
from .consumers import ChatConsumer

websocket_urlpatterns = [
    re_path(r"ws/chat/direct/(?P<direct_chat_id>\d+)/$", ChatConsumer.as_asgi()),
    re_path(r"ws/chat/group/(?P<group_id>\d+)/$", ChatConsumer.as_asgi()),
]
