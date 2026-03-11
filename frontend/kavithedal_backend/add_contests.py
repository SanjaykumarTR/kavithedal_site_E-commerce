import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.contests.models import Contest
from django.utils import timezone
from datetime import timedelta

# Check if contests exist
if Contest.objects.exists():
    print(f"Contests already exist: {Contest.objects.count()}")
else:
    # Create sample contests
    contest1 = Contest.objects.create(
        title='Tamil Poetry Competition 2026',
        description='Share your best Tamil poetry with us! Open to all age groups. Express your emotions through beautiful verses.',
        deadline=timezone.now() + timedelta(days=30),
        prize_details='First Prize: ₹10,000\nSecond Prize: ₹5,000\nThird Prize: ₹2,500',
        rules='1. Poem must be original\n2. Maximum 50 lines\n3. Tamil language only\n4. Last date to submit: 30 days from announcement',
        is_active=True
    )

    contest2 = Contest.objects.create(
        title='Short Story Contest',
        description='Write an engaging short story in Tamil or English. Theme: Village Life',
        deadline=timezone.now() + timedelta(days=30),
        prize_details='First Prize: ₹15,000\nSecond Prize: ₹7,500\nThird Prize: ₹3,000',
        rules='1. Story must be original\n2. Word limit: 2000-5000 words\n3. Tamil or English\n4. Last date to submit: 30 days from announcement',
        is_active=True
    )

    print(f'Created {Contest.objects.count()} contests')
