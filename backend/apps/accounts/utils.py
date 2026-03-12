"""
Utility functions for Kavithedal Publications.
"""
import os
from django.conf import settings


def _get_admin_allowed_email():
    """
    Return the admin email from Django settings (which reads from the ADMIN_EMAIL
    environment variable). Fallback to empty string so the check fails safely
    rather than allowing an unexpected email.
    """
    return getattr(settings, 'ADMIN_EMAIL', '').lower().strip()


# Kept for backwards-compatibility — dynamic property via function above
ADMIN_ALLOWED_EMAIL = property(_get_admin_allowed_email)


def is_authorized_admin(user):
    """
    Check if user is authorized to access admin panel.
    
    Only the specific admin email (kavithedaldpi@gmail.com) is allowed
    to access the admin panel regardless of their role.
    
    Args:
        user: The user object to check
        
    Returns:
        bool: True if user is authorized admin, False otherwise
    """
    if not user or not hasattr(user, 'is_authenticated'):
        return False
    
    if not user.is_authenticated:
        return False
    
    # Check if user has the allowed email
    if not hasattr(user, 'email') or not user.email:
        return False
    
    return user.email.lower() == _get_admin_allowed_email()


def is_admin_user(user):
    """
    Check if user has admin role AND is the authorized admin email.
    
    This is stricter than is_authorized_admin - it requires both:
    1. The user to have admin/superadmin role
    2. The user to have the allowed email
    
    Args:
        user: The user object to check
        
    Returns:
        bool: True if user is admin with allowed email, False otherwise
    """
    if not is_authorized_admin(user):
        return False
    
    # Check role as well
    role = getattr(user, 'role', None)
    return role in ['admin', 'superadmin']
