"""
Switch Testimonial.video_file to VideoMediaCloudinaryStorage.

Previously, video files were uploaded using MediaCloudinaryStorage
(resource_type='image'). Cloudinary rejects video files (mp4/mov/webm)
uploaded as resource_type='image', so videos were never stored successfully.

VideoMediaCloudinaryStorage uses resource_type='video', the correct type
for video files so Cloudinary can process and serve them.

After deploying: re-upload any existing testimonial videos via Django Admin
so they are stored with the correct Cloudinary resource type.
"""
import apps.testimonials.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('testimonials', '0005_testimonial_photo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='testimonial',
            name='video_file',
            field=models.FileField(
                blank=True,
                help_text='Upload MP4/MOV video file',
                null=True,
                storage=apps.testimonials.models._video_storage,
                upload_to='testimonials/videos/',
            ),
        ),
    ]
