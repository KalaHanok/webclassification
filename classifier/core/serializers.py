from rest_framework import serializers
from django.contrib.auth import get_user_model
User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    device_id = serializers.CharField()

    class Meta:
        model = User
        fields = ['username', 'password', 'device_id']

    def create(self, validated_data):
        device_id = validated_data.pop('device_id')
        user = User.objects.create_user(**validated_data)
        user.device_id = device_id
        user.save()
        return user