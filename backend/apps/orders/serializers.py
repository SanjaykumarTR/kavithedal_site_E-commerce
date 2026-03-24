"""
Serializers for Orders App.
"""
from rest_framework import serializers
from .models import Order, Payment, UserLibrary, EbookPurchase, DeliveryZone
from apps.books.serializers import BookSerializer, _file_url


class DeliveryZoneSerializer(serializers.ModelSerializer):
    """Serializer for DeliveryZone model."""
    delivery_time = serializers.CharField(read_only=True)
    
    class Meta:
        model = DeliveryZone
        fields = [
            'id', 'pincode', 'city', 'state', 'zone_type', 
            'delivery_charge', 'min_delivery_days', 'max_delivery_days',
            'delivery_time', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DeliveryZoneLookupSerializer(serializers.Serializer):
    """Serializer for looking up delivery zone by pincode."""
    pincode = serializers.CharField(max_length=10)


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for Order model."""
    book_title = serializers.CharField(source='book.title', read_only=True)
    book_cover = serializers.SerializerMethodField()
    user_email = serializers.CharField(source='user.email', read_only=True)

    def get_book_cover(self, obj):
        return _file_url(obj.book.cover_image, self.context.get('request'), resource_type='image')
    delivery_zone_info = DeliveryZoneSerializer(source='delivery_zone', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'user', 'user_email', 'book', 'book_title', 'book_cover',
            'order_type', 'quantity', 'book_price', 'delivery_charge', 'total_price',
            'status', 'payment_status', 'delivery_status', 
            'full_name', 'email', 'phone',
            'shipping_address', 'shipping_city', 'shipping_state', 'shipping_pincode',
            'delivery_zone_info', 'estimated_delivery_date',
            'tracking_number', 'razorpay_order_id', 'razorpay_payment_id',
            'transaction_id', 'ordered_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'status', 'ordered_at', 'updated_at']


class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating orders with delivery zone calculation."""
    pincode = serializers.CharField(max_length=10, write_only=True, required=False)
    
    class Meta:
        model = Order
        fields = [
            'book', 'order_type', 'quantity', 
            'full_name', 'email', 'phone',
            'shipping_address', 'shipping_city', 'shipping_state', 'shipping_pincode',
            'pincode', 'delivery_charge', 'estimated_delivery_date'
        ]
    
    def create(self, validated_data):
        user = self.context['request'].user
        book = validated_data['book']
        order_type = validated_data.get('order_type', 'physical')
        quantity = validated_data.get('quantity', 1)
        pincode = validated_data.pop('pincode', None)
        
        # Get the appropriate price
        if order_type == 'ebook':
            book_price = book.ebook_price or 0
        else:
            book_price = book.physical_price or book.price
        
        # Calculate delivery charge based on PIN code
        delivery_charge = 0
        delivery_zone = None
        estimated_delivery_date = None
        
        if order_type == 'physical' and pincode:
            try:
                delivery_zone = DeliveryZone.objects.get(pincode=pincode, is_active=True)
                delivery_charge = delivery_zone.delivery_charge
                
                # Calculate estimated delivery date
                from datetime import date, timedelta
                delivery_days = delivery_zone.max_delivery_days
                estimated_delivery_date = date.today() + timedelta(days=delivery_days)
            except DeliveryZone.DoesNotExist:
                # Default delivery charge if PIN code not found
                delivery_charge = 100  # Default Rs. 100
                
                # Calculate estimated delivery date (default 7 days)
                from datetime import date, timedelta
                estimated_delivery_date = date.today() + timedelta(days=7)
        
        total_price = book_price * quantity + delivery_charge
        
        order = Order.objects.create(
            user=user,
            book=book,
            order_type=order_type,
            quantity=quantity,
            book_price=book_price,
            delivery_charge=delivery_charge,
            total_price=total_price,
            delivery_zone=delivery_zone,
            estimated_delivery_date=estimated_delivery_date,
            full_name=validated_data.get('full_name'),
            email=validated_data.get('email'),
            phone=validated_data.get('phone'),
            shipping_address=validated_data.get('shipping_address'),
            shipping_city=validated_data.get('shipping_city'),
            shipping_state=validated_data.get('shipping_state'),
            shipping_pincode=validated_data.get('shipping_pincode'),
        )
        return order


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for Payment model."""
    order_book_title = serializers.CharField(source='order.book.title', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'order_book_title', 'razorpay_order_id',
            'razorpay_payment_id', 'amount', 'currency', 'status',
            'payment_method', 'transaction_id', 'error_code',
            'error_message', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'razorpay_order_id', 'created_at', 'updated_at']


class PaymentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating payments."""
    
    class Meta:
        model = Payment
        fields = ['order', 'razorpay_order_id', 'razorpay_payment_id',
                  'razorpay_signature', 'amount', 'payment_method',
                  'transaction_id', 'status', 'error_code', 'error_message']


class UserLibrarySerializer(serializers.ModelSerializer):
    """Serializer for User Library."""
    book = BookSerializer(read_only=True)
    book_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = UserLibrary
        fields = ['id', 'book', 'book_id', 'purchased_at', 'order']
        read_only_fields = ['id', 'purchased_at', 'order']


class UserLibraryListSerializer(serializers.ModelSerializer):
    """Serializer for listing user's library."""
    book_id = serializers.UUIDField(source='book.id', read_only=True)
    book_title = serializers.CharField(source='book.title', read_only=True)
    book_cover = serializers.SerializerMethodField()
    book_author = serializers.CharField(source='book.author.name', read_only=True)
    has_pdf = serializers.SerializerMethodField()

    def get_book_cover(self, obj):
        return _file_url(obj.book.cover_image, self.context.get('request'), resource_type='image')
    
    def get_has_pdf(self, obj):
        """Check if book has a PDF file."""
        return bool(obj.book.pdf_file)
    
    class Meta:
        model = UserLibrary
        fields = [
            'id', 'book_id', 'book_title', 'book_cover', 'book_author',
            'has_pdf', 'purchased_at', 'order'
        ]


class EbookPurchaseSerializer(serializers.ModelSerializer):
    """Serializer for EbookPurchase model."""
    book_title = serializers.CharField(source='book.title', read_only=True)
    book_cover = serializers.SerializerMethodField()
    user_email = serializers.CharField(source='user.email', read_only=True)

    def get_book_cover(self, obj):
        return _file_url(obj.book.cover_image, self.context.get('request'), resource_type='image')
    
    class Meta:
        model = EbookPurchase
        fields = [
            'id', 'user', 'user_email', 'book', 'book_title', 'book_cover',
            'user_name', 'email', 'phone', 'address', 'price',
            'payment_status', 'razorpay_order_id', 'razorpay_payment_id',
            'transaction_id', 'order_date', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'payment_status', 'razorpay_order_id', 
                           'razorpay_payment_id', 'transaction_id', 'order_date', 'updated_at']


class EbookPurchaseCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating EbookPurchase with Razorpay payment."""
    
    class Meta:
        model = EbookPurchase
        fields = ['book', 'user_name', 'email', 'phone', 'address', 'price']
    
    def create(self, validated_data):
        user = self.context['request'].user
        book = validated_data['book']
        
        purchase = EbookPurchase.objects.create(
            user=user,
            book=book,
            user_name=validated_data['user_name'],
            email=validated_data['email'],
            phone=validated_data['phone'],
            address=validated_data['address'],
            price=validated_data['price'],
            payment_status='initiated'
        )
        return purchase


class EbookPurchaseVerifySerializer(serializers.Serializer):
    """Serializer for verifying Razorpay payment."""
    purchase_id = serializers.UUIDField()
    razorpay_payment_id = serializers.CharField()
    razorpay_signature = serializers.CharField()
    razorpay_order_id = serializers.CharField(required=False)
