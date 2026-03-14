"""
Switch Book.cover_image to ImageCloudinaryStorage (RESOURCE_TYPE='image').

The default MediaCloudinaryStorage uses resource_type='raw', which means
uploaded images get stored as Cloudinary raw resources. Cloudinary may serve
these with incorrect or missing Content-Type headers, causing <img> tags to
fail. ImageCloudinaryStorage uses resource_type='image', guaranteeing proper
CDN delivery and browser rendering.

After this migration deploys, re-upload any existing book covers and author
photos from the Django admin so they get stored as the correct Cloudinary type.
"""
import apps.books.cloudinary_storage
import apps.books.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('books', '0008_add_stock_field_and_validators'),
    ]

    operations = [
        migrations.AlterField(
            model_name='book',
            name='cover_image',
            field=models.ImageField(
                blank=True,
                null=True,
                storage=apps.books.cloudinary_storage.ImageCloudinaryStorage(),
                upload_to='books/covers/',
                validators=[
                    apps.books.validators.validate_image_type,
                    apps.books.validators.validate_image_size,
                ],
            ),
        ),
    ]
