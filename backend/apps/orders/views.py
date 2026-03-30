"""
Views for Orders App — Cashfree payment integration.
Razorpay has been fully removed and replaced with Cashfree PG (API v2023-08-01).
"""
import base64
import hashlib
import hmac
import json
import logging
import uuid
from datetime import date, timedelta

import requests as http_requests
from django.conf import settings
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.utils import is_authorized_admin
from .models import CartCheckoutSession, DeliveryZone, EbookPurchase, Order, Payment, UserLibrary
from .serializers import (
    DeliveryZoneSerializer, OrderCreateSerializer, OrderSerializer,
    PaymentSerializer, UserLibraryListSerializer, UserLibrarySerializer,
)

logger = logging.getLogger('apps')

# ─── Cashfree API Helpers ──────────────────────────────────────────────────────

_CF_PROD_URL = 'https://api.cashfree.com/pg'
_CF_SANDBOX_URL = 'https://sandbox.cashfree.com/pg'
_CF_API_VERSION = '2023-08-01'


def _cashfree_configured():
    """Return True when Cashfree credentials are set in env."""
    return bool(
        getattr(settings, 'CASHFREE_APP_ID', '') and
        getattr(settings, 'CASHFREE_SECRET_KEY', '')
    )


def _cf_base_url():
    env = getattr(settings, 'CASHFREE_ENV', 'sandbox')
    return _CF_PROD_URL if env == 'production' else _CF_SANDBOX_URL


def _cf_headers():
    return {
        'x-client-id': settings.CASHFREE_APP_ID,
        'x-client-secret': settings.CASHFREE_SECRET_KEY,
        'x-api-version': _CF_API_VERSION,
        'Content-Type': 'application/json',
    }


def _cf_make_order_id(prefix, uid):
    """
    Build a Cashfree-compatible order ID.
    Rules: max 50 chars, alphanumeric + hyphen + underscore only.
    """
    hex_part = str(uid).replace('-', '')[:20]
    return f'kv-{prefix}-{hex_part}'


def _normalize_phone(phone):
    """Strip country code — Cashfree requires a 10-digit Indian mobile number."""
    phone = str(phone).strip().replace(' ', '').replace('-', '').replace('+', '')
    if phone.startswith('91') and len(phone) == 12:
        phone = phone[2:]
    return phone[:10] or '9999999999'


def _cf_create_order(cf_order_id, amount, customer_id, customer_email,
                     customer_phone, return_url, note=''):
    """POST /pg/orders — create a Cashfree payment order."""
    payload = {
        'order_id': cf_order_id,
        'order_amount': round(float(amount), 2),
        'order_currency': 'INR',
        'customer_details': {
            'customer_id': str(customer_id)[:50],
            'customer_email': customer_email,
            'customer_phone': _normalize_phone(customer_phone),
        },
        'order_meta': {
            'return_url': return_url,
        },
    }
    if note:
        payload['order_note'] = str(note)[:50]

    resp = http_requests.post(
        f'{_cf_base_url()}/orders',
        json=payload,
        headers=_cf_headers(),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _cf_get_order(cf_order_id):
    """GET /pg/orders/{order_id} — fetch order status from Cashfree."""
    resp = http_requests.get(
        f'{_cf_base_url()}/orders/{cf_order_id}',
        headers=_cf_headers(),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


# ─── Delivery Helpers ──────────────────────────────────────────────────────────

def calculate_delivery_charge(total_price):
    """
    Calculate delivery charge for physical books based on order total.
      < ₹500  → ₹40
      ₹500–₹999 → ₹30
      ≥ ₹1000 → ₹20
    eBooks always get ₹0.
    """
    total = float(total_price)
    if total <= 0:
        return 0
    if total < 500:
        return 40
    elif total < 1000:
        return 30
    return 20


# ─── Email Helpers ─────────────────────────────────────────────────────────────

def _send_customer_email(customer_email, customer_name, book_titles,
                          order_type, amount, order_id, estimated_delivery=None):
    """Send order confirmation email to the customer."""
    from django.core.mail import send_mail

    if isinstance(book_titles, list):
        book_list = '\n'.join(f'  • {t}' for t in book_titles)
    else:
        book_list = f'  • {book_titles}'

    order_type_label = 'eBook' if order_type == 'ebook' else 'Physical Book'

    if order_type == 'ebook':
        delivery_section = (
            'Your eBook is now available in your library.\n'
            'Visit https://kavithedal.com/library to read it.'
        )
    else:
        delivery_section = 'Your book will be shipped to your address.'
        if estimated_delivery:
            delivery_section += f'\nEstimated delivery: {estimated_delivery}'

    subject = 'Order Confirmed — Kavithedal Publications'
    message = f"""Dear {customer_name},

Thank you for your purchase! Your payment has been received successfully.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ORDER DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Book(s):
{book_list}

Type    : {order_type_label}
Amount  : ₹{amount}
Order ID: {order_id}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{delivery_section}

View your orders: https://kavithedal.com/user-dashboard

For any queries, contact us at kavithedalpublications@gmail.com

Warm regards,
Kavithedal Publications
"""
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL,
                  [customer_email], fail_silently=False)
    except Exception as exc:
        logger.error('Failed to send customer email to %s: %s', customer_email, exc)


def _send_admin_email_for_purchase(purchase):
    """Send admin notification email for a completed eBook purchase."""
    from django.core.mail import send_mail

    subject = f'New eBook Purchase: {purchase.book.title}'
    message = f"""
New eBook Purchase Details:

Customer Name : {purchase.user_name}
Customer Email: {purchase.email}
Phone         : {purchase.phone}
Address       : {purchase.address}

Book Name     : {purchase.book.title}
Price         : ₹{purchase.price}
Payment Status: {purchase.payment_status}
Order Date    : {purchase.order_date}

Automated notification — Kavithedal Publications.
"""
    admin_email = getattr(settings, 'ADMIN_EMAIL', settings.DEFAULT_FROM_EMAIL)
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL,
                  [admin_email], fail_silently=False)
    except Exception as exc:
        logger.error('Failed to send admin email for purchase %s: %s', purchase.id, exc)


