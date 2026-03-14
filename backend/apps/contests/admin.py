"""
Admin configuration for Contests app.
"""
from django import forms
from django.contrib import admin
from django.utils.html import mark_safe
from .models import Contest, ContestSubmission


class ContestAdminForm(forms.ModelForm):
    """Prevent storage.delete() crash when clearing banner_image in Django 5.x admin."""
    class Meta:
        model = Contest
        fields = '__all__'

    def _post_clean(self):
        if self.cleaned_data.get('banner_image') is False:
            self.cleaned_data['banner_image'] = ''
        super()._post_clean()


@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    form = ContestAdminForm

    list_display = ['title', 'is_active', 'start_date', 'deadline', 'banner_preview', 'created_at']
    list_filter = ['is_active']
    search_fields = ['title', 'description', 'prize_details']
    ordering = ['-created_at']
    readonly_fields = ['banner_preview', 'created_at', 'updated_at']

    fieldsets = (
        ('Contest Info', {
            'fields': ('title', 'description', 'is_active'),
        }),
        ('Banner Image', {
            'fields': ('banner_image', 'banner_preview'),
        }),
        ('Dates', {
            'fields': ('start_date', 'deadline'),
        }),
        ('Details', {
            'fields': ('prize_details', 'rules'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def banner_preview(self, obj):
        if obj.banner_image:
            try:
                url = obj.banner_image.url
            except Exception:
                return '(no preview)'
            return mark_safe(
                f'<img src="{url}" style="max-height:80px;max-width:160px;'
                f'object-fit:cover;border-radius:6px;" />'
            )
        return '(no image)'
    banner_preview.short_description = 'Banner Preview'


@admin.register(ContestSubmission)
class ContestSubmissionAdmin(admin.ModelAdmin):
    list_display = ['title', 'contest', 'participant_name', 'participant_email', 'content_type', 'status', 'created_at']
    list_filter = ['status', 'content_type', 'contest']
    search_fields = ['title', 'participant_name', 'participant_email']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
