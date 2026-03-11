"""
Custom permissions for Kavithedal Publications.
"""
from rest_framework.permissions import BasePermission
from .utils import is_authorized_admin, ADMIN_ALLOWED_EMAIL


class IsAdminUser(BasePermission):
    """
    Custom permission to only allow admin users with the specific allowed email.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return is_authorized_admin(request.user)


class IsRegularUser(BasePermission):
    """
    Custom permission to only allow regular users.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role == 'user'
