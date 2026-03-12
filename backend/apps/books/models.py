"""
Book Model for Kavithedal Publications.
"""
import uuid
from django.db import models
from apps.authors.models import Author
from apps.books.validators import (
    validate_image_type, validate_image_size,
    validate_pdf_type, validate_pdf_size,
)


class Category(models.Model):
    """
    Category model for book classification.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'categories'
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Book(models.Model):
    """
    Book model for managing books in the publishing platform.
    """
    BOOK_TYPE_CHOICES = [
        ('ebook', 'eBook Only'),
        ('physical', 'Physical Book Only'),
        ('both', 'Both eBook and Physical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=300)
    author = models.ForeignKey(
        Author,
        on_delete=models.CASCADE,
        related_name='books'
    )
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text='Discount percentage (0-100)')
    ebook_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    physical_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    book_type = models.CharField(max_length=20, choices=BOOK_TYPE_CHOICES, default='both')
    pdf_file = models.FileField(
        upload_to='books/pdfs/',
        blank=True,
        null=True,
        validators=[validate_pdf_type, validate_pdf_size],
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='books'
    )
    cover_image = models.ImageField(
        upload_to='books/covers/',
        blank=True,
        null=True,
        validators=[validate_image_type, validate_image_size],
    )
    stock = models.PositiveIntegerField(default=0, help_text='Number of physical copies in stock')
    published_date = models.DateField(blank=True, null=True)
    isbn = models.CharField(max_length=20, blank=True)
    pages = models.PositiveIntegerField(default=0)
    language = models.CharField(max_length=50, default='English')
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'books'
        verbose_name = 'Book'
        verbose_name_plural = 'Books'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    @property
    def author_name(self):
        return self.author.name
    
    @property
    def ebook_final_price(self):
        """Calculate final eBook price after discount"""
        if self.ebook_price and self.discount_percentage:
            discount_amount = self.ebook_price * (self.discount_percentage / 100)
            return self.ebook_price - discount_amount
        return self.ebook_price
    
    @property
    def physical_final_price(self):
        """Calculate final physical book price after discount"""
        if self.physical_price and self.discount_percentage:
            discount_amount = self.physical_price * (self.discount_percentage / 100)
            return self.physical_price - discount_amount
        return self.physical_price


class BookSubmission(models.Model):
    """
    Model for book submissions from writers who want to publish.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    email = models.EmailField()
    contact = models.CharField(max_length=20)
    book_title = models.CharField(max_length=300)
    description = models.TextField()
    file = models.FileField(upload_to='book_submissions/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'book_submissions'
        verbose_name = 'Book Submission'
        verbose_name_plural = 'Book Submissions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.book_title}"


class ContactMessage(models.Model):
    """Model for contact form messages that get sent to admin email."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        db_table = 'contact_messages'
        verbose_name = 'Contact Message'
        verbose_name_plural = 'Contact Messages'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.email}"
