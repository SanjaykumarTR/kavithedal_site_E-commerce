"""
URL Configuration for Books App.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BookViewSet, CategoryViewSet, BookSubmissionViewSet, ContactMessageViewSet, 
    image_diagnostic, check_pdf_access, update_reading_progress, get_reading_progress
)

router = DefaultRouter()
router.register(r'contact-messages', ContactMessageViewSet, basename='contact-message')
router.register(r'submissions', BookSubmissionViewSet, basename='book-submission')
router.register(r'', BookViewSet, basename='book')

urlpatterns = [
    path('image-diagnostic/', image_diagnostic, name='image-diagnostic'),
    
    # Secure PDF access endpoints
    path('<uuid:book_id>/check-access/', check_pdf_access, name='check-pdf-access'),
    path('<uuid:book_id>/reading-progress/update/', update_reading_progress, name='update-reading-progress'),
    path('<uuid:book_id>/reading-progress/', get_reading_progress, name='get-reading-progress'),
    
    path('', include(router.urls)),
]
