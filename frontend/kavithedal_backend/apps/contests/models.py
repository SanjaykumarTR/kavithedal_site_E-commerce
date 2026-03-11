"""
Models for Contests App.
"""
from django.db import models
from django.conf import settings


class Contest(models.Model):
    """
    Contest model for managing writing contests.
    """
    title = models.CharField(max_length=200)
    description = models.TextField()
    deadline = models.DateTimeField()
    prize_details = models.TextField(blank=True)
    rules = models.TextField()
    banner_image = models.ImageField(upload_to='contests/banners/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contests'
        verbose_name = 'Contest'
        verbose_name_plural = 'Contests'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def is_expired(self):
        from django.utils import timezone
        return self.deadline < timezone.now()

    @property
    def is_open(self):
        from django.utils import timezone
        return self.is_active and self.deadline >= timezone.now()


class ContestSubmission(models.Model):
    """
    Model for contest submissions (essays, poems, stories).
    """
    CONTENT_TYPE_CHOICES = [
        ('essay', 'Essay'),
        ('poem', 'Poem'),
        ('story', 'Story'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='submissions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='contest_submissions', null=True, blank=True)
    # Participant details (for users who are not logged in or want to provide their info)
    participant_name = models.CharField(max_length=200, blank=True, default='')
    participant_email = models.EmailField(blank=True, default='')
    participant_contact = models.CharField(max_length=20, blank=True, default='')
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    content = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contest_submissions'
        verbose_name = 'Contest Submission'
        verbose_name_plural = 'Contest Submissions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.contest.title} - {self.content_type}"
