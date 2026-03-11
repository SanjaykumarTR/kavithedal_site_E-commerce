"""
Serializers for Contests App.
"""
from rest_framework import serializers
from .models import Contest, ContestSubmission


class ContestSubmissionSerializer(serializers.ModelSerializer):
    """
    Serializer for ContestSubmission model.
    """
    user_name = serializers.ReadOnlyField(source='user.username')
    contest_title = serializers.ReadOnlyField(source='contest.title')
    
    class Meta:
        model = ContestSubmission
        fields = ['id', 'contest', 'contest_title', 'user', 'user_name', 
                  'participant_name', 'participant_email', 'participant_contact',
                  'content_type', 'title', 'content', 'status', 'created_at']
        read_only_fields = ['id', 'user', 'status', 'created_at']
    
    def create(self, validated_data):
        # If user is authenticated, link the submission to the user
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
            # If user is logged in, auto-fill participant details from user
            if not validated_data.get('participant_name'):
                validated_data['participant_name'] = request.user.get_full_name() or request.user.username
            if not validated_data.get('participant_email'):
                validated_data['participant_email'] = request.user.email
            if not validated_data.get('participant_contact'):
                validated_data['participant_contact'] = request.user.phone or ''
        return super().create(validated_data)


class ContestSubmissionListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for ContestSubmission list view.
    """
    user_name = serializers.ReadOnlyField(source='user.username')
    contest_title = serializers.ReadOnlyField(source='contest.title')
    
    class Meta:
        model = ContestSubmission
        fields = ['id', 'contest_title', 'user_name', 
                  'participant_name', 'participant_email', 'participant_contact',
                  'content_type', 'title', 'content', 'status', 'created_at']


class ContestSerializer(serializers.ModelSerializer):
    """
    Serializer for Contest model.
    """
    is_expired = serializers.ReadOnlyField()
    is_open = serializers.ReadOnlyField()
    
    class Meta:
        model = Contest
        fields = [
            'id', 'title', 'description', 'deadline', 'prize_details',
            'rules', 'banner_image', 'is_active', 'is_expired', 'is_open',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ContestListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for Contest list view.
    """
    is_expired = serializers.ReadOnlyField()
    is_open = serializers.ReadOnlyField()
    
    class Meta:
        model = Contest
        fields = [
            'id', 'title', 'description', 'deadline', 'prize_details',
            'rules', 'banner_image', 'is_active', 'is_expired', 'is_open'
        ]


class ContestCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating/updating Contest.
    """
    class Meta:
        model = Contest
        fields = [
            'title', 'description', 'deadline', 'prize_details',
            'rules', 'banner_image', 'is_active'
        ]
    
    def validate_deadline(self, value):
        from django.utils import timezone
        if value < timezone.now():
            raise serializers.ValidationError("Deadline cannot be in the past")
        return value
