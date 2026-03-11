import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.books.models import Book
from apps.authors.models import Author

print('=== CURRENT DATABASE STATE ===')
print(f'Total Books: {Book.objects.count()}')
print(f'Total Authors: {Author.objects.count()}')
print()
print('Authors:')
for a in Author.objects.all():
    print(f'  - {a.name} ({a.email}) - Books: {a.books.count()}')
print()
print('Books (recent):')
for b in Book.objects.all().order_by('-created_at')[:10]:
    author_name = b.author.name if b.author else "No author"
    print(f'  - {b.title} by {author_name}')
