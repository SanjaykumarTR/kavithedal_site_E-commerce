"""
Admin configuration for Orders app.
"""
from django.contrib import admin
from .models import DeliveryZone, Order, Payment, UserLibrary, EbookPurchase


@admin.register(DeliveryZone)
class DeliveryZoneAdmin(admin.ModelAdmin):
    list_display = ['pincode', 'city', 'state', 'zone_type', 'delivery_charge', 'min_delivery_days', 'max_delivery_days', 'is_active']
    list_filter = ['zone_type', 'is_active', 'state']
    search_fields = ['pincode', 'city', 'state']
    ordering = ['pincode']
    list_editable = ['is_active', 'delivery_charge']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'book', 'order_type', 'status', 'payment_status', 'delivery_status', 'total_price', 'ordered_at']
    list_filter = ['order_type', 'status', 'payment_status', 'delivery_status', 'ordered_at']
    search_fields = ['user__email', 'book__title', 'shipping_pincode', 'full_name']
    readonly_fields = ['id', 'ordered_at', 'updated_at']
    date_hierarchy = 'ordered_at'
    raw_id_fields = ['user', 'book', 'delivery_zone']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'amount', 'status', 'payment_method', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['order__id', 'razorpay_payment_id', 'transaction_id']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(UserLibrary)
class UserLibraryAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'book', 'purchased_at']
    list_filter = ['purchased_at']
    search_fields = ['user__email', 'book__title']
    raw_id_fields = ['user', 'book', 'order']


@admin.register(EbookPurchase)
class EbookPurchaseAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'book', 'email', 'payment_status', 'price', 'order_date']
    list_filter = ['payment_status', 'order_date']
    search_fields = ['user__email', 'book__title', 'email', 'phone']
    readonly_fields = ['id', 'order_date', 'updated_at']
    raw_id_fields = ['user', 'book']
