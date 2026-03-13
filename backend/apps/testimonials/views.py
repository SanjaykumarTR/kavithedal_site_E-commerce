"""
Views for Testimonials App.
"""
import logging
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import models
from django_filters import rest_framework as filters
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger('apps')

from .models import Testimonial
from .serializers import TestimonialSerializer, TestimonialListSerializer, TestimonialCreateSerializer
from apps.accounts.utils import is_authorized_admin


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission:
    - Allow any user to read (list/retrieve)
    - Only the authorized admin email can create/update/delete
    """
    def has_permission(self, request, view):
        # Allow any request for safe methods
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # For write operations, check if user is authenticated and is the authorized admin
        if request.user and request.user.is_authenticated:
            return is_authorized_admin(request.user)
        return False


class TestimonialFilter(filters.FilterSet):
    """Filter for Testimonial model."""
    status = filters.ChoiceFilter(field_name='status', choices=Testimonial.STATUS_CHOICES)
    role = filters.ChoiceFilter(field_name='role', choices=Testimonial.ROLE_CHOICES)
    
    class Meta:
        model = Testimonial
        fields = ['status', 'role']


class TestimonialViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Testimonial CRUD operations.
    
    Public users can:
    - Create new testimonials
    - View approved testimonials
    
    Admin users can:
    - Create, update, and delete testimonials
    - Approve/reject testimonials
    """
    queryset = Testimonial.objects.all()
    filterset_class = TestimonialFilter
    search_fields = ['name', 'message']
    ordering_fields = ['created_at', 'rating']
    ordering = ['-created_at']
    
    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [IsAdminOrReadOnly()]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TestimonialCreateSerializer
        if self.action == 'list':
            return TestimonialListSerializer
        return TestimonialSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action in ['list', 'retrieve']:
            # Public users only see approved testimonials
            # Authorized admin sees all testimonials
            user = self.request.user
            if user.is_authenticated and is_authorized_admin(user):
                # Admin sees all testimonials
                return queryset
            # Non-admin users only see approved
            queryset = queryset.filter(status='approved')
        return queryset
    
    def perform_create(self, serializer):
        # Save the testimonial
        testimonial = serializer.save()
        
        # Send email to admin about new testimonial
        try:
            from django.conf import settings
            admin_email = getattr(settings, 'ADMIN_EMAIL', 'kavithedaldpi@gmail.com')
            subject = f'New Testimonial Submitted by {testimonial.name}'
            message = f"""
A new testimonial has been submitted and is awaiting approval.

Details:
- Name: {testimonial.name}
- Email: {testimonial.email or 'Not provided'}
- Role: {testimonial.role}
- Rating: {testimonial.rating} stars
- Message: {testimonial.message}

Please login to the admin panel to review and approve/reject this testimonial.
            """
            send_mail(
                subject,
                message,
                getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@kavithedal.com'),
                [admin_email],
                fail_silently=False,
            )
        except Exception as e:
            logger.error('Failed to send testimonial notification email: %s', e)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrReadOnly])
    def approve(self, request, pk=None):
        """
        POST /api/testimonials/{id}/approve/
        Approve a testimonial.
        """
        testimonial = self.get_object()
        testimonial.status = 'approved'
        testimonial.save()
        serializer = self.get_serializer(testimonial)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrReadOnly])
    def reject(self, request, pk=None):
        """
        POST /api/testimonials/{id}/reject/
        Reject a testimonial.
        """
        testimonial = self.get_object()
        testimonial.status = 'rejected'
        testimonial.save()
        serializer = self.get_serializer(testimonial)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAdminOrReadOnly])
    def pending(self, request):
        """
        GET /api/testimonials/pending/
        Get all pending testimonials (admin only).
        """
        testimonials = self.queryset.filter(status='pending')
        serializer = TestimonialSerializer(testimonials, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def average_rating(self, request):
        """
        GET /api/testimonials/average_rating/
        Get average rating of approved testimonials.
        """
        approved = self.queryset.filter(status='approved')
        if approved.exists():
            avg_rating = approved.aggregate(avg=models.Avg('rating'))['avg']
            return Response({'average_rating': round(avg_rating, 2)})
        return Response({'average_rating': 0})
