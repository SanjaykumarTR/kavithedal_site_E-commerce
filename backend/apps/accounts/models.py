"""
Custom Admin User Model for Kavithedal Publications.
"""
import uuid
from datetime import datetime, timedelta
from django.contrib.auth.models import AbstractUser
from django.db import models


class AdminUser(AbstractUser):
    """
    Custom Admin User model with UUID as primary key.
    """
    ROLE_CHOICES = [
        ('user', 'User'),
        ('admin', 'Admin'),
        ('superadmin', 'Super Admin'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    phone = models.CharField(max_length=20, blank=True, null=True)
    profile_image = models.ImageField(upload_to='admin_profiles/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'admin_users'
        verbose_name = 'Admin User'
        verbose_name_plural = 'Admin Users'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        """Return the first_name plus the last_name."""
        return f"{self.first_name} {self.last_name}".strip() or self.email
    
    @property
    def is_admin(self):
        return self.role in ['admin', 'superadmin'] or self.is_staff

    @property
    def is_regular_user(self):
        return self.role == 'user'
    
    @property
    def is_superadmin(self):
        return self.role == 'superadmin' or self.is_superuser


class AdminOTP(models.Model):
    """
    Model to store OTP codes for admin login verification.
    """
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(AdminUser, on_delete=models.CASCADE, related_name='otps')
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)
    is_used = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'admin_otp'
        verbose_name = 'Admin OTP'
        verbose_name_plural = 'Admin OTPs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"OTP for {self.user.email}"
