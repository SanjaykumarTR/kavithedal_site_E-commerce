"""
Serializers for Accounts App.
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import AdminUser, AdminOTP


class AdminUserSerializer(serializers.ModelSerializer):
    """
    Serializer for Admin User model.
    """
    class Meta:
        model = AdminUser
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'role', 'phone', 'profile_image', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AdminUserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating Admin User.
    """
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    
    class Meta:
        model = AdminUser
        fields = [
            'email', 'username', 'password', 'confirm_password',
            'first_name', 'last_name', 'role', 'phone'
        ]
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match")
        return data
    
    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        
        user = AdminUser.objects.create_user(
            password=password,
            **validated_data
        )
        return user


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    """
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    
    class Meta:
        model = AdminUser
        fields = ['email', 'username', 'password', 'confirm_password']
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match")
        
        # Check if email already exists
        if AdminUser.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError("Email already registered")
        
        return data
    
    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = AdminUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role='user'  # Default role for new users
        )
        return user


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login.
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        
        if email and password:
            # Try to find user by email
            try:
                user = AdminUser.objects.get(email=email)
            except AdminUser.DoesNotExist:
                raise serializers.ValidationError("Invalid email or password")
            
            # Check password
            if not user.check_password(password):
                raise serializers.ValidationError("Invalid email or password")
            
            if not user.is_active:
                raise serializers.ValidationError("User account is disabled")
            
            data['user'] = user
        else:
            raise serializers.ValidationError("Must include 'email' and 'password'")
        
        return data


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for password change.
    """
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("New passwords do not match")
        return data


class AdminOTPSerializer(serializers.ModelSerializer):
    """
    Serializer for AdminOTP model.
    """
    class Meta:
        model = AdminOTP
        fields = ['id', 'user', 'otp_code', 'is_used', 'expires_at', 'created_at']
        read_only_fields = ['id', 'user', 'otp_code', 'expires_at', 'created_at']


class OTPVerifySerializer(serializers.Serializer):
    """
    Serializer for verifying OTP.
    """
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=6, min_length=6)
