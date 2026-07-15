from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Farm role', {'fields': ('role', 'phone')}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_active')
    list_filter = UserAdmin.list_filter + ('role',)
