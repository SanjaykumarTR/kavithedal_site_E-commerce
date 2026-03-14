"""
Admin configuration for Books app — with image previews and Cloudinary support.
"""
import logging
from django.conf import settings
from django.contrib import admin, messages
from django.utils.html import mark_safe
from .models import Book, Category, BookSubmission, ContactMessage

logger = logging.getLogger('apps')


def _cloudinary_active():
    """Return True when Cloudinary is the active file storage backend."""
    return getattr(settings, 'DEFAULT_FILE_STORAGE', '').startswith('cloudinary')


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'author', 'book_type',
        'ebook_price', 'physical_price', 'discount_percentage',
        'stock', 'is_active', 'is_featured', 'cover_preview',
    ]
    list_filter = ['book_type', 'is_active', 'is_featured', 'category', 'language']
    search_fields = ['title', 'author__name', 'isbn']
    ordering = ['-created_at']
    readonly_fields = ['cover_preview', 'created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'author', 'description', 'category'),
        }),
        ('Pricing & Type', {
            'fields': (
                'book_type',
                'price', 'discount_percentage',
                'ebook_price', 'physical_price',
            ),
        }),
        ('Inventory', {
            'fields': ('stock',),
        }),
        ('Cover Image', {
            'fields': ('cover_image', 'cover_preview'),
        }),
        ('PDF File', {
            'fields': ('pdf_file',),
        }),
        ('Publication Details', {
            'fields': ('published_date', 'isbn', 'pages', 'language'),
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def changelist_view(self, request, extra_context=None):
        """Show a Cloudinary status banner at the top of the book list."""
        if _cloudinary_active():
            cloud = getattr(settings, 'CLOUDINARY_STORAGE', {}).get('CLOUD_NAME', '?')
            messages.info(
                request,
                f'✅ Cloudinary is active (cloud: {cloud}). '
                'Uploaded images and PDFs are stored permanently on Cloudinary CDN.'
            )
        else:
            messages.warning(
                request,
                '⚠️ Cloudinary is NOT configured. '
                'Uploaded images will be lost on every Render redeploy. '
                'Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET '
                'in your Render environment variables.'
            )
        return super().changelist_view(request, extra_context=extra_context)

    def save_form(self, request, form, change):
        """Intercept file-clear actions BEFORE form.save() calls storage.delete().

        Django signals a file clear by setting cleaned_data[field] = False.
        FileField.save_form_data() then calls storage.delete() which raises
        exceptions with Cloudinary. Replace False with '' to skip deletion
        while still clearing the field value in the database.
        """
        file_fields = ('cover_image', 'pdf_file')
        for field_name in file_fields:
            if form.cleaned_data.get(field_name) is False:
                form.cleaned_data[field_name] = ''
        return super().save_form(request, form, change)

    def save_model(self, request, obj, form, change):
        """Save the book, gracefully handling file-storage errors on upload."""
        image_uploading = (
            'cover_image' in form.changed_data and
            bool(form.cleaned_data.get('cover_image'))
        )
        pdf_uploading = (
            'pdf_file' in form.changed_data and
            bool(form.cleaned_data.get('pdf_file'))
        )
        image_clearing = (
            'cover_image' in form.changed_data and
            form.cleaned_data.get('cover_image') == ''
        )
        pdf_clearing = (
            'pdf_file' in form.changed_data and
            form.cleaned_data.get('pdf_file') == ''
        )

        try:
            super().save_model(request, obj, form, change)

            if image_clearing:
                messages.success(request, '✅ Cover image cleared successfully.')
            if pdf_clearing:
                messages.success(request, '✅ PDF file cleared successfully.')
            if image_uploading and obj.cover_image:
                try:
                    from apps.books.serializers import _cloudinary_url
                    stored = obj.cover_image.name if obj.cover_image else None
                    url = _cloudinary_url(stored, 'image') if stored else None
                    if url:
                        messages.success(request, mark_safe(
                            f'✅ Cover image uploaded successfully. '
                            f'<a href="{url}" target="_blank">View on Cloudinary ↗</a>'
                            if _cloudinary_active() else '✅ Cover image saved.'
                        ))
                except Exception:
                    pass
            if pdf_uploading and obj.pdf_file:
                messages.success(request, '✅ PDF uploaded successfully.')

        except Exception as exc:
            logger.error(
                'BookAdmin save_model failed for "%s": %s', obj.title, exc, exc_info=True
            )
            if image_uploading:
                obj.cover_image = None
            if pdf_uploading:
                obj.pdf_file = None
            try:
                obj.save()
            except Exception as inner_exc:
                logger.error(
                    'BookAdmin fallback save also failed for "%s": %s',
                    obj.title, inner_exc, exc_info=True,
                )
                messages.error(request, f'Could not save book: {inner_exc}')
                raise inner_exc
            messages.warning(
                request,
                f'❌ Book saved WITHOUT image/PDF — file upload failed: {exc}. '
                'Check that CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, '
                'and CLOUDINARY_API_SECRET are correct in Render environment variables.'
            )

    def cover_preview(self, obj):
        if obj.cover_image:
            try:
                from apps.books.serializers import _cloudinary_url
                stored = obj.cover_image.name if obj.cover_image else None
                url = _cloudinary_url(stored, 'image') if stored else None
                if not url:
                    url = obj.cover_image.url
            except Exception:
                return '(no preview)'
            return mark_safe(
                f'<img src="{url}" style="max-height:100px;max-width:100px;'
                f'object-fit:cover;border-radius:4px;" />'
            )
        return '(no image)'
    cover_preview.short_description = 'Preview'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name']


@admin.register(BookSubmission)
class BookSubmissionAdmin(admin.ModelAdmin):
    list_display = ['book_title', 'name', 'email', 'contact', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['name', 'email', 'book_title']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'is_read', 'created_at']
    list_filter = ['is_read']
    search_fields = ['name', 'email']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
