"""
Admin configuration for Authors app — with photo preview and Cloudinary support.
"""
from django.contrib import admin
from django.utils.html import mark_safe
from .models import Author


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'mobile_number', 'books_count_display', 'photo_preview', 'created_at']
    search_fields = ['name', 'email', 'mobile_number']
    ordering = ['name']
    readonly_fields = ['photo_preview', 'created_at', 'updated_at']

    fieldsets = (
        ('Personal Info', {
            'fields': ('name', 'biography'),
        }),
        ('Photo', {
            'fields': ('photo', 'photo_preview'),
        }),
        ('Contact', {
            'fields': ('email', 'mobile_number', 'social_links'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def photo_preview(self, obj):
        if obj.photo:
            try:
                url = obj.photo.url
            except Exception:
                return '(no preview)'
            return mark_safe(
                f'<img src="{url}" style="max-height:100px;max-width:100px;'
                f'object-fit:cover;border-radius:50%;" />'
            )
        return '(no photo)'
    photo_preview.short_description = 'Preview'

    def books_count_display(self, obj):
        return obj.books.count()
    books_count_display.short_description = 'Books'
