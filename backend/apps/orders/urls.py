"""
URL Configuration for Orders App — Cashfree payment integration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    OrderViewSet, PaymentViewSet, UserLibraryViewSet,
    CreateOrderView, EbookPurchaseView, CartCheckoutView,
    CashfreeVerifyPaymentView, DeliveryZoneViewSet, CalculateDeliveryView,
    CashfreeWebhookView,
)

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'library', UserLibraryViewSet, basename='library')
router.register(r'delivery-zones', DeliveryZoneViewSet, basename='delivery-zone')

urlpatterns = [
    # Delivery zone actions (must come before router.urls to avoid prefix conflicts)
    path('delivery-zones/calculate/', DeliveryZoneViewSet.as_view({'post': 'calculate_delivery'}), name='calculate-delivery'),
    path('delivery-zones/check/', DeliveryZoneViewSet.as_view({'get': 'by_pincode'}), name='by-pincode'),

    # Router-generated URLs
    path('', include(router.urls)),

    # ── Single-book purchase (physical or ebook via CreateOrderView) ───────────
    path('create-order/', CreateOrderView.as_view(), name='create-order'),

    # ── Dedicated eBook checkout (collects name / phone / address) ─────────────
    path('ebook-purchase/', EbookPurchaseView.as_view(), name='ebook-purchase'),

    # ── Cart checkout (multi-item) ─────────────────────────────────────────────
    path('cart-checkout/', CartCheckoutView.as_view(), name='cart-checkout'),

    # ── Payment verification (called from /payment-success after Cashfree redirect)
    path('verify-cashfree-payment/', CashfreeVerifyPaymentView.as_view(), name='verify-cashfree-payment'),

    # ── Delivery charge calculator ─────────────────────────────────────────────
    path('calculate-delivery/', CalculateDeliveryView.as_view(), name='calculate-delivery-total'),

    # ── Cashfree webhook (also reachable at /api/payment/webhook/ via config/urls.py)
    path('webhook/', CashfreeWebhookView.as_view(), name='cashfree-webhook'),
]
