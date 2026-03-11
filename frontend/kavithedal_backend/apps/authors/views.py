"""
Views for Authors App.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters import rest_framework as filters

from .models import Author
from .serializers import AuthorSerializer, AuthorListSerializer


class AuthorFilter(filters.FilterSet):
    """Filter for Author model."""
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    
    class Meta:
        model = Author
        fields = ['name']


class AuthorViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Author CRUD operations.
    
    Public users can view all authors.
    Admin users can create, update, and delete authors.
    """
    queryset = Author.objects.all()
    filterset_class = AuthorFilter
    search_fields = ['name', 'biography']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'books']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AuthorListSerializer
        return AuthorSerializer
    
    @action(detail=True, methods=['get'])
    def books(self, request, pk=None):
        """
        GET /api/authors/{id}/books/
        Get all books by this author.
        """
        author = self.get_object()
        from apps.books.serializers import BookListSerializer
        books = author.books.all()
        serializer = BookListSerializer(books, many=True)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """
        Create a new author or return existing one if same name, email, and mobile_number exists.
        """
        name = request.data.get('name', '').strip()
        email = request.data.get('email', '').strip()
        mobile_number = request.data.get('mobile_number', '').strip()
        
        # Check if author with same name, email, and mobile_number already exists
        existing_author = Author.objects.filter(
            name__iexact=name,
            email__iexact=email,
            mobile_number=mobile_number
        ).first()
        
        if existing_author:
            serializer = self.get_serializer(existing_author)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """
        Update an existing author.
        """
        return super().update(request, *args, **kwargs)
