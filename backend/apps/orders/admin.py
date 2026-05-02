"""
Admin configuration for Orders app.
"""
from django.contrib import admin
from .models import DeliveryZone, Order, Payment, UserLibrary, EbookPurchase, CartCheckoutSession


@admin.register(DeliveryZone)
class DeliveryZoneAdmin(admin.ModelAdmin):
    list_display = ['pincode', 'city', 'state', 'zone_type', 'delivery_charge', 'min_delivery_days', 'max_delivery_days', 'is_active']
    list_filter = ['zone_type', 'is_active', 'state']
    search_fields = ['pincode', 'city', 'state']
    ordering = ['pincode']
    list_editable = ['is_active', 'delivery_charge']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'book', 'order_type', 'status', 'payment_status', 'delivery_status', 'total_price', 'payment_method_display', 'ordered_at']
    list_filter = ['order_type', 'status', 'payment_status', 'delivery_status', 'ordered_at']
    search_fields = ['user__email', 'book__title', 'shipping_pincode', 'full_name', 'payu_order_id', 'razorpay_order_id']
    readonly_fields = ['id', 'ordered_at', 'updated_at']
    date_hierarchy = 'ordered_at'
    raw_id_fields = ['user', 'book', 'delivery_zone']

    def payment_method_display(self, obj):
        """Display the payment method used (PayU, Razorpay, Cashfree, etc.)"""
        if obj.payments.exists():
            return obj.payments.first().payment_method
        return 'N/A'
    payment_method_display.short_description = 'Payment Method'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'amount', 'status', 'payment_method', 'gateway_id', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['order__id', 'transaction_id', 'payu_payment_id', 'razorpay_payment_id', 'cashfree_payment_id']
    readonly_fields = ['id', 'created_at', 'updated_at']

    def gateway_id(self, obj):
        """Display gateway-specific payment ID"""
        if obj.payment_method == 'payu' and obj.payu_payment_id:
            return obj.payu_payment_id
        elif obj.payment_method == 'razorpay' and obj.razorpay_payment_id:
            return obj.razorpay_payment_id
        elif obj.cashfree_payment_id:
            return obj.cashfree_payment_id
        return '-'
    gateway_id.short_description = 'Gateway Payment ID'


@admin.register(UserLibrary)
class UserLibraryAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'book', 'purchased_at']
    list_filter = ['purchased_at']
    search_fields = ['user__email', 'book__title']
    raw_id_fields = ['user', 'book', 'order']


@admin.register(EbookPurchase)
class EbookPurchaseAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'book', 'email', 'payment_status', 'price', 'gateway_id', 'order_date']
    list_filter = ['payment_status', 'order_date']
    search_fields = ['user__email', 'book__title', 'email', 'phone', 'payu_order_id']
    readonly_fields = ['id', 'order_date', 'updated_at']
    raw_id_fields = ['user', 'book']

    def gateway_id(self, obj):
        """Display gateway order ID"""
        return obj.payu_order_id or obj.razorpay_order_id or obj.cashfree_order_id or '-'
    gateway_id.short_description = 'Gateway Order ID'


@admin.register(CartCheckoutSession)
class CartCheckoutSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'total_amount', 'status', 'gateway_order_id', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['payu_order_id', 'cashfree_order_id', 'user__email']
    readonly_fields = ['id', 'created_at']

    def gateway_order_id(self, obj):
        return obj.payu_order_id or obj.cashfree_order_id or '-'
    gateway_order_id.short_description = 'Gateway Order ID'
