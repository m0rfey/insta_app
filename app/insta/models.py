from datetime import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.timezone import get_current_timezone


class User(AbstractUser):
    birthday = models.DateField(blank=True, null=True)


class InstagramAccount(models.Model):

    user = models.OneToOneField(User, related_name='instagram', on_delete=models.CASCADE)
    access_token = models.CharField(max_length=250)
    token_type = models.CharField(max_length=50)
    expires_in = models.DateTimeField()
    data = JSONField()

    class Meta:
        verbose_name_plural = 'Instagram accounts'
        verbose_name = 'Instagram account'

    def __str__(self):
        return self.user.username

    def is_not_expired(self) -> bool:
        tz = get_current_timezone()
        today = datetime.now(tz)
        if today < self.expires_in:
            return True
        return False
