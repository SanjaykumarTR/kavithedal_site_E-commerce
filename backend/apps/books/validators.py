"""
File validators for book covers, author photos, and PDF uploads.
"""
import os
from django.core.exceptions import ValidationError


def _is_new_upload(file):
    """
    Return True only when `file` is a freshly uploaded file object
    (InMemoryUploadedFile / TemporaryUploadedFile), not a FieldFile that
    already lives in storage.  We only run extension/size checks on new
    uploads — existing Cloudinary FieldFiles have public_ids as names
    (e.g. "media/books/pdfs/mybook") and no reliable extension.
    """
    from django.core.files.uploadedfile import UploadedFile
    return isinstance(file, UploadedFile)


def validate_image_type(file):
    """Accept JPEG, PNG, and WebP images only."""
    if not file or not _is_new_upload(file):
        return
    valid_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in valid_extensions:
        raise ValidationError(
            f'Unsupported image format "{ext}". Allowed formats: JPEG, PNG, WebP.'
        )


def validate_pdf_type(file):
    """Accept PDF files only."""
    if not file or not _is_new_upload(file):
        return
    ext = os.path.splitext(file.name)[1].lower()
    if ext != '.pdf':
        raise ValidationError(
            f'Only PDF files are accepted. Received "{ext}".'
        )


def validate_image_size(file):
    """Reject images larger than 5 MB."""
    limit_mb = 5
    # Use getattr so we handle FieldFile objects whose .size may return None
    # when django-cloudinary-storage does not implement storage.size().
    size = getattr(file, 'size', None)
    if size is not None and size > limit_mb * 1024 * 1024:
        raise ValidationError(
            f'Image file is too large ({size // (1024 * 1024)} MB). '
            f'Maximum allowed size is {limit_mb} MB.'
        )


def validate_pdf_size(file):
    """Reject PDF files larger than 50 MB."""
    limit_mb = 50
    size = getattr(file, 'size', None)
    if size is not None and size > limit_mb * 1024 * 1024:
        raise ValidationError(
            f'PDF file is too large ({size // (1024 * 1024)} MB). '
            f'Maximum allowed size is {limit_mb} MB.'
        )
