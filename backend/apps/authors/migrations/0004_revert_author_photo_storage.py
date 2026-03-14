"""
Revert Author.photo back to default storage (no explicit storage argument).
This undoes migration 0003 which added ImageCloudinaryStorage.
"""
import apps.books.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authors', '0003_alter_author_photo_storage'),
    ]

    operations = [
        migrations.AlterField(
            model_name='author',
            name='photo',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='authors/',
                validators=[
                    apps.books.validators.validate_image_type,
                    apps.books.validators.validate_image_size,
                ],
            ),
        ),
    ]
