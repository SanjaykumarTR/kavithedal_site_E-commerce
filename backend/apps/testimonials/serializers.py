"""
Serializers for Testimonials App.
"""
from rest_framework import serializers
from .models import Testimonial


class TestimonialSerializer(serializers.ModelSerializer):
    """
    Serializer for Testimonial model.
    """
    class Meta:
        model = Testimonial
        fields = [
            'id', 'name', 'email', 'role', 'message', 'rating', 'status',
            'has_video', 'video_type', 'video_url', 'video_file',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value


class TestimonialListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for Testimonial list view.
    """
    class Meta:
        model = Testimonial
        fields = ['id', 'name', 'role', 'message', 'rating', 'has_video', 'video_type', 'video_url', 'video_file']


class TestimonialCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating Testimonial.
    """
    class Meta:
        model = Testimonial
        fields = ['name', 'email', 'role', 'message', 'rating', 'has_video', 'video_type', 'video_url', 'video_file']
    
    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value
