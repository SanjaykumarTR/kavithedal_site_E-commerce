from django.db import migrations


class Migration(migrations.Migration):
    """
    Remove the `shipping_phone` column from the orders table.
    This field was present in the initial migration but was removed from the
    model (replaced by `phone`, added in migration 0003).  Django detects the
    DB column as an unapplied model change, so this migration drops it cleanly.
    """

    dependencies = [
        ('orders', '0005_ebookpurchase_secure_access_fields'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='shipping_phone',
        ),
    ]
