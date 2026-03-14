"""
Revert Book.cover_image back to default storage (no explicit storage argument).
This undoes migration 0009 which added ImageCloudinaryStorage and caused
admin 500 errors on the book change page.
"""
import apps.books.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('books', '0009_alter_book_cover_image_storage'),
    ]

    operations = [
        migrations.AlterField(
            model_name='book',
            name='cover_image',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='books/covers/',
                validators=[
                    apps.books.validators.validate_image_type,
                    apps.books.validators.validate_image_size,
                ],
            ),
        ),
    ]
