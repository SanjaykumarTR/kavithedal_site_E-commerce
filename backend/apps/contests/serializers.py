"""
Serializers for Contests App.
"""
from rest_framework import serializers
from .models import Contest, ContestSubmission


def _file_url(field_file):
    """Return absolute URL using the storage backend (handles Cloudinary prefix)."""
    if not field_file:
        return None
    try:
        url = field_file.url
        return url if url else None
    except Exception:
        return None


class ContestSubmissionSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.username')
    contest_title = serializers.ReadOnlyField(source='contest.title')

    class Meta:
        model = ContestSubmission
        fields = ['id', 'contest', 'contest_title', 'user', 'user_name',
                  'participant_name', 'participant_email', 'participant_contact',
                  'content_type', 'title', 'content', 'status', 'created_at']
        read_only_fields = ['id', 'user', 'status', 'created_at']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
            if not validated_data.get('participant_name'):
                validated_data['participant_name'] = request.user.get_full_name() or request.user.username
            if not validated_data.get('participant_email'):
                validated_data['participant_email'] = request.user.email
            if not validated_data.get('participant_contact'):
                validated_data['participant_contact'] = request.user.phone or ''
        return super().create(validated_data)


class ContestSubmissionListSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.username')
    contest_title = serializers.ReadOnlyField(source='contest.title')

    class Meta:
        model = ContestSubmission
        fields = ['id', 'contest_title', 'user_name',
                  'participant_name', 'participant_email', 'participant_contact',
                  'content_type', 'title', 'content', 'status', 'created_at']


class ContestSerializer(serializers.ModelSerializer):
    is_expired = serializers.ReadOnlyField()
    is_open = serializers.ReadOnlyField()
    banner_url = serializers.SerializerMethodField()

    class Meta:
        model = Contest
        fields = [
            'id', 'title', 'description', 'start_date', 'deadline',
            'prize_details', 'rules', 'banner_image', 'banner_url',
            'is_active', 'is_expired', 'is_open', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_banner_url(self, obj):
        return _file_url(obj.banner_image)


class ContestListSerializer(serializers.ModelSerializer):
    is_expired = serializers.ReadOnlyField()
    is_open = serializers.ReadOnlyField()
    banner_url = serializers.SerializerMethodField()

    class Meta:
        model = Contest
        fields = [
            'id', 'title', 'description', 'start_date', 'deadline',
            'prize_details', 'rules', 'banner_url',
            'is_active', 'is_expired', 'is_open'
        ]

    def get_banner_url(self, obj):
        return _file_url(obj.banner_image)


class ContestCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contest
        fields = [
            'title', 'description', 'start_date', 'deadline',
            'prize_details', 'rules', 'banner_image', 'is_active'
        ]

    def validate_deadline(self, value):
        from django.utils import timezone
        if value < timezone.now():
            raise serializers.ValidationError("Deadline cannot be in the past")
        return value
