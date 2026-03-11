"""
Utility functions for Kavithedal Publications.
"""

# Admin email that is allowed to access the admin panel
ADMIN_ALLOWED_EMAIL = 'kavithedaldpi@gmail.com'


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
    
    return user.email.lower() == ADMIN_ALLOWED_EMAIL


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
