"""
URL Configuration for Orders App.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    OrderViewSet, PaymentViewSet, UserLibraryViewSet,
    CreateOrderView, VerifyPaymentView,
    EbookPurchaseView, VerifyEbookPaymentView,
    DeliveryZoneViewSet, CartCheckoutView, CartPaymentVerifyView
)

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'library', UserLibraryViewSet, basename='library')
router.register(r'delivery-zones', DeliveryZoneViewSet, basename='delivery-zone')

urlpatterns = [
    # Custom delivery zone actions (must come before router.urls)
    path('delivery-zones/calculate/', DeliveryZoneViewSet.as_view({'post': 'calculate_delivery'}), name='calculate-delivery'),
    path('delivery-zones/check/', DeliveryZoneViewSet.as_view({'get': 'by_pincode'}), name='by-pincode'),
    # Include router URLs
    path('', include(router.urls)),
    path('create-order/', CreateOrderView.as_view(), name='create-order'),
    path('verify-payment/', VerifyPaymentView.as_view(), name='verify-payment'),
    path('ebook-purchase/', EbookPurchaseView.as_view(), name='ebook-purchase'),
    path('verify-ebook-payment/', VerifyEbookPaymentView.as_view(), name='verify-ebook-payment'),
    path('cart-checkout/', CartCheckoutView.as_view(), name='cart-checkout'),
    path('cart-verify-payment/', CartPaymentVerifyView.as_view(), name='cart-verify-payment'),
]
