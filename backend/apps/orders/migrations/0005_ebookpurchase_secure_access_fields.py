"""
Migration: Add secure ebook access fields and reading progress tracking.
"""
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0004_cartcheckoutsession'),
    ]

    operations = [
        # Add secure access token fields
        migrations.AddField(
            model_name='ebookpurchase',
            name='access_token',
            field=models.CharField(
                blank=True,
                help_text='Unique token for secure PDF access',
                max_length=255,
                null=True,
                unique=True
            ),
        ),
        migrations.AddField(
            model_name='ebookpurchase',
            name='access_token_created',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='ebookpurchase',
            name='access_token_expires',
            field=models.DateTimeField(blank=True, null=True),
        ),
        # Add Cashfree order fields
        migrations.AddField(
            model_name='ebookpurchase',
            name='cashfree_order_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='ebookpurchase',
            name='cashfree_payment_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        # Add order_id field
        migrations.AddField(
            model_name='ebookpurchase',
            name='order_id',
            field=models.CharField(
                blank=True,
                help_text='Cashfree order ID for this purchase',
                max_length=100,
                null=True
            ),
        ),
        # Add reading progress tracking
        migrations.AddField(
            model_name='ebookpurchase',
            name='current_page',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='ebookpurchase',
            name='reading_progress',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]