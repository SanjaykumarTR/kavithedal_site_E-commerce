"""
Admin configuration for Books app.
"""
from django.contrib import admin
from .models import Book, Category


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'price', 'ebook_price', 'physical_price', 'book_type', 'is_active', 'is_featured']
    list_filter = ['book_type', 'is_active', 'is_featured', 'category']
    search_fields = ['title', 'author__name']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'author', 'description')
        }),
        ('Pricing', {
            'fields': ('price', 'ebook_price', 'physical_price', 'book_type')
        }),
        ('Files', {
            'fields': ('cover_image', 'pdf_file')
        }),
        ('Details', {
            'fields': ('category', 'published_date', 'isbn', 'pages', 'language')
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured')
        }),
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']
