from django.urls import path
from .views import *

urlpatterns = [
    # simple test page

    # auth
    path('signup/', signup),
    path('login/', login),

    # users
    path('get_users/', get_users),

    # direct chat
    path('start_direct_chat/', start_direct_chat),


    # groups
    path('create_group/', create_group),
    path('my_groups/', my_groups),
    path('user_groups_from_token/', user_groups_from_token),
    path('group_chat_messages/<int:group_id>/', group_chat_messages),

    # 🔥 MUST HAVE group_id IN URL
    path('add_user_to_group/<int:group_id>/', add_user_to_group),

    path('group_members/<int:group_id>/', group_members),
    

    # profile
    path('update_profile_photo/', update_profile_photo),
    path('get_profile/', get_profile),
    path('test/', test),
]
