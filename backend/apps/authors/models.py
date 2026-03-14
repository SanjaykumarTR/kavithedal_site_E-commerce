"""
Author Model for Kavithedal Publications.
"""
import uuid
from django.db import models
from apps.books.validators import validate_image_type, validate_image_size


class Author(models.Model):
    """
    Author model for managing book authors.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    biography = models.TextField(blank=True)
    photo = models.ImageField(
        upload_to='authors/',
        blank=True,
        null=True,
        validators=[validate_image_type, validate_image_size],
    )
    email = models.EmailField(blank=True)
    mobile_number = models.CharField(max_length=20, blank=True)
    social_links = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'authors'
        verbose_name = 'Author'
        verbose_name_plural = 'Authors'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def books_count(self):
        return self.books.count()
