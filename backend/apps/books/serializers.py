"""
Serializers for Books App.
"""
import logging
from django.conf import settings
from rest_framework import serializers
from .models import Book, Category, BookSubmission, ContactMessage
from apps.authors.serializers import AuthorSerializer, AuthorListSerializer

logger = logging.getLogger('apps')


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for Category model.
    """
    books_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'books_count', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_books_count(self, obj):
        return obj.books.count()


def _cloudinary_url(name, resource_type='image'):
    """Construct a Cloudinary delivery URL from a stored field name.

    NOTE: django-cloudinary-storage prepends MEDIA_URL (= 'media/') as a
    folder prefix when uploading, so the actual Cloudinary public_id is
    'media/<name>'.  This function should only be used when you already
    have the full public_id (including any prefix), or for admin display
    fallbacks.  For serialiser use, always call field_file.url instead —
    the storage backend handles the prefix automatically.
    """
    cloud = getattr(settings, 'CLOUDINARY_STORAGE', {}).get('CLOUD_NAME', '')
    if not cloud or not name:
        return None
    clean = str(name).lstrip('/')

    if clean.startswith('http://') or clean.startswith('https://'):
        # Already has a delivery type segment — return unchanged
        if '/image/upload/' in clean or '/raw/upload/' in clean or '/video/upload/' in clean:
            return clean
        # Malformed: has cloud domain but missing resource_type/upload entirely
        prefix = f'res.cloudinary.com/{cloud}/'
        if prefix in clean:
            path = clean.split(prefix, 1)[1]
            return f'https://res.cloudinary.com/{cloud}/{resource_type}/upload/{path}'
        return clean  # unknown URL format — return unchanged

    return f'https://res.cloudinary.com/{cloud}/{resource_type}/upload/{clean}'


def _file_url(field_file, request=None, resource_type='image'):
    """Return an absolute URL for any storage-backed file field.

    Uses field_file.url which calls MediaCloudinaryStorage._get_url().
    That method calls _prepend_prefix() to add the MEDIA_URL folder prefix
    ('media/') so Cloudinary resolves the correct public_id.
    Do NOT call _cloudinary_url() here — it would miss the prefix.
    """
    if not field_file:
        return None

    stored_name = getattr(field_file, 'name', None)

    try:
        url = field_file.url
    except Exception as e:
        logger.warning('_file_url: .url raised %s for field %s', e, stored_name)
        return None

    if not url:
        return None

    if url.startswith('http://') or url.startswith('https://'):
        return url

    if request is not None:
        return request.build_absolute_uri(url)
    return url


class BookSerializer(serializers.ModelSerializer):
    """
    Serializer for Book model.
    """
    author_name = serializers.ReadOnlyField()
    category_name = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    has_pdf = serializers.SerializerMethodField()
    discounted_price = serializers.SerializerMethodField()
    ebook_final_price = serializers.SerializerMethodField()
    physical_final_price = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()
    pdf_file = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            'id', 'title', 'author', 'author_name', 'description', 'price',
            'discount_percentage', 'discounted_price',
            'ebook_price', 'ebook_final_price',
            'physical_price', 'physical_final_price',
            'book_type',
            'category', 'category_name', 'cover_image', 'pdf_file',
            'published_date', 'isbn', 'pages', 'language', 'is_featured', 'is_active',
            'has_pdf', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_cover_image(self, obj):
        return _file_url(obj.cover_image, self.context.get('request'), resource_type='image')

    def get_pdf_file(self, obj):
        return _file_url(obj.pdf_file, self.context.get('request'), resource_type='raw')
    
    def get_category(self, obj):
        """Return category as string name for frontend compatibility"""
        return obj.category.name if obj.category else None
    
    def get_category_name(self, obj):
        return obj.category.name if obj.category else None
    
    def get_has_pdf(self, obj):
        return bool(obj.pdf_file)
    
    def get_discounted_price(self, obj):
        if obj.discount_percentage and obj.discount_percentage > 0:
            discount_amount = (obj.price * obj.discount_percentage) / 100
            return float(obj.price) - float(discount_amount)
        return obj.price
    
    def get_ebook_final_price(self, obj):
        """Calculate final eBook price after discount"""
        if obj.ebook_price and obj.discount_percentage:
            discount_amount = obj.ebook_price * (obj.discount_percentage / 100)
            return float(obj.ebook_price) - float(discount_amount)
        return obj.ebook_price
    
    def get_physical_final_price(self, obj):
        """Calculate final physical book price after discount"""
        if obj.physical_price and obj.discount_percentage:
            discount_amount = obj.physical_price * (obj.discount_percentage / 100)
            return float(obj.physical_price) - float(discount_amount)
        return obj.physical_price
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['author'] = AuthorListSerializer(instance.author).data
        return representation


class BookListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for Book list view.
    """
    author_name = serializers.ReadOnlyField()
    category_name = serializers.SerializerMethodField()
    has_pdf = serializers.SerializerMethodField()
    discounted_price = serializers.SerializerMethodField()
    author = serializers.SerializerMethodField()
    ebook_final_price = serializers.SerializerMethodField()
    physical_final_price = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            'id', 'title', 'author', 'author_name', 'price', 'discount_percentage', 'discounted_price',
            'ebook_price', 'ebook_final_price',
            'physical_price', 'physical_final_price',
            'book_type', 'stock',
            'category_name', 'cover_image', 'has_pdf', 'published_date', 'is_featured'
        ]

    def get_cover_image(self, obj):
        return _file_url(obj.cover_image, self.context.get('request'), resource_type='image')

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None

    def get_has_pdf(self, obj):
        return bool(obj.pdf_file)
    
    def get_discounted_price(self, obj):
        if obj.discount_percentage and obj.discount_percentage > 0:
            discount_amount = (obj.price * obj.discount_percentage) / 100
            return float(obj.price) - float(discount_amount)
        return obj.price
    
    def get_ebook_final_price(self, obj):
        """Calculate final eBook price after discount"""
        if obj.ebook_price and obj.discount_percentage:
            discount_amount = obj.ebook_price * (obj.discount_percentage / 100)
            return float(obj.ebook_price) - float(discount_amount)
        return obj.ebook_price
    
    def get_physical_final_price(self, obj):
        """Calculate final physical book price after discount"""
        if obj.physical_price and obj.discount_percentage:
            discount_amount = obj.physical_price * (obj.discount_percentage / 100)
            return float(obj.physical_price) - float(discount_amount)
        return obj.physical_price
    
    def get_author(self, obj):
        from apps.authors.serializers import AuthorListSerializer
        return AuthorListSerializer(obj.author).data


class BookCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating/updating Book.
    """
    category = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    author_email = serializers.EmailField(required=False, allow_blank=True, write_only=True)
    author_mobile = serializers.CharField(required=False, allow_blank=True, write_only=True)
    author_name = serializers.CharField(required=False, allow_blank=True, write_only=True)
    
    def validate_isbn(self, value):
        """Validate ISBN is 10 or 13 digits."""
        if value and (len(value) not in [10, 13] or not value.isdigit()):
            raise serializers.ValidationError("ISBN must be exactly 10 or 13 digits.")
        return value
    
    def validate_discount_percentage(self, value):
        """Validate discount percentage is between 0 and 100."""
        if value and (value < 0 or value > 100):
            raise serializers.ValidationError("Discount percentage must be between 0 and 100.")
        return value
    
    def validate_category(self, value):
        """Convert string category name to Category object."""
        if not value or value == "":
            return None
        from apps.books.models import Category
        # Try to find existing category first
        try:
            category = Category.objects.get(name=value)
            return category
        except Category.DoesNotExist:
            # Create new category if it doesn't exist
            category = Category.objects.create(name=value)
            return category
    
    def create(self, validated_data):
        """Create book with automatic author creation/linking."""
        author_email = validated_data.pop('author_email', None)
        author_mobile = validated_data.pop('author_mobile', None)
        author_id = validated_data.get('author')
        author_name = validated_data.get('author_name')
        
        # If author_email or author_mobile is provided, find or create author
        if (author_email or author_mobile) and not author_id:
            from apps.authors.models import Author
            author = None
            
            # Try to find existing author by matching name+email+mobile_number
            # First try exact match on all three
            if author_email and author_mobile:
                author = Author.objects.filter(
                    name__iexact=author_name or author_email.split('@')[0],
                    email__iexact=author_email,
                    mobile_number=author_mobile
                ).first()
            
            # If not found, try by email only
            if not author and author_email:
                try:
                    author = Author.objects.get(email__iexact=author_email)
                except Author.DoesNotExist:
                    pass
            
            # If not found, try by mobile number only
            if not author and author_mobile:
                try:
                    author = Author.objects.get(mobile_number=author_mobile)
                except Author.DoesNotExist:
                    pass
            
            # Create new author if not found
            if not author:
                author_name_val = author_name or (author_email.split('@')[0] if author_email else author_mobile)
                author = Author.objects.create(
                    name=author_name_val,
                    email=author_email or '',
                    mobile_number=author_mobile or ''
                )
            validated_data['author'] = author
        
        # Ensure is_active defaults to True if not provided
        if 'is_active' not in validated_data:
            validated_data['is_active'] = True
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Update book with automatic author creation/linking."""
        author_email = validated_data.pop('author_email', None)
        author_mobile = validated_data.pop('author_mobile', None)
        author_id = validated_data.get('author')
        author_name = validated_data.get('author_name')
        
        # If author_email or author_mobile is provided, find or create author
        if (author_email or author_mobile) and not author_id:
            from apps.authors.models import Author
            author = None
            
            # Try to find existing author by matching name+email+mobile_number
            # First try exact match on all three
            if author_email and author_mobile:
                author = Author.objects.filter(
                    name__iexact=author_name or author_email.split('@')[0],
                    email__iexact=author_email,
                    mobile_number=author_mobile
                ).first()
            
            # If not found, try by email only
            if not author and author_email:
                try:
                    author = Author.objects.get(email__iexact=author_email)
                except Author.DoesNotExist:
                    pass
            
            # If not found, try by mobile number only
            if not author and author_mobile:
                try:
                    author = Author.objects.get(mobile_number=author_mobile)
                except Author.DoesNotExist:
                    pass
            
            # Create new author if not found
            if not author:
                author_name_val = author_name or (author_email.split('@')[0] if author_email else author_mobile)
                author = Author.objects.create(
                    name=author_name_val,
                    email=author_email or '',
                    mobile_number=author_mobile or ''
                )
            validated_data['author'] = author
        
        return super().update(instance, validated_data)
    
    class Meta:
        model = Book
        fields = [
            'title', 'author', 'author_name', 'author_email', 'author_mobile', 'description', 'price', 'discount_percentage', 'category',
            'cover_image', 'pdf_file', 'published_date', 'isbn', 'pages', 'language',
            'is_featured', 'is_active', 'ebook_price', 'physical_price', 'book_type'
        ]
        extra_kwargs = {
            'author_email': {'write_only': True},
            'author_mobile': {'write_only': True},
            'author_name': {'write_only': True}
        }


class BookSubmissionSerializer(serializers.ModelSerializer):
    """
    Serializer for BookSubmission model.
    """
    class Meta:
        model = BookSubmission
        fields = ['id', 'name', 'email', 'contact', 'book_title', 'description', 'file', 'status', 'created_at']
        read_only_fields = ['id', 'status', 'created_at']


class ContactMessageSerializer(serializers.ModelSerializer):
    """
    Serializer for ContactMessage model.
    """
    class Meta:
        model = ContactMessage
        fields = ['id', 'name', 'email', 'message', 'created_at', 'is_read']
        read_only_fields = ['id', 'created_at', 'is_read']
