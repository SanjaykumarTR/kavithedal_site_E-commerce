"""
Admin configuration for Testimonials app.
"""
from django import forms
from django.contrib import admin
from django.utils.html import mark_safe
from .models import Testimonial


class TestimonialAdminForm(forms.ModelForm):
    """Prevent storage.delete() crash when clearing photo in Django 5.x admin."""
    class Meta:
        model = Testimonial
        fields = '__all__'

    def _post_clean(self):
        for field_name in ('photo', 'video_file'):
            if self.cleaned_data.get(field_name) is False:
                self.cleaned_data[field_name] = ''
        super()._post_clean()


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    form = TestimonialAdminForm

    list_display = ['name', 'role', 'rating_display', 'status', 'photo_preview', 'created_at']
    list_filter = ['status', 'role', 'rating']
    search_fields = ['name', 'email', 'message']
    ordering = ['-created_at']
    readonly_fields = ['photo_preview', 'created_at', 'updated_at']

    fieldsets = (
        ('Reviewer Info', {
            'fields': ('name', 'email', 'role', 'photo', 'photo_preview'),
        }),
        ('Testimonial', {
            'fields': ('message', 'rating', 'status'),
        }),
        ('Video (Optional)', {
            'fields': ('has_video', 'video_type', 'video_url', 'video_file'),
            'classes': ('collapse',),
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
                f'<img src="{url}" style="max-height:60px;max-width:60px;'
                f'object-fit:cover;border-radius:50%;border:2px solid #B71C1C;" />'
            )
        return '(no photo)'
    photo_preview.short_description = 'Photo'

    def rating_display(self, obj):
        return '⭐' * obj.rating
    rating_display.short_description = 'Rating'
