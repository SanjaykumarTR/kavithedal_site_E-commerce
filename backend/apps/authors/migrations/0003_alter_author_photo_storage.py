"""
Switch Author.photo to ImageCloudinaryStorage (RESOURCE_TYPE='image').
"""
import apps.books.cloudinary_storage
import apps.books.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authors', '0002_author_mobile_number'),
    ]

    operations = [
        migrations.AlterField(
            model_name='author',
            name='photo',
            field=models.ImageField(
                blank=True,
                null=True,
                storage=apps.books.cloudinary_storage.ImageCloudinaryStorage(),
                upload_to='authors/',
                validators=[
                    apps.books.validators.validate_image_type,
                    apps.books.validators.validate_image_size,
                ],
            ),
        ),
    ]
