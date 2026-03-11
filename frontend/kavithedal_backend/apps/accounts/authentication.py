"""
Custom JWT Authentication that handles is_staff from token claims.
"""
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth.models import AnonymousUser


class CustomJWTAuthentication(JWTAuthentication):
    """
    Custom JWT Authentication that extracts is_staff from token claims.
    """
    
    def get_user(self, validated_token):
        """
        Override to add is_staff from token claims.
        """
        user = super().get_user(validated_token)
        
        if user and user.is_authenticated:
            # Add is_staff from token claims if not already set
            if not user.is_staff:
                user.is_staff = validated_token.get('is_staff', False)
            
            # Also add role if available
            if hasattr(user, 'role'):
                token_role = validated_token.get('role')
                if token_role:
                    user.role = token_role
        
        return user
