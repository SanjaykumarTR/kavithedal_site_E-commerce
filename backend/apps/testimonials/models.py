"""
Testimonial Model for Kavithedal Publications.
"""
import uuid
from django.db import models


def _video_storage():
    """Return VideoMediaCloudinaryStorage when available, else default storage.

    Using a callable means Django stores only the function reference in
    migrations — safe across environments where cloudinary_storage may not
    be installed (e.g. local dev without Cloudinary credentials).
    Video files MUST be uploaded as resource_type='video' on Cloudinary;
    the default MediaCloudinaryStorage uses resource_type='image' which
    causes Cloudinary to reject mp4/mov/webm uploads entirely.
    """
    try:
        from cloudinary_storage.storage import VideoMediaCloudinaryStorage
        return VideoMediaCloudinaryStorage()
    except ImportError:
        from django.core.files.storage import FileSystemStorage
        return FileSystemStorage()


class Testimonial(models.Model):
    """
    Testimonial model for managing reader and author testimonials.
    """
    ROLE_CHOICES = [
        ('reader', 'Reader'),
        ('author', 'Author'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    VIDEO_TYPE_CHOICES = [
        ('none', 'None'),
        ('youtube', 'YouTube'),
        ('vimeo', 'Vimeo'),
        ('mp4_url', 'MP4 URL'),
        ('mp4_file', 'MP4 File Upload'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True, help_text="Email for notification purposes")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='reader')
    message = models.TextField()
    rating = models.PositiveIntegerField(default=5)  # 1-5
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    has_video = models.BooleanField(default=False)
    video_type = models.CharField(max_length=20, choices=VIDEO_TYPE_CHOICES, default='none', blank=True)
    video_url = models.URLField(max_length=500, blank=True, help_text="YouTube/Vimeo URL or MP4 video URL")
    video_file = models.FileField(upload_to='testimonials/videos/', storage=_video_storage, blank=True, null=True, help_text="Upload MP4/MOV video file")
    photo = models.ImageField(upload_to='testimonials/photos/', blank=True, null=True, help_text="Profile photo of the reviewer")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'testimonials'
        verbose_name = 'Testimonial'
        verbose_name_plural = 'Testimonials'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.rating}⭐"
    
    @property
    def is_approved(self):
        return self.status == 'approved'
