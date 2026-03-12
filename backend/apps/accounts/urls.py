"""
URL Configuration for Accounts App.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LoginView, LogoutView, RefreshTokenView, AdminUserViewSet, VerifyOTPView, RegisterView

router = DefaultRouter()
router.register(r'users', AdminUserViewSet, basename='admin-user')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('token/refresh/', RefreshTokenView.as_view(), name='token_refresh'),
    path('', include(router.urls)),
]
