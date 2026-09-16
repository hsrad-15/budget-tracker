from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    """
    Custom user model that uses email as the unique identifier
    instead of username, per spec (Email/Password authentication).
    """

    username = None
    email = models.EmailField("email address", unique=True)
    full_name = models.CharField(max_length=150, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

    @property
    def display_name(self):
        return self.full_name or self.email.split("@")[0]
