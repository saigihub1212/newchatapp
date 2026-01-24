from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import MyUser
from django.contrib.auth.hashers import make_password
class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ['username', 'password']
    def create(self, data):
        data["password"]=make_password(data["password"])      
        return MyUser.objects.create(**data)

    # def retrive(self,data):
    #     print(self.fields["username"].validators)
    #     user = authenticate(
    #         username=data.get("username"),
    #         password=data.get("password")
    #     )

    #     if not user:
    #         raise serializers.ValidationError("Invalid username or password")

    #     if not user.is_active:
    #         raise serializers.ValidationError("User account is disabled")

    #     data["user"] = user
    #     return data