from datetime import datetime

from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserListSerializer(serializers.ModelSerializer):
    active = serializers.SerializerMethodField(read_only=True)
    age = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'age', 'active')

    def get_active(self, obj):
        return obj.is_active

    def get_age(self, obj):
        today = datetime.today()
        if obj.birthday is not None:
            return today.year - obj.birthday.year
        return None


class UserRetrieveSerializer(UserListSerializer):

    class Meta:
        model = User
        fields = ('username', 'age', 'active', 'last_login', 'date_joined', 'email', 'first_name', 'last_name')


class MediaSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    media_type = serializers.CharField(read_only=True)
    media_url = serializers.CharField(read_only=True)
    permalink = serializers.CharField(read_only=True)
    timestamp = serializers.DateTimeField(read_only=True)
    username = serializers.CharField(read_only=True)
