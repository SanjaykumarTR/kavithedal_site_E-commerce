from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0002_alter_contestsubmission_unique_together_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='contest',
            name='start_date',
            field=models.DateTimeField(blank=True, null=True, help_text='Contest start date (optional)'),
        ),
    ]
