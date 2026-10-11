"""Show users (with their role) in the Django admin panel."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CampusUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active")
    # Add the role field to the built-in admin edit/create pages.
    fieldsets = UserAdmin.fieldsets + (("CampusFix", {"fields": ("role",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("CampusFix", {"fields": ("email", "role")}),)