# ─── Permissions ───────────────────────────────────────────────────────────────

class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user or is_authorized_admin(request.user)


# ─── ViewSets (unchanged from original) ───────────────────────────────────────

class OrderViewSet(viewsets.ModelViewSet):
    """ViewSet for Order CRUD operations."""
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if is_authorized_admin(user):
            return Order.objects.all().select_related('book', 'book__author', 'user', 'delivery_zone')
        return Order.objects.filter(user=user).select_related('book', 'book__author', 'delivery_zone')

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def simulate_payment(self, request, pk=None):
        """Simulate payment — only available when Cashfree is NOT configured (local dev)."""
        if _cashfree_configured():
            return Response(
                {'error': 'Payment simulation is not available when Cashfree is configured.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        order = self.get_object()
        if order.status != 'pending':
            return Response(
                {'error': 'Payment already processed or cancelled'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        Payment.objects.create(
            order=order,
            razorpay_order_id=f'simulated_{order.id}',
            razorpay_payment_id=f'simulated_payment_{order.id}',
            amount=order.total_price,
            status='completed',
            payment_method='simulated',
            transaction_id=f'sim_txn_{order.id}',
        )
        order.status = 'completed'
        order.save()
        if order.order_type == 'ebook':
            UserLibrary.objects.get_or_create(
                user=order.user, book=order.book, defaults={'order': order}
            )
        return Response({
            'status': 'Payment successful',
            'order_id': str(order.id),
            'message': 'Payment simulated successfully!',
        })

    # Legacy aliases kept for compatibility
    @action(detail=True, methods=['post'])
    def initiate_payment(self, request, pk=None):
        return self.simulate_payment(request, pk)

    @action(detail=True, methods=['post'])
    def verify_payment(self, request, pk=None):
        return self.simulate_payment(request, pk)


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if is_authorized_admin(user):
            return Payment.objects.all().select_related('order', 'order__book')
        return Payment.objects.filter(order__user=user).select_related('order', 'order__book')


class DeliveryZoneViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DeliveryZoneSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return DeliveryZone.objects.filter(is_active=True)

    @action(detail=False, methods=['get'])
    def by_pincode(self, request):
        pincode = request.query_params.get('pincode')
        if not pincode:
            return Response({'error': 'pincode is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            zone = DeliveryZone.objects.get(pincode=pincode, is_active=True)
            return Response(DeliveryZoneSerializer(zone).data)
        except DeliveryZone.DoesNotExist:
            return Response({
                'pincode': pincode, 'city': 'Unknown', 'state': 'Unknown',
                'zone_type': 'national', 'delivery_charge': '100.00',
                'min_delivery_days': 5, 'max_delivery_days': 10,
                'delivery_time': '5-10 Days', 'is_active': True,
                'message': 'Delivery available with standard charges',
            })

    @action(detail=False, methods=['post'])
    def calculate_delivery(self, request):
        pincode = (request.data.get('pincode') or '').strip()
        book_price = float(request.data.get('book_price', 0) or 0)
        delivery_charge = calculate_delivery_charge(book_price)

        if pincode.startswith('636'):
            min_days, max_days = 2, 3
        elif pincode.startswith('600'):
            min_days, max_days = 3, 5
        else:
            min_days, max_days = 5, 7

        estimated_date = date.today() + timedelta(days=max_days)
        return Response({
            'pincode': pincode,
            'delivery_charge': delivery_charge,
            'book_price': book_price,
            'total_price': book_price + delivery_charge,
            'min_delivery_days': min_days,
            'max_delivery_days': max_days,
            'estimated_delivery_date': estimated_date.strftime('%Y-%m-%d'),
            'message': 'Delivery charge calculated successfully',
        })


class UserLibraryViewSet(viewsets.ModelViewSet):
    serializer_class = UserLibrarySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserLibrary.objects.filter(
            user=self.request.user
        ).select_related('book', 'book__author', 'order')

    def get_serializer_class(self):
        if self.action == 'list':
            return UserLibraryListSerializer
        return UserLibrarySerializer

    @action(detail=False, methods=['get'])
    def check_access(self, request):
        book_id = request.query_params.get('book_id')
        if not book_id:
            return Response({'error': 'book_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        has_access = UserLibrary.objects.filter(
            user=request.user, book_id=book_id
        ).exists()
        return Response({'has_access': has_access, 'book_id': book_id})


# ─── Cashfree Payment Views ────────────────────────────────────────────────────

class CreateOrderView(APIView):
    """
    Create a Cashfree payment order for a single physical or ebook purchase.
    Called by PhysicalPurchase.jsx.

    Simulation mode (no Cashfree keys): auto-completes the order instantly.
    Production mode: returns payment_session_id for Cashfree JS SDK.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        book_id = request.data.get('book_id')
        order_type = request.data.get('order_type', 'physical')

        if not book_id:
            return Response({'error': 'book_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        from apps.books.models import Book
        try:
            book = Book.objects.get(id=book_id, is_active=True)
        except Book.DoesNotExist:
            return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)

        if order_type == 'ebook' and UserLibrary.objects.filter(
            user=request.user, book=book
        ).exists():
            return Response(
                {'error': 'You already own this eBook'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if order_type == 'ebook':
            unit_price = book.ebook_price
            if not unit_price:
                return Response({'error': 'eBook price not set'}, status=status.HTTP_400_BAD_REQUEST)
            delivery_charge = 0
            total_price = float(unit_price)
        else:
            unit_price = book.physical_price or book.price
            if not unit_price:
                return Response({'error': 'Physical book price not set'}, status=status.HTTP_400_BAD_REQUEST)
            delivery_charge = calculate_delivery_charge(float(unit_price))
            total_price = float(unit_price) + delivery_charge

        shipping_pincode = request.data.get('shipping_pincode', '')
        estimated_delivery_date = None
        if order_type == 'physical' and shipping_pincode:
            max_days = (3 if shipping_pincode.startswith('636')
                        else 5 if shipping_pincode.startswith('600') else 7)
            estimated_delivery_date = date.today() + timedelta(days=max_days)

        order = Order.objects.create(
            user=request.user,
            book=book,
            order_type=order_type,
            quantity=1,
            book_price=unit_price,
            delivery_charge=delivery_charge,
            total_price=total_price,
            status='processing',
            delivery_status='pending',
            payment_status='pending',
            full_name=request.data.get('full_name', ''),
            email=request.data.get('email', ''),
            phone=request.data.get('phone', ''),
            shipping_address=request.data.get('shipping_address', ''),
            shipping_city=request.data.get('shipping_city', ''),
            shipping_state=request.data.get('shipping_state', ''),
            shipping_pincode=shipping_pincode,
            estimated_delivery_date=estimated_delivery_date,
        )

        if not _cashfree_configured():
            # ── Simulation mode (local dev without Cashfree keys) ──────────────
            Payment.objects.create(
                order=order,
                razorpay_order_id=f'sim_{order.id}',
                razorpay_payment_id=f'sim_pay_{order.id}',
                amount=total_price,
                status='completed',
                payment_method='simulated',
                transaction_id=f'sim_txn_{order.id}',
            )
            order.status = 'completed'
            order.payment_status = 'paid'
            order.save()
            if order_type == 'ebook':
                UserLibrary.objects.get_or_create(
                    user=request.user, book=book, defaults={'order': order}
                )
            return Response({
                'order_id': str(order.id),
                'status': 'completed',
                'purchased': True,
                'book_title': book.title,
                'book_cover': book.cover_image.url if book.cover_image else None,
                'delivery_charge': delivery_charge,
                'total_price': total_price,
                'estimated_delivery_date': (
                    estimated_delivery_date.strftime('%Y-%m-%d')
                    if estimated_delivery_date else None
                ),
            })

        # ── Cashfree payment order ──────────────────────────────────────────────
        prefix = 'eb' if order_type == 'ebook' else 'ph'
        cf_order_id = _cf_make_order_id(prefix, order.id)
        return_url = (
            f"{settings.FRONTEND_URL}/payment-success"
            f"?order_id={cf_order_id}&type={order_type}"
        )
        try:
            cf_data = _cf_create_order(
                cf_order_id=cf_order_id,
                amount=total_price,
                customer_id=str(request.user.pk)[:50],
                customer_email=request.data.get('email') or request.user.email,
                customer_phone=request.data.get('phone', '9999999999'),
                return_url=return_url,
                note=book.title,
            )
        except Exception as exc:
            logger.error('Cashfree create order failed for order %s: %s', order.id, exc)
            order.delete()
            return Response(
                {'error': 'Payment gateway error. Please try again.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Store Cashfree order ID on the Order record for later lookup
        order.razorpay_order_id = cf_order_id
        order.save(update_fields=['razorpay_order_id'])

        return Response({
            'order_id': str(order.id),
            'payment_session_id': cf_data.get('payment_session_id', ''),
            'cashfree_order_id': cf_order_id,
            'amount': total_price,
            'book_title': book.title,
            'book_cover': book.cover_image.url if book.cover_image else None,
            'delivery_charge': delivery_charge,
            'estimated_delivery_date': (
                estimated_delivery_date.strftime('%Y-%m-%d')
                if estimated_delivery_date else None
            ),
        })


class EbookPurchaseView(APIView):
    """
    Create a Cashfree payment order for dedicated eBook checkout.
    Called by EbookPurchase.jsx (collects user_name, phone, address).

    Simulation mode: auto-completes and adds book to library.
    Production mode: returns payment_session_id for Cashfree JS SDK.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        book_id = request.data.get('book_id')
        user_name = request.data.get('user_name', '').strip()
        email = request.data.get('email', request.user.email).strip()
        phone = request.data.get('phone', '').strip()
        address = request.data.get('address', '').strip()

        if not all([book_id, user_name, email, phone, address]):
            return Response(
                {'error': 'All fields are required: book_id, user_name, email, phone, address'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.books.models import Book
        try:
            book = Book.objects.get(id=book_id, is_active=True)
        except Book.DoesNotExist:
            return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)

        if UserLibrary.objects.filter(user=request.user, book=book).exists():
            return Response(
                {'error': 'You already own this eBook'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        unit_price = book.ebook_price
        if not unit_price:
            return Response({'error': 'eBook price not set'}, status=status.HTTP_400_BAD_REQUEST)

        purchase = EbookPurchase.objects.create(
            user=request.user,
            book=book,
            user_name=user_name,
            email=email,
            phone=phone,
            address=address,
            price=unit_price,
            payment_status='initiated',
        )

        if not _cashfree_configured():
            # ── Simulation mode ────────────────────────────────────────────────
            purchase.payment_status = 'completed'
            purchase.transaction_id = f'sim_{purchase.id}'
            purchase.save()
            UserLibrary.objects.get_or_create(user=request.user, book=book)
            _send_admin_email_for_purchase(purchase)
            return Response({
                'purchase_id': str(purchase.id),
                'status': 'completed',
                'book_title': book.title,
            })

        # ── Cashfree payment order ──────────────────────────────────────────────
        cf_order_id = _cf_make_order_id('eb', purchase.id)
        return_url = (
            f"{settings.FRONTEND_URL}/payment-success"
            f"?order_id={cf_order_id}&type=ebook"
        )
        try:
            cf_data = _cf_create_order(
                cf_order_id=cf_order_id,
                amount=float(unit_price),
                customer_id=str(request.user.pk)[:50],
                customer_email=email,
                customer_phone=phone,
                return_url=return_url,
                note=book.title,
            )
        except Exception as exc:
            logger.error('Cashfree ebook order creation failed for purchase %s: %s', purchase.id, exc)
            purchase.delete()
            return Response(
                {'error': 'Payment gateway error. Please try again.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        purchase.razorpay_order_id = cf_order_id
        purchase.save(update_fields=['razorpay_order_id'])

        return Response({
            'purchase_id': str(purchase.id),
            'payment_session_id': cf_data.get('payment_session_id', ''),
            'cashfree_order_id': cf_order_id,
            'amount': float(unit_price),
            'book_title': book.title,
            'book_cover': book.cover_image.url if book.cover_image else None,
        })


class CartCheckoutView(APIView):
    """
    Create a Cashfree payment order for multi-item cart checkout.
    Cart items are stored server-side in CartCheckoutSession so they cannot
    be tampered with by the user after the Cashfree redirect.

    Simulation mode: creates orders directly without Cashfree.
    Production mode: returns payment_session_id for Cashfree JS SDK.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        items = request.data.get('items', [])
        total_amount = float(request.data.get('total_amount', 0) or 0)

        if not items:
            return Response({'error': 'No items in cart'}, status=status.HTTP_400_BAD_REQUEST)
        if total_amount <= 0:
            return Response({'error': 'Invalid total amount'}, status=status.HTTP_400_BAD_REQUEST)

        session_uuid = uuid.uuid4()
        cf_order_id = _cf_make_order_id('ct', session_uuid)

        if not _cashfree_configured():
            # ── Simulation mode ────────────────────────────────────────────────
            return self._simulate_cart(request, items, total_amount, session_uuid)

        # Store items server-side before redirecting to Cashfree
        CartCheckoutSession.objects.create(
            id=session_uuid,
            user=request.user,
            cashfree_order_id=cf_order_id,
            items=items,
            total_amount=total_amount,
        )

        return_url = (
            f"{settings.FRONTEND_URL}/payment-success"
            f"?order_id={cf_order_id}&type=cart"
        )
        try:
            cf_data = _cf_create_order(
                cf_order_id=cf_order_id,
                amount=total_amount,
                customer_id=str(request.user.pk)[:50],
                customer_email=request.user.email,
                customer_phone=request.data.get('phone', '9999999999'),
                return_url=return_url,
                note=f'{len(items)} book(s)',
            )
        except Exception as exc:
            CartCheckoutSession.objects.filter(id=session_uuid).delete()
            logger.error('Cashfree cart order creation failed: %s', exc)
            return Response(
                {'error': 'Payment gateway error. Please try again.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({
            'payment_session_id': cf_data.get('payment_session_id', ''),
            'cashfree_order_id': cf_order_id,
            'amount': total_amount,
        })

    def _simulate_cart(self, request, items, total_amount, session_uuid):
        """Create orders directly (dev mode — no Cashfree configured)."""
        from apps.books.models import Book

        physical_total = sum(
            float(i.get('price', 0)) * int(i.get('qty', 1))
            for i in items if i.get('book_type', 'physical') != 'ebook'
        )
        total_delivery = calculate_delivery_charge(physical_total)
        delivery_assigned = False
        created_orders = []

        for item in items:
            try:
                book = Book.objects.get(id=item['book_id'])
                item_delivery = 0
                if item.get('book_type', 'physical') != 'ebook' and not delivery_assigned:
                    item_delivery = total_delivery
                    delivery_assigned = True
                item_total = float(item.get('price', 0)) * int(item.get('qty', 1)) + item_delivery

                order = Order.objects.create(
                    user=request.user, book=book,
                    order_type=item.get('book_type', 'physical'),
                    quantity=item.get('qty', 1),
                    book_price=item.get('price', 0),
                    delivery_charge=item_delivery,
                    total_price=item_total,
                    status='completed', delivery_status='pending', payment_status='paid',
                    razorpay_order_id=f'sim_{session_uuid}',
                    razorpay_payment_id=f'sim_pay_{session_uuid}',
                    transaction_id=f'sim_txn_{session_uuid}',
                    full_name=request.user.get_full_name() or '',
                    email=request.user.email,
                )
                Payment.objects.create(
                    order=order,
                    razorpay_order_id=f'sim_{session_uuid}',
                    razorpay_payment_id=f'sim_pay_{session_uuid}',
                    amount=item_total, status='completed',
                    payment_method='simulated',
                    transaction_id=f'sim_txn_{session_uuid}',
                )
                if order.order_type == 'ebook':
                    UserLibrary.objects.get_or_create(
                        user=request.user, book=book, defaults={'order': order}
                    )
                created_orders.append(str(order.id))
            except Book.DoesNotExist:
                continue

        return Response({
            'status': 'completed',
            'message': f'{len(created_orders)} order(s) created successfully',
            'order_ids': created_orders,
        })


class CashfreeVerifyPaymentView(APIView):
    """
    Called from /payment-success page after Cashfree redirects the user back.

    GET /api/orders/verify-cashfree-payment/?order_id=kv-eb-xxxxx

    Verifies the order status via the Cashfree API, then marks purchases
    as completed and (for eBooks) adds the book to UserLibrary.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cf_order_id = request.query_params.get('order_id', '').strip()
        if not cf_order_id:
            return Response(
                {'error': 'order_id query param is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not _cashfree_configured():
            return self._sim_verify(request, cf_order_id)

        # ── Verify with Cashfree API ───────────────────────────────────────────
        try:
            cf_order = _cf_get_order(cf_order_id)
        except http_requests.HTTPError as exc:
            logger.error('Cashfree order lookup failed for %s: %s', cf_order_id, exc)
            return Response(
                {'error': 'Failed to verify payment. Please try again.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        cf_status = cf_order.get('order_status', '')
        if cf_status != 'PAID':
            logger.info('Cashfree order %s status=%s (not PAID)', cf_order_id, cf_status)
            return Response({
                'paid': False,
                'status': cf_status,
                'message': 'Payment not completed. If you paid, please wait a moment and refresh.',
            })

        # Extract payment ID from Cashfree payments sub-array
        cf_payments = cf_order.get('payments', []) or []
        cf_payment_id = str(cf_payments[0].get('cf_payment_id', '')) if cf_payments else ''

        return self._complete_purchase(request, cf_order_id, cf_payment_id)

    # ── Private helpers ────────────────────────────────────────────────────────

    def _sim_verify(self, request, cf_order_id):
        """Return success for sim orders (Cashfree not configured)."""
        try:
            p = EbookPurchase.objects.get(user=request.user, razorpay_order_id=cf_order_id)
            return Response({'paid': True, 'status': 'PAID', 'purchase_type': 'ebook',
                             'book_title': p.book.title, 'purchase_id': str(p.id)})
        except EbookPurchase.DoesNotExist:
            pass
        try:
            o = Order.objects.get(user=request.user, razorpay_order_id=cf_order_id)
            return Response({'paid': True, 'status': 'PAID',
                             'purchase_type': o.order_type, 'book_title': o.book.title})
        except Order.DoesNotExist:
            pass
        try:
            CartCheckoutSession.objects.get(user=request.user, cashfree_order_id=cf_order_id)
            return Response({'paid': True, 'status': 'PAID', 'purchase_type': 'cart'})
        except CartCheckoutSession.DoesNotExist:
            pass
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

    def _complete_purchase(self, request, cf_order_id, cf_payment_id):
        """Mark the matching purchase as paid and grant ebook access."""

        # 1. EbookPurchase (via EbookPurchaseView)
        try:
            purchase = EbookPurchase.objects.get(
                user=request.user, razorpay_order_id=cf_order_id
            )
            if purchase.payment_status != 'completed':
                with transaction.atomic():
                    purchase.payment_status = 'completed'
                    purchase.razorpay_payment_id = cf_payment_id
                    purchase.transaction_id = cf_payment_id
                    purchase.save()
                    UserLibrary.objects.get_or_create(user=request.user, book=purchase.book)
                    _send_admin_email_for_purchase(purchase)
                    _send_customer_email(
                        customer_email=purchase.email,
                        customer_name=purchase.user_name,
                        book_titles=purchase.book.title,
                        order_type='ebook',
                        amount=float(purchase.price),
                        order_id=str(purchase.id),
                    )
            return Response({
                'paid': True, 'status': 'PAID', 'purchase_type': 'ebook',
                'book_title': purchase.book.title, 'purchase_id': str(purchase.id),
            })
        except EbookPurchase.DoesNotExist:
            pass

        # 2. Order (via CreateOrderView — physical or ebook)
        try:
            order = Order.objects.get(
                user=request.user, razorpay_order_id=cf_order_id
            )
            if order.payment_status != 'paid':
                with transaction.atomic():
                    Payment.objects.create(
                        order=order,
                        razorpay_order_id=cf_order_id,
                        razorpay_payment_id=cf_payment_id,
                        amount=order.total_price,
                        status='completed',
                        payment_method='cashfree',
                        transaction_id=cf_payment_id,
                    )
                    order.payment_status = 'paid'
                    order.status = 'completed'
                    order.razorpay_payment_id = cf_payment_id
                    order.transaction_id = cf_payment_id
                    order.save()
                    if order.order_type == 'ebook':
                        UserLibrary.objects.get_or_create(
                            user=request.user, book=order.book, defaults={'order': order}
                        )
                    _send_customer_email(
                        customer_email=order.email or request.user.email,
                        customer_name=order.full_name or request.user.email,
                        book_titles=order.book.title,
                        order_type=order.order_type,
                        amount=float(order.total_price),
                        order_id=str(order.id),
                        estimated_delivery=(
                            order.estimated_delivery_date.strftime('%d %b %Y')
                            if order.estimated_delivery_date else None
                        ),
                    )
            return Response({
                'paid': True, 'status': 'PAID',
                'purchase_type': order.order_type,
                'book_title': order.book.title, 'order_id': str(order.id),
            })
        except Order.DoesNotExist:
            pass

        # 3. CartCheckoutSession (via CartCheckoutView)
        try:
            cart_session = CartCheckoutSession.objects.get(
                user=request.user, cashfree_order_id=cf_order_id
            )
            if cart_session.status != 'completed':
                self._complete_cart(request, cart_session, cf_order_id, cf_payment_id)
            return Response({'paid': True, 'status': 'PAID', 'purchase_type': 'cart'})
        except CartCheckoutSession.DoesNotExist:
            pass

        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

    def _complete_cart(self, request, cart_session, cf_order_id, cf_payment_id):
        """Create Order records from a cart session after Cashfree confirms payment."""
        from apps.books.models import Book

        items = cart_session.items
        physical_total = sum(
            float(i.get('price', 0)) * int(i.get('qty', 1))
            for i in items if i.get('book_type', 'physical') != 'ebook'
        )
        total_delivery = calculate_delivery_charge(physical_total)
        delivery_assigned = False
        book_titles = []

        with transaction.atomic():
            for item in items:
                try:
                    book = Book.objects.get(id=item['book_id'])
                    item_delivery = 0
                    if item.get('book_type', 'physical') != 'ebook' and not delivery_assigned:
                        item_delivery = total_delivery
                        delivery_assigned = True
                    item_total = float(item.get('price', 0)) * int(item.get('qty', 1)) + item_delivery

                    order = Order.objects.create(
                        user=request.user, book=book,
                        order_type=item.get('book_type', 'physical'),
                        quantity=item.get('qty', 1),
                        book_price=item.get('price', 0),
                        delivery_charge=item_delivery,
                        total_price=item_total,
                        status='completed', delivery_status='pending', payment_status='paid',
                        razorpay_order_id=cf_order_id,
                        razorpay_payment_id=cf_payment_id,
                        transaction_id=cf_payment_id,
                        full_name=request.user.get_full_name() or '',
                        email=request.user.email,
                    )
                    Payment.objects.create(
                        order=order,
                        razorpay_order_id=cf_order_id,
                        razorpay_payment_id=cf_payment_id,
                        amount=item_total,
                        status='completed',
                        payment_method='cashfree',
                        transaction_id=cf_payment_id,
                    )
                    if order.order_type == 'ebook':
                        UserLibrary.objects.get_or_create(
                            user=request.user, book=book, defaults={'order': order}
                        )
                    book_titles.append(book.title)
                except Book.DoesNotExist:
                    continue

            cart_session.status = 'completed'
            cart_session.save(update_fields=['status'])

        _send_customer_email(
            customer_email=request.user.email,
            customer_name=request.user.get_full_name() or request.user.email,
            book_titles=book_titles,
            order_type='physical',
            amount=float(cart_session.total_amount),
            order_id=cf_payment_id,
        )


class CalculateDeliveryView(APIView):
    """Public endpoint — calculate delivery charge for a given physical books total."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        items_total = request.data.get('items_total', 0)
        try:
            items_total = float(items_total)
        except (TypeError, ValueError):
            return Response(
                {'error': 'items_total must be a number'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        delivery_charge = calculate_delivery_charge(items_total)
        return Response({
            'items_total': round(items_total, 2),
            'delivery_charge': delivery_charge,
            'final_total': round(items_total + delivery_charge, 2),
        })


# ─── Cashfree Webhook ──────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class CashfreeWebhookView(APIView):
    """
    Cashfree Webhook endpoint — registered in Cashfree dashboard.
    URL: /api/payment/webhook/

    Verifies the x-webhook-signature header (HMAC-SHA256, base64-encoded)
    using CASHFREE_SECRET_KEY before processing any event.

    Events:
      PAYMENT_SUCCESS_WEBHOOK — mark purchase paid, add ebooks to library
      PAYMENT_FAILED_WEBHOOK  — mark purchase failed
    """
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        secret = getattr(settings, 'CASHFREE_SECRET_KEY', '')
        if not secret:
            logger.error('CashfreeWebhookView: CASHFREE_SECRET_KEY not configured')
            return Response(
                {'error': 'Webhook not configured'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ── Signature verification ─────────────────────────────────────────────
        timestamp = request.headers.get('x-webhook-timestamp', '')
        signature = request.headers.get('x-webhook-signature', '')

        if not timestamp or not signature:
            logger.warning('CashfreeWebhookView: missing signature headers')
            return Response({'error': 'Missing signature'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            raw_body = request.body.decode('utf-8')
            message = timestamp + raw_body
            expected_sig = base64.b64encode(
                hmac.new(secret.encode(), message.encode(), hashlib.sha256).digest()
            ).decode()
            if not hmac.compare_digest(expected_sig, signature):
                logger.warning('CashfreeWebhookView: signature mismatch — possible spoofed request')
                return Response({'error': 'Invalid signature'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.error('CashfreeWebhookView: signature error: %s', exc)
            return Response({'error': 'Signature error'}, status=status.HTTP_400_BAD_REQUEST)

        # ── Parse payload ──────────────────────────────────────────────────────
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return Response({'error': 'Invalid JSON'}, status=status.HTTP_400_BAD_REQUEST)

        event = payload.get('type', '')
        data = payload.get('data', {})
        order_data = data.get('order', {})
        payment_data = data.get('payment', {})

        cf_order_id = order_data.get('order_id', '')
        cf_payment_id = str(payment_data.get('cf_payment_id', ''))
        payment_status_val = payment_data.get('payment_status', '')

        logger.info(
            'CashfreeWebhookView: event=%s order=%s payment=%s payment_status=%s',
            event, cf_order_id, cf_payment_id, payment_status_val,
        )

        is_success = event == 'PAYMENT_SUCCESS_WEBHOOK' or payment_status_val == 'SUCCESS'
        is_failure = event == 'PAYMENT_FAILED_WEBHOOK' or payment_status_val == 'FAILED'

        if is_success and cf_order_id:
            with transaction.atomic():
                # Update EbookPurchase records
                for ep in EbookPurchase.objects.filter(
                    razorpay_order_id=cf_order_id, payment_status='initiated'
                ).select_related('user', 'book'):
                    ep.payment_status = 'completed'
                    ep.razorpay_payment_id = cf_payment_id
                    ep.transaction_id = cf_payment_id
                    ep.save(update_fields=['payment_status', 'razorpay_payment_id', 'transaction_id'])
                    UserLibrary.objects.get_or_create(user=ep.user, book=ep.book)

                # Update Order records
                for order in Order.objects.filter(
                    razorpay_order_id=cf_order_id, payment_status='pending'
                ).select_related('user', 'book'):
                    order.payment_status = 'paid'
                    order.status = 'completed'
                    order.razorpay_payment_id = cf_payment_id
                    order.transaction_id = cf_payment_id
                    order.save(update_fields=[
                        'payment_status', 'status', 'razorpay_payment_id', 'transaction_id'
                    ])
                    if order.order_type == 'ebook':
                        UserLibrary.objects.get_or_create(
                            user=order.user, book=order.book, defaults={'order': order}
                        )

            logger.info('CashfreeWebhookView: PAYMENT_SUCCESS processed for order %s', cf_order_id)

        elif is_failure and cf_order_id:
            with transaction.atomic():
                EbookPurchase.objects.filter(
                    razorpay_order_id=cf_order_id, payment_status='initiated'
                ).update(payment_status='failed')
                Order.objects.filter(
                    razorpay_order_id=cf_order_id, payment_status='pending'
                ).update(payment_status='failed', status='cancelled')

            logger.info('CashfreeWebhookView: PAYMENT_FAILED processed for order %s', cf_order_id)

        # Always return 200 — Cashfree retries on non-2xx
        return Response({'status': 'ok'})
