"""
URL Configuration for Books App.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookViewSet, CategoryViewSet, BookSubmissionViewSet, ContactMessageViewSet

router = DefaultRouter()
router.register(r'contact-messages', ContactMessageViewSet, basename='contact-message')
router.register(r'submissions', BookSubmissionViewSet, basename='book-submission')
router.register(r'', BookViewSet, basename='book')

urlpatterns = [
    path('', include(router.urls)),
]
