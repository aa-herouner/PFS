from django import forms
from django.contrib.auth.forms import (
    PasswordChangeForm,
    UserCreationForm,
)

from core.forms import INPUT_CLASS, StyledFormMixin

from .models import User


class UserCreateForm(StyledFormMixin, UserCreationForm):
    """Owner-facing: create a user and set their role."""

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phone', 'role')


class UserEditForm(StyledFormMixin, forms.ModelForm):
    """Owner-facing: edit an existing user's details, role and active state.

    Password is managed separately (Django admin / password reset), not here.
    """

    class Meta:
        model = User
        fields = (
            'username', 'first_name', 'last_name', 'email', 'phone',
            'role', 'is_active',
        )


class ProfileForm(StyledFormMixin, forms.ModelForm):
    """Self-service: a user edits their own basic details (not role/active)."""

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone')


class StyledPasswordChangeForm(StyledFormMixin, PasswordChangeForm):
    """PasswordChangeForm with Tailwind-styled inputs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', INPUT_CLASS)
