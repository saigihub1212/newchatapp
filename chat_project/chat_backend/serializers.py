from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import MyUser
from django.contrib.auth.hashers import make_password
class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ['username', 'password', 'age', 'gender', 'profile_pic']
    def create(self, data):
        data["password"]=make_password(data["password"])      
        return MyUser.objects.create(**data)

    