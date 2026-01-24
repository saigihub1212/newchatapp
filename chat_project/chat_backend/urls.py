from django.urls import path
from .views import *

urlpatterns = [
    # auth
    path('register/', register),
    path('login/', login),
    path('welcome/', welcome),

    # users
    path('get_users/', get_users),

    # direct chat
    path('start_direct_chat/', start_direct_chat),

    # groups
    path('create_group/', create_group),

    # 🔥 MUST HAVE group_id IN URL
    path('add_user_to_group/<int:group_id>/', add_user_to_group),

    path('group_members/<int:group_id>/', group_members),
    path('my_groups/', my_groups),
]
