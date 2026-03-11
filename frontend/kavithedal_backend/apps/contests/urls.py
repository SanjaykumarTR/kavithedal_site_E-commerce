"""
URL Configuration for Contests App.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ContestViewSet, ContestSubmissionViewSet

router = DefaultRouter()
router.register(r'submissions', ContestSubmissionViewSet, basename='contest-submission')
router.register(r'', ContestViewSet, basename='contest')

urlpatterns = [
    path('', include(router.urls)),
]
