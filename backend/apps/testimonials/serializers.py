"""
Serializers for Testimonials App.
"""
from rest_framework import serializers
from .models import Testimonial


def _file_url(field_file):
    """Return absolute URL using the storage backend (handles Cloudinary prefix)."""
    if not field_file:
        return None
    try:
        url = field_file.url
        return url if url else None
    except Exception:
        return None


class TestimonialSerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Testimonial
        fields = [
            'id', 'name', 'email', 'role', 'photo', 'photo_url', 'message', 'rating', 'status',
            'has_video', 'video_type', 'video_url', 'video_file',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_photo_url(self, obj):
        return _file_url(obj.photo)

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value


class TestimonialListSerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Testimonial
        fields = [
            'id', 'name', 'role', 'photo_url', 'message', 'rating',
            'has_video', 'video_type', 'video_url', 'video_file'
        ]

    def get_photo_url(self, obj):
        return _file_url(obj.photo)


class TestimonialCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Testimonial
        fields = ['name', 'email', 'role', 'message', 'rating', 'has_video', 'video_type', 'video_url', 'video_file']

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value
