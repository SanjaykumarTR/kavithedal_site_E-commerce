"""Script to add sample data to the database"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from apps.books.models import Book, Category
from apps.authors.models import Author

# Create a category
cat, _ = Category.objects.get_or_create(name='Literature', description='Tamil Literature books')

# Create an author
author, _ = Author.objects.get_or_create(
    name='Kavi Velan',
    biography='A renowned Tamil poet and writer'
)

# Create books
books = [
    {'title': 'Vaazhiya Vilakku', 'price': 250},
    {'title': 'Pudhiya Ulagu', 'price': 300},
    {'title': 'Kadal Kadandhu', 'price': 275},
    {'title': 'Nadchanthiraikal', 'price': 200},
    {'title': 'Malarum Malarndhal', 'price': 350},
]

for b in books:
    Book.objects.get_or_create(
        title=b['title'],
        defaults={
            'price': b['price'],
            'description': 'A great Tamil book',
            'category': cat,
            'author': author,
            'is_active': True
        }
    )

print(f'Books: {Book.objects.count()}')
print(f'Authors: {Author.objects.count()}')
print(f'Categories: {Category.objects.count()}')
