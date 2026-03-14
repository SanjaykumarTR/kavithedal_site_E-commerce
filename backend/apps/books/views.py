"""
Views for secure file access - PDFs can only be downloaded by purchasers.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import FileResponse, Http404
from django.conf import settings
import os
import logging

logger = logging.getLogger('apps')

from apps.books.models import Book, Category, BookSubmission, ContactMessage
from apps.books.serializers import BookSerializer, BookListSerializer, BookCreateUpdateSerializer, CategorySerializer, BookSubmissionSerializer, ContactMessageSerializer
from apps.orders.models import UserLibrary
from apps.accounts.utils import is_authorized_admin


class BookViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Book model with CRUD operations.
    """
    queryset = Book.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'list':
            return BookListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return BookCreateUpdateSerializer
        return BookSerializer
    
    def get_queryset(self):
        from apps.accounts.utils import is_authorized_admin
        queryset = Book.objects.select_related('author', 'category').all()

        # Admins see all books; regular users see only active ones
        if not is_authorized_admin(self.request.user):
            queryset = queryset.filter(is_active=True)

        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__name=category)

        # Filter by featured
        featured = self.request.query_params.get('featured')
        if featured:
            queryset = queryset.filter(is_featured=True)

        # Search by title or author name
        search = self.request.query_params.get('search')
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(author__name__icontains=search)
            )

        return queryset


class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Category model with CRUD operations.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class IsPurchasedPermission(permissions.BasePermission):
    """Permission to check if user has purchased the book."""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return True
    
    def has_object_permission(self, request, view, obj):
        # Check if user has purchased this book
        has_access = UserLibrary.objects.filter(
            user=request.user,
            book=obj
        ).exists()
        
        # Also allow the authorized admin
        if is_authorized_admin(request.user):
            return True
            
        return has_access


class SecureFileView(APIView):
    """
    API View to serve PDF files securely.
    Only users who have purchased the book can access the PDF.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, book_id):
        # Check if user has purchased the book
        has_access = UserLibrary.objects.filter(
            user=request.user,
            book_id=book_id
        ).exists()
        
        # Allow authorized admin access
        if not has_access and not is_authorized_admin(request.user):
            return Response(
                {'error': 'You do not have access to this file. Please purchase the book first.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get the book
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return Response(
                {'error': 'Book not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not book.pdf_file:
            return Response(
                {'error': 'No PDF file available for this book'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Return the Cloudinary (or local dev) URL — the access check above
        # already verified the user is authorised. The frontend opens this URL.
        try:
            pdf_url = book.pdf_file.url
        except Exception as e:
            logger.error('Could not resolve PDF URL for book %s: %s', book_id, e)
            return Response(
                {'error': 'PDF file is not accessible'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({'pdf_url': pdf_url, 'title': book.title})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def check_pdf_access(request, book_id):
    """Check if user has access to a book's PDF."""
    has_access = UserLibrary.objects.filter(
        user=request.user,
        book_id=book_id
    ).exists()
    
    # Also allow the authorized admin
    if is_authorized_admin(request.user):
        has_access = True
    
    try:
        book = Book.objects.get(id=book_id)
        has_pdf = bool(book.pdf_file)
    except Book.DoesNotExist:
        has_pdf = False
    
    return Response({
        'has_access': has_access,
        'has_pdf': has_pdf,
        'book_id': book_id
    })


class BookSubmissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for BookSubmission model.
    Public users can submit books.
    The authorized admin can view and manage submissions.
    """
    queryset = BookSubmission.objects.all()
    serializer_class = BookSubmissionSerializer
    
    def get_permissions(self):
        if self.action in ['create']:
            return [permissions.AllowAny()]  # Allow public to submit
        # Only the authorized admin can list/update/delete
        from apps.accounts.permissions import IsAdminUser
        return [IsAdminUser()]
    
    def get_serializer_class(self):
        return BookSubmissionSerializer
    
    def get_queryset(self):
        if is_authorized_admin(self.request.user):
            return BookSubmission.objects.all()
        return BookSubmission.objects.none()
    
    def perform_create(self, serializer):
        # Save the submission
        submission = serializer.save()
        
        # Send email to admin
        try:
            from django.conf import settings
            from django.core.mail import send_mail
            admin_email = getattr(settings, 'ADMIN_EMAIL', 'kavithedaldpi@gmail.com')
            subject = f'New Book Submission: {submission.book_title}'
            message = f"""
A new book has been submitted for review.

Details:
- Name: {submission.name}
- Email: {submission.email}
- Contact: {submission.contact}
- Book Title: {submission.book_title}
- Description: {submission.description}

Please login to the admin panel to review this submission.
            """
            send_mail(
                subject,
                message,
                getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@kavithedal.com'),
                [admin_email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Error sending email: {e}")


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def image_diagnostic(request):
    """Public diagnostic endpoint: shows stored cover_image name + resolved URL for every book."""
    from apps.books.serializers import _file_url
    books = Book.objects.all().order_by('-created_at')
    results = []
    for book in books:
        stored = book.cover_image.name if book.cover_image else None
        try:
            raw_url = book.cover_image.url if book.cover_image else None
        except Exception as e:
            raw_url = f'ERROR: {e}'
        resolved = _file_url(book.cover_image, request, resource_type='image')
        results.append({
            'title': book.title,
            'stored_name': stored,
            'raw_url': raw_url,
            'resolved_url': resolved,
        })
    from django.http import JsonResponse
    return JsonResponse({'books': results})


class ContactMessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ContactMessage model.
    Public users can submit contact messages.
    The authorized admin can view and manage messages.
    """
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    
    def get_permissions(self):
        if self.action in ['create']:
            return [permissions.AllowAny()]  # Allow public to submit
        # Only the authorized admin can list/update/delete
        from apps.accounts.permissions import IsAdminUser
        return [IsAdminUser()]
    
    def get_serializer_class(self):
        return ContactMessageSerializer
    
    def get_queryset(self):
        if is_authorized_admin(self.request.user):
            return ContactMessage.objects.all()
        return ContactMessage.objects.none()
    
    def perform_create(self, serializer):
        # Save the message
        message = serializer.save()
        
        # Send email to admin
        try:
            from django.conf import settings
            from django.core.mail import send_mail
            admin_email = getattr(settings, 'ADMIN_EMAIL', 'kavithedaldpi@gmail.com')
            subject = f'New Contact Message: {message.name}'
            message_text = f"""
You have received a new contact message.

From: {message.name}
Email: {message.email}

Message:
{message.message}

Please login to the admin panel to respond.
            """
            send_mail(
                subject,
                message_text,
                getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@kavithedal.com'),
                [admin_email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Error sending email: {e}")
