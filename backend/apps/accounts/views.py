"""
Views for Accounts App - Authentication and User Management.
"""
import logging
import random
import string
from datetime import timedelta

from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone

logger = logging.getLogger('apps')

from rest_framework import status, viewsets, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import AdminUser, AdminOTP
from .serializers import (
    AdminUserSerializer, AdminUserCreateSerializer,
    LoginSerializer, PasswordChangeSerializer,
    RegisterSerializer
)
from .permissions import IsAdminUser
from .utils import _get_admin_allowed_email


class RegisterView(generics.GenericAPIView):
    """
    POST /api/register/
    User registration endpoint.
    """
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        refresh['is_staff'] = user.is_staff
        refresh['email'] = user.email
        
        return Response({
            'status': 'REGISTRATION_SUCCESS',
            'message': 'User registered successfully',
            'user': {
                'id': str(user.id),
                'email': user.email,
                'username': user.username,
                'role': user.role
            },
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'redirect': '/user-dashboard'
        }, status=status.HTTP_201_CREATED)


class LoginView(generics.GenericAPIView):
    """
    POST /api/login/
    User login endpoint.
    """
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        # Check role
        if user.role == 'admin':
            # Only allow admin access to the specific allowed email
            if user.email.lower() != _get_admin_allowed_email():
                return Response(
                    {'status': 'FAILED', 'message': 'Unauthorized: Only the designated admin can access the admin panel'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Generate OTP
            otp_code = ''.join(random.choices(string.digits, k=6))
            
            # Delete old OTPs for this user
            AdminOTP.objects.filter(user=user, is_used=False).delete()
            
            # Create new OTP with 5 minute expiry (timezone-aware)
            otp = AdminOTP.objects.create(
                user=user,
                otp_code=otp_code,
                expires_at=timezone.now() + timedelta(minutes=5)
            )
            
            # Send OTP via email
            try:
                send_mail(
                    'Your Admin Login OTP - Kavithedal Publications',
                    f'Your OTP for admin login is: {otp_code}\nThis OTP is valid for 5 minutes.\n\nIf you did not request this, please ignore this email.',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
                return Response({
                    'status': 'ADMIN_OTP_REQUIRED',
                    'admin_id': str(user.id),
                    'message': 'OTP sent to registered email',
                    'redirect': '/verify-otp'
                }, status=status.HTTP_200_OK)
            except Exception as e:
                # Log error server-side only — never expose OTP to the client
                logger.error("Failed to send admin OTP email to %s: %s", user.email, e)
                return Response(
                    {
                        'status': 'FAILED',
                        'message': 'Could not send OTP email. Please try again or contact support.',
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
        
        # For regular users, generate tokens immediately
        refresh = RefreshToken.for_user(user)
        # Add custom claims
        refresh['role'] = user.role
        refresh['is_staff'] = user.is_staff
        refresh['email'] = user.email
        
        return Response({
            'status': 'USER_LOGIN_SUCCESS',
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'role': user.role,
            'redirect': '/user-dashboard'
        }, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    """
    POST /api/verify-otp/
    Verify OTP and return tokens for admin users.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        admin_id = request.data.get('admin_id')
        otp_code = request.data.get('otp')
        
        if not admin_id or not otp_code:
            return Response(
                {'status': 'FAILED', 'message': 'admin_id and otp are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = AdminUser.objects.get(id=admin_id, role='admin')
        except AdminUser.DoesNotExist:
            return Response(
                {'status': 'FAILED', 'message': 'Invalid admin'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Check if the admin email is allowed
        if user.email.lower() != _get_admin_allowed_email():
            return Response(
                {'status': 'FAILED', 'message': 'Unauthorized: Only the designated admin can access the admin panel'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Find valid OTP (use timezone.now() for correct tz-aware comparison)
        now = timezone.now()
        try:
            otp = AdminOTP.objects.get(
                user=user,
                otp_code=otp_code,
                is_used=False,
                expires_at__gt=now,
            )
        except AdminOTP.DoesNotExist:
            # Check if there's an OTP with wrong code and increment attempts
            existing_otp = AdminOTP.objects.filter(
                user=user,
                is_used=False,
                expires_at__gt=now,
            ).first()
            
            if existing_otp:
                existing_otp.attempts += 1
                existing_otp.save()
                
                if existing_otp.attempts >= 3:
                    existing_otp.is_used = True
                    existing_otp.save()
                    return Response(
                        {'status': 'FAILED', 'message': 'Maximum attempts exceeded. Please login again.'},
                        status=status.HTTP_401_UNAUTHORIZED
                    )
            
            return Response(
                {'status': 'FAILED', 'message': 'Invalid or expired OTP'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Mark OTP as used
        otp.is_used = True
        otp.save()
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        # Add custom claims
        refresh['role'] = user.role
        refresh['is_staff'] = user.is_staff
        refresh['email'] = user.email
        
        return Response({
            'status': 'ADMIN_LOGIN_SUCCESS',
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'role': 'admin',
            'redirect': '/admin-dashboard'
        }, status=status.HTTP_200_OK)


class LogoutView(generics.GenericAPIView):
    """
    POST /api/logout/
    User logout endpoint.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RefreshTokenView(generics.GenericAPIView):
    """
    POST /api/token/refresh/
    Refresh JWT token endpoint.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        from rest_framework_simplejwt.views import TokenRefreshView
        from rest_framework_simplejwt.serializers import TokenRefreshSerializer
        
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class AdminUserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Admin User CRUD operations.
    """
    queryset = AdminUser.objects.all()
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AdminUserCreateSerializer
        return AdminUserSerializer
    
    def get_permissions(self):
        if self.action in ['create']:
            return [AllowAny()]
        return super().get_permissions()
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """
        GET /api/users/me/
        Get current user info.
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def change_password(self, request):
        """
        POST /api/users/change_password/
        Change password for current user.
        """
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'error': 'Old password is incorrect'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({'message': 'Password changed successfully'}, status=status.HTTP_200_OK)
