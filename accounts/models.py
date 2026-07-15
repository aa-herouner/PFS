from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user with a farm role. Declared before the first migration."""

    class Role(models.TextChoices):
        OWNER = 'OWNER', 'Owner/Admin'
        MANAGER = 'MANAGER', 'Manager'
        ATTENDANT = 'ATTENDANT', 'Attendant'

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.ATTENDANT,
    )
    phone = models.CharField(max_length=20, blank=True)

    @property
    def is_owner(self):
        return self.role == self.Role.OWNER

    @property
    def is_manager(self):
        return self.role == self.Role.MANAGER

    @property
    def is_attendant(self):
        return self.role == self.Role.ATTENDANT

    def __str__(self):
        return self.get_full_name() or self.username
