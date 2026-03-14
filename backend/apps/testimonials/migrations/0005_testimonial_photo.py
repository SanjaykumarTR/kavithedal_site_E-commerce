from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('testimonials', '0004_testimonial_email'),
    ]

    operations = [
        migrations.AddField(
            model_name='testimonial',
            name='photo',
            field=models.ImageField(blank=True, null=True, upload_to='testimonials/photos/', help_text='Profile photo of the reviewer'),
        ),
    ]
