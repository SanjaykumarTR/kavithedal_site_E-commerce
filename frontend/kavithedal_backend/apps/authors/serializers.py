"""
Serializers for Authors App.
"""
from rest_framework import serializers
from .models import Author


class AuthorSerializer(serializers.ModelSerializer):
    """
    Serializer for Author model.
    """
    books_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Author
        fields = [
            'id', 'name', 'biography', 'photo', 'email', 'mobile_number',
            'social_links', 'books_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'books_count', 'created_at', 'updated_at']


class AuthorListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for Author list view.
    """
    books_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Author
        fields = ['id', 'name', 'photo', 'biography', 'email', 'mobile_number', 'books_count']
