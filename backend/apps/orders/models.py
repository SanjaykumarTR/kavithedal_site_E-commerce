"""
Order and Payment Models for Kavithedal Publications.
"""
import uuid
from django.db import models
from django.conf import settings
from apps.books.models import Book


class DeliveryZone(models.Model):
    """
    Delivery zones based on PIN codes for physical book delivery.
    All deliveries ship from Dharmapuri, Tamil Nadu.
    """
    ZONE_CHOICES = [
        ('local', 'Local (TN)'),
        ('south', 'South India'),
        ('national', 'Rest of India'),
        ('remote', 'Remote Areas'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pincode = models.CharField(max_length=10, unique=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zone_type = models.CharField(max_length=20, choices=ZONE_CHOICES)
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2)
    min_delivery_days = models.PositiveIntegerField(default=3)
    max_delivery_days = models.PositiveIntegerField(default=5)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'delivery_zones'
        verbose_name = 'Delivery Zone'
        verbose_name_plural = 'Delivery Zones'
        ordering = ['pincode']
    
    def __str__(self):
        return f"{self.pincode} - {self.city}, {self.state} ({self.zone_type})"
    
    @property
    def delivery_time(self):
        if self.min_delivery_days == self.max_delivery_days:
            return f"{self.min_delivery_days} Days"
        return f"{self.min_delivery_days}-{self.max_delivery_days} Days"


class Order(models.Model):
    """
    Order model for managing book purchases.
    """
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    DELIVERY_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('packed', 'Packed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    order_type = models.CharField(
        max_length=20,
        choices=[('ebook', 'eBook'), ('physical', 'Physical Book')],
        default='physical'
    )
    quantity = models.PositiveIntegerField(default=1)
    book_price = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        default='pending'
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    delivery_status = models.CharField(
        max_length=20,
        choices=DELIVERY_STATUS_CHOICES,
        default='pending'
    )
    # Shipping details
    full_name = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=15, blank=True)
    shipping_address = models.TextField(blank=True, null=True)
    shipping_city = models.CharField(max_length=100, blank=True)
    shipping_state = models.CharField(max_length=100, blank=True)
    shipping_pincode = models.CharField(max_length=10, blank=True)
    # Delivery zone info
    delivery_zone = models.ForeignKey(
        DeliveryZone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )
    estimated_delivery_date = models.DateField(null=True, blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)
    # Payment info
    razorpay_order_id = models.CharField(max_length=100, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)
    ordered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'orders'
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-ordered_at']
    
    def __str__(self):
        return f"Order {self.id} - {self.book.title}"
    
    @property
    def is_ebook(self):
        return self.order_type == 'ebook'
    
    @property
    def is_physical(self):
        return self.order_type == 'physical'


class Payment(models.Model):
    """
    Payment model for managing payments via Razorpay.
    """
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('initiated', 'Initiated'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('razorpay', 'Razorpay'),
        ('card', 'Credit/Debit Card'),
        ('upi', 'UPI'),
        ('netbanking', 'Net Banking'),
        ('simulated', 'Simulated (Dev/Test)'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    razorpay_order_id = models.CharField(max_length=100, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    razorpay_signature = models.CharField(max_length=200, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        blank=True
    )
    transaction_id = models.CharField(max_length=100, blank=True)
    error_code = models.CharField(max_length=50, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payments'
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Payment {self.id} - {self.amount}"


class UserLibrary(models.Model):
    """
    User library model - tracks purchased eBooks for each user.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='library'
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='purchasers'
    )
    purchased_at = models.DateTimeField(auto_now_add=True)
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        related_name='library_entries'
    )
    
    class Meta:
        db_table = 'user_library'
        verbose_name = 'User Library'
        verbose_name_plural = 'User Libraries'
        unique_together = [['user', 'book']]
        ordering = ['-purchased_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.book.title}"


class EbookPurchase(models.Model):
    """
    eBook Purchase model - stores customer details for eBook purchases.
    """
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('initiated', 'Initiated'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ebook_purchases'
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='ebook_purchases'
    )
    # Customer details
    user_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    address = models.TextField()
    # Order details
    price = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    # Payment gateway details
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=200, blank=True, null=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    # Timestamps
    order_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ebook_purchases'
        verbose_name = 'eBook Purchase'
        verbose_name_plural = 'eBook Purchases'
        ordering = ['-order_date']
    
    def __str__(self):
        return f"eBook Purchase {self.id} - {self.book.title} - {self.email}"
