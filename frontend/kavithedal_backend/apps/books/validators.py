"""
File validators for book covers, author photos, and PDF uploads.
"""
import os
from django.core.exceptions import ValidationError


def validate_image_type(file):
    """Accept JPEG, PNG, and WebP images only."""
    valid_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in valid_extensions:
        raise ValidationError(
            f'Unsupported image format "{ext}". Allowed formats: JPEG, PNG, WebP.'
        )


def validate_pdf_type(file):
    """Accept PDF files only."""
    ext = os.path.splitext(file.name)[1].lower()
    if ext != '.pdf':
        raise ValidationError(
            f'Only PDF files are accepted. Received "{ext}".'
        )


def validate_image_size(file):
    """Reject images larger than 5 MB."""
    limit_mb = 5
    if hasattr(file, 'size') and file.size > limit_mb * 1024 * 1024:
        raise ValidationError(
            f'Image file is too large ({file.size // (1024 * 1024)} MB). '
            f'Maximum allowed size is {limit_mb} MB.'
        )


def validate_pdf_size(file):
    """Reject PDF files larger than 50 MB."""
    limit_mb = 50
    if hasattr(file, 'size') and file.size > limit_mb * 1024 * 1024:
        raise ValidationError(
            f'PDF file is too large ({file.size // (1024 * 1024)} MB). '
            f'Maximum allowed size is {limit_mb} MB.'
        )
