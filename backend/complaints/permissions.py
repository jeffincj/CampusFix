"""DRF permission classes based on the user's role."""
from rest_framework.permissions import BasePermission


class IsStudent(BasePermission):
    message = "Only students can do this."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_student


class IsStaffOrAdmin(BasePermission):
    message = "Only staff and admins can do this."

    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.is_staff_member or request.user.is_admin)


class IsAdmin(BasePermission):
    message = "Only admins can do this."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin
