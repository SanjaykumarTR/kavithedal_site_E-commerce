"""
Admin configuration for Books app — with image previews and Cloudinary support.
"""
import logging
from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.utils.html import mark_safe
from .models import Book, Category, BookSubmission, ContactMessage

logger = logging.getLogger('apps')


def _cloudinary_active():
    """Return True when Cloudinary is the active file storage backend."""
    # Django 5.x uses STORAGES dict; DEFAULT_FILE_STORAGE was removed in 5.0
    storages = getattr(settings, 'STORAGES', {})
    default_backend = storages.get('default', {}).get('BACKEND', '')
    return default_backend.startswith('cloudinary')


class BookAdminForm(forms.ModelForm):
    """
    Custom ModelForm that prevents Cloudinary storage.delete() from being called
    when an admin user clears a file field.

    Django 5.x calls FileField.save_form_data() during form._post_clean()
    (which runs inside form.is_valid()).  When the clear checkbox is ticked,
    cleaned_data[field] == False, and save_form_data() calls FieldFile.delete()
    → storage.delete() → Cloudinary API → can raise exceptions → 500 error.

    By replacing False with '' here (before super()._post_clean()), we allow
    save_form_data() to set the field to '' (clearing the DB value) WITHOUT
    calling storage.delete(), which avoids the Cloudinary error.
    """
    class Meta:
        model = Book
        fields = '__all__'

    def _post_clean(self):
        for field_name in ('cover_image', 'pdf_file'):
            if self.cleaned_data.get(field_name) is False:
                self.cleaned_data[field_name] = ''
        try:
            super()._post_clean()
        except ValidationError:
            raise
        except Exception as e:
            # Cloudinary upload or other storage errors during form processing.
            # Convert to ValidationError so Django shows a user-friendly form
            # error instead of crashing with a 500.
            logger.error('BookAdminForm._post_clean storage error: %s', e, exc_info=True)
            raise ValidationError(
                f'File upload failed: {e}. '
                'Check that CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and '
                'CLOUDINARY_API_SECRET are set correctly in Render environment variables.'
            )


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    form = BookAdminForm

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
            not form.cleaned_data.get('cover_image')
        )
        pdf_clearing = (
            'pdf_file' in form.changed_data and
            not form.cleaned_data.get('pdf_file')
        )

        try:
            super().save_model(request, obj, form, change)

            if image_clearing:
                messages.success(request, '✅ Cover image cleared successfully.')
            if pdf_clearing:
                messages.success(request, '✅ PDF file cleared successfully.')
            if image_uploading and obj.cover_image:
                try:
                    url = obj.cover_image.url
                    messages.success(request, mark_safe(
                        f'✅ Cover image uploaded successfully. '
                        f'<a href="{url}" target="_blank">View on Cloudinary ↗</a>'
                        if _cloudinary_active() else '✅ Cover image saved.'
                    ))
                except Exception:
                    messages.success(request, '✅ Cover image saved.')
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
                messages.error(
                    request,
                    f'❌ Could not save book at all: {inner_exc}. '
                    'Check Render logs for details.'
                )
                return  # do not re-raise — avoids 500, returns to admin list
            messages.warning(
                request,
                f'❌ Book saved WITHOUT image/PDF — file upload failed: {exc}. '
                'Check that CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, '
                'and CLOUDINARY_API_SECRET are correct in Render environment variables.'
            )

    def cover_preview(self, obj):
        if obj.cover_image:
            try:
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
