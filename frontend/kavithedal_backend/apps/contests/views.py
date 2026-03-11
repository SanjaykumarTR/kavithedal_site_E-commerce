"""
Views for Contests App.
"""
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters import rest_framework as filters

from .models import Contest, ContestSubmission
from .serializers import ContestSerializer, ContestListSerializer, ContestCreateUpdateSerializer, ContestSubmissionSerializer, ContestSubmissionListSerializer
from apps.accounts.utils import is_authorized_admin


class IsAuthorizedAdmin(permissions.BasePermission):
    """
    Custom permission to only allow the authorized admin email.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return is_authorized_admin(request.user)


class ContestFilter(filters.FilterSet):
    """Filter for Contest model."""
    is_active = filters.BooleanFilter(field_name='is_active')
    
    class Meta:
        model = Contest
        fields = ['is_active']


class ContestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Contest CRUD operations.
    
    Public users can view active contests.
    Admin users can create, update, and delete contests.
    """
    queryset = Contest.objects.all()
    filterset_class = ContestFilter
    search_fields = ['title', 'description']
    ordering_fields = ['deadline', 'created_at']
    ordering = ['-created_at']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'active', 'upcoming', 'closed']:
            return [permissions.AllowAny()]
        if self.action in ['submit']:
            return [permissions.AllowAny()]  # Allow guest submissions
        # Use custom admin check for create/update/delete
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthorizedAdmin()]  # Custom permission
        return [permissions.IsAuthenticated()]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ContestCreateUpdateSerializer
        if self.action == 'list':
            return ContestListSerializer
        return ContestSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action in ['list', 'retrieve']:
            # Public users only see active contests
            queryset = queryset.filter(is_active=True)
        return queryset
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        GET /api/contests/active/
        Get all active contests.
        """
        from django.utils import timezone
        contests = self.queryset.filter(
            is_active=True,
            deadline__gte=timezone.now()
        )
        serializer = ContestListSerializer(contests, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """
        GET /api/contests/upcoming/
        Get upcoming contests.
        """
        from django.utils import timezone
        contests = self.queryset.filter(
            is_active=True,
            deadline__gt=timezone.now()
        )
        serializer = ContestListSerializer(contests, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def closed(self, request):
        """
        GET /api/contests/closed/
        Get closed contests.
        """
        from django.utils import timezone
        contests = self.queryset.filter(deadline__lt=timezone.now())
        serializer = ContestListSerializer(contests, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """
        POST /api/contests/{id}/submit/
        Submit an entry to this contest.
        """
        contest = self.get_object()
        
        # Get submission data
        content_type = request.data.get('content_type')
        title = request.data.get('title')
        content = request.data.get('content')
        
        if not all([content_type, title, content]):
            return Response(
                {'detail': 'content_type, title, and content are required.'},
                status=400
            )
        
        # Get participant details
        participant_name = request.data.get('participant_name', '')
        participant_email = request.data.get('participant_email', '')
        participant_contact = request.data.get('participant_contact', '')
        
        # Check if user is authenticated
        user = None
        if request.user.is_authenticated:
            user = request.user
            # Auto-fill from user if not provided
            if not participant_name:
                participant_name = request.user.get_full_name() or request.user.username
            if not participant_email:
                participant_email = request.user.email
            if not participant_contact:
                participant_contact = request.user.phone or ''
            
            # Check if user already submitted
            existing = ContestSubmission.objects.filter(
                contest=contest,
                user=user
            ).first()
            
            if existing:
                return Response(
                    {'detail': 'You have already submitted to this contest.'},
                    status=400
                )
        else:
            # For guest users, participant details are required
            if not all([participant_name, participant_email, participant_contact]):
                return Response(
                    {'detail': 'participant_name, participant_email, and participant_contact are required for guest submissions.'},
                    status=400
                )
        
        # Create submission
        submission = ContestSubmission.objects.create(
            contest=contest,
            user=request.user,
            content_type=content_type,
            title=title,
            content=content,
            participant_name=participant_name,
            participant_email=participant_email,
            participant_contact=participant_contact
        )
        
        serializer = ContestSubmissionSerializer(submission)
        return Response(serializer.data, status=201)


class ContestSubmissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ContestSubmission CRUD operations.
    
    Authenticated users can create submissions.
    Admin users can view all submissions and update status.
    """
    queryset = ContestSubmission.objects.all()
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            # Users can see their own submissions, admins can see all
            return [permissions.IsAuthenticated()]
        if self.action in ['create']:
            return [permissions.AllowAny()]  # Allow guest submissions
        if self.action in ['partial_update', 'update']:
            # Only the authorized admin can update submission status
            return [IsAuthorizedAdmin()]
        return [IsAuthorizedAdmin()]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ContestSubmissionListSerializer
        return ContestSubmissionSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Filter by participant email if provided (for non-logged-in users)
        participant_email = self.request.query_params.get('participant_email')
        if participant_email:
            queryset = queryset.filter(participant_email=participant_email)
            return queryset
            
        # Check if user is the authorized admin
        if is_authorized_admin(user):
            # Admin sees all submissions including guest submissions (where user is NULL)
            return queryset.all()
        # Regular users see only their own submissions
        return queryset.filter(user=user)
    
    def perform_create(self, serializer):
        # Auto-fill participant details from user if authenticated
        user = self.request.user
        if user.is_authenticated:
            # Check if participant details are being provided
            if not serializer.validated_data.get('participant_name'):
                serializer.validated_data['participant_name'] = user.get_full_name() or user.username
            if not serializer.validated_data.get('participant_email'):
                serializer.validated_data['participant_email'] = user.email
            if not serializer.validated_data.get('participant_contact'):
                serializer.validated_data['participant_contact'] = user.phone or ''
            serializer.save(user=user)
        else:
            serializer.save()
    
    def create(self, request, *args, **kwargs):
        # Handle contest ID - now it's an integer
        contest_id = request.data.get('contest')
        if contest_id:
            try:
                # Ensure contest_id is an integer - handle both QueryDict and dict
                if hasattr(request.data, '_mutable'):
                    request.data._mutable = True
                    request.data['contest'] = int(contest_id)
                else:
                    # Create a new dict with the converted contest ID
                    new_data = dict(request.data)
                    new_data['contest'] = int(contest_id)
                    request._data = new_data
            except (ValueError, TypeError):
                pass
        return super().create(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        # Only allow status update for the authorized admin
        if not is_authorized_admin(request.user):
            return Response(
                {'detail': 'You do not have permission to update submission status.'},
                status=403
            )
        return super().partial_update(request, *args, **kwargs)
    
    @action(detail=False, methods=['get'])
    def my_submissions(self, request):
        """
        GET /api/contest-submissions/my/
        Get current user's submissions.
        """
        submissions = self.queryset.filter(user=request.user)
        serializer = ContestSubmissionListSerializer(submissions, many=True)
        return Response(serializer.data)
