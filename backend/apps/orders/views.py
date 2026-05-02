"""
Views for Orders App — Cashfree payment integration.
"""
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

# ============= CASHFREE UTILITY FUNCTIONS =============

def _cashfree_configured():
    """Return True when Cashfree credentials are set in env."""
    return bool(
        getattr(settings, 'CASHFREE_APP_ID', '') and
        getattr(settings, 'CASHFREE_SECRET_KEY', '')
    )


def _cashfree_headers():
    """Get Cashfree API headers."""
    return {
        'x-api-version': '2023-08-01',
        'Content-Type': 'application/json',
        'x-client-id': getattr(settings, 'CASHFREE_APP_ID', ''),
        'x-client-secret': getattr(settings, 'CASHFREE_SECRET_KEY', ''),
    }


def _cf_create_order(order_id, amount, customer_details, return_url):
    """
    Create a Cashfree payment order.
    
    Args:
        order_id: Unique order identifier
        amount: Amount to charge
        customer_details: Dict with customer_id, name, email, phone
        return_url: URL to redirect after payment
    
    Returns:
        dict with payment_session_id or error
    """
    base_url = getattr(settings, 'CASHFREE_BASE_URL', 'https://sandbox.cashfree.com/pg')
    url = f"{base_url}/orders"
    
    payload = {
        'order_id': str(order_id),
        'order_amount': float(amount),
        'order_currency': 'INR',
        'customer_details': customer_details,
        'order_meta': {
            'return_url': return_url,
            'notify_url': f"{settings.BACKEND_URL}/api/payment/webhook/"
        }
    }
    
    try:
        response = http_requests.post(url, json=payload, headers=_cashfree_headers())
        response.raise_for_status()
        data = response.json()
        logger.info(f"Cashfree order created: order_id={order_id}, cf_order_id={data.get('cf_order_id')}")
        return data
    except http_requests.exceptions.RequestException as e:
        logger.error(f"Cashfree order creation failed: {e}")
        return {'error': str(e)}


def _cf_get_order(order_id):
    """Get Cashfree order status."""
    base_url = getattr(settings, 'CASHFREE_BASE_URL', 'https://sandbox.cashfree.com/pg')
    url = f"{base_url}/orders/{order_id}"
    
    try:
        response = http_requests.get(url, headers=_cashfree_headers())
        response.raise_for_status()
        return response.json()
    except http_requests.exceptions.RequestException as e:
        logger.error(f"Cashfree get order failed: {e}")
        return None


def _generate_order_id(prefix, uid):
    """Generate a unique order ID for Cashfree."""
    hex_part = str(uid).replace('-', '')[:20]
    return f'kv-{prefix}-{hex_part}'


def _normalize_phone(phone):
    """Normalize phone number for Cashfree."""
    phone = str(phone).strip().replace(' ', '').replace('-', '').replace('+', '')
    if phone.startswith('91') and len(phone) == 12:
        phone = phone[2:]
    return phone[:10] or '9999999999'


# ============= PAYMENT HELPERS =============

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


# ============= EMAIL HELPERS =============

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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ORDER DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Book(s):
{book_list}

Type    : {order_type_label}
Amount  : ₹{amount}
Order ID: {order_id}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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


# ============= PERMISSIONS =============

class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user or is_authorized_admin(request.user)


# ============= VIEWSETS =============

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
            cashfree_order_id=f'sim_{order.id}',
            cashfree_payment_id=f'sim_pay_{order.id}',
            amount=order.total_price,
            status='completed',
            payment_method='simulated',
            transaction_id=f'sim_txn_{order.id}',
        )
        order.status = 'completed'
        order.payment_status = 'paid'
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


# ============= CASHFREE PAYMENT VIEWS =============

class CreateOrderView(APIView):
    """
    Create a Cashfree payment order for a single physical or ebook purchase.

    Simulation mode (no Cashfree keys): auto-completes the order instantly.
    Production mode: returns Cashfree payment_session_id for SDK checkout.

    POST /api/orders/create-order/
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

        # Calculate price
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

        # Estimate delivery for physical books
        shipping_pincode = request.data.get('shipping_pincode', '')
        estimated_delivery_date = None
        if order_type == 'physical' and shipping_pincode:
            max_days = (3 if shipping_pincode.startswith('636')
                        else 5 if shipping_pincode.startswith('600') else 7)
            estimated_delivery_date = date.today() + timedelta(days=max_days)

        # Create Order record
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

        # Simulation mode (local dev without Cashfree keys)
        if not _cashfree_configured():
            Payment.objects.create(
                order=order,
                cashfree_order_id=f'sim_{order.id}',
                cashfree_payment_id=f'sim_pay_{order.id}',
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

        # Production: Create Cashfree order
        cf_order_id = _generate_order_id('ord', order.id)

        customer_details = {
            'customer_id': str(request.user.id),
            'customer_name': request.data.get('full_name', request.user.get_full_name() or 'Customer'),
            'customer_email': request.data.get('email', request.user.email),
            'customer_phone': _normalize_phone(request.data.get('phone', request.user.phone or '9999999999')),
        }

        success_url = (
            f"{settings.FRONTEND_URL}/payment-success"
            f"?order_id={cf_order_id}&type={order_type}"
        )

        cf_response = _cf_create_order(
            order_id=cf_order_id,
            amount=total_price,
            customer_details=customer_details,
            return_url=success_url
        )

        if 'error' in cf_response:
            return Response(
                {'error': f"Failed to create Cashfree order: {cf_response['error']}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        payment_session_id = cf_response.get('payment_session_id')
        if not payment_session_id:
            return Response(
                {'error': 'No payment session ID received from Cashfree'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Store Cashfree order ID on Order record
        order.cashfree_order_id = cf_order_id
        order.save(update_fields=['cashfree_order_id'])

        # Return Cashfree payment parameters
        return Response({
            'order_id': str(order.id),
            'cashfree_order_id': cf_order_id,
            'payment_session_id': payment_session_id,
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
    Collects user_name, phone, address before initiating payment.

    Simulation mode: auto-completes and adds book to library.
    Production mode: returns Cashfree payment_session_id.

    POST /api/orders/ebook-purchase/
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

        # Create EbookPurchase record
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

        # Simulation mode
        if not _cashfree_configured():
            purchase.payment_status = 'completed'
            purchase.transaction_id = f'sim_{purchase.id}'
            purchase.cashfree_order_id = f'sim_{purchase.id}'
            purchase.save()
            UserLibrary.objects.get_or_create(user=request.user, book=book, defaults={'order': None})
            _send_admin_email_for_purchase(purchase)
            return Response({
                'purchase_id': str(purchase.id),
                'status': 'completed',
                'book_title': book.title,
            })

        # Production: Create Cashfree order
        cf_order_id = _generate_order_id('eb', purchase.id)

        customer_details = {
            'customer_id': str(request.user.id),
            'customer_name': user_name,
            'customer_email': email,
            'customer_phone': _normalize_phone(phone),
        }

        success_url = (
            f"{settings.FRONTEND_URL}/payment-success"
            f"?order_id={cf_order_id}&type=ebook"
        )

        cf_response = _cf_create_order(
            order_id=cf_order_id,
            amount=float(unit_price),
            customer_details=customer_details,
            return_url=success_url
        )

        if 'error' in cf_response:
            return Response(
                {'error': f"Failed to create Cashfree order: {cf_response['error']}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        payment_session_id = cf_response.get('payment_session_id')
        if not payment_session_id:
            return Response(
                {'error': 'No payment session ID received from Cashfree'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Store Cashfree order ID
        purchase.cashfree_order_id = cf_order_id
        purchase.save(update_fields=['cashfree_order_id'])

        return Response({
            'purchase_id': str(purchase.id),
            'cashfree_order_id': cf_order_id,
            'payment_session_id': payment_session_id,
            'amount': float(unit_price),
            'book_title': book.title,
            'book_cover': book.cover_image.url if book.cover_image else None,
        })


class CartCheckoutView(APIView):
    """
    Create a Cashfree payment order for multi-item cart checkout.
    Items are stored server-side for tamper-proofing.

    Simulation mode: creates orders directly without Cashfree.
    Production mode: returns Cashfree payment_session_id.

    POST /api/orders/cart-checkout/
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
        cf_order_id = _generate_order_id('ct', session_uuid)

        # Simulation mode
        if not _cashfree_configured():
            return self._simulate_cart(request, items, total_amount, session_uuid)

        # Store items server-side
        CartCheckoutSession.objects.create(
            id=session_uuid,
            user=request.user,
            cashfree_order_id=cf_order_id,
            items=items,
            total_amount=total_amount,
            status='pending',
        )

        customer_details = {
            'customer_id': str(request.user.id),
            'customer_name': request.user.get_full_name() or 'Customer',
            'customer_email': request.user.email,
            'customer_phone': _normalize_phone(request.data.get('phone', '9999999999')),
        }

        success_url = (
            f"{settings.FRONTEND_URL}/payment-success"
            f"?order_id={cf_order_id}&type=cart"
        )

        cf_response = _cf_create_order(
            order_id=cf_order_id,
            amount=total_amount,
            customer_details=customer_details,
            return_url=success_url
        )

        if 'error' in cf_response:
            return Response(
                {'error': f"Failed to create Cashfree order: {cf_response['error']}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        payment_session_id = cf_response.get('payment_session_id')
        if not payment_session_id:
            return Response(
                {'error': 'No payment session ID received from Cashfree'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            'cashfree_order_id': cf_order_id,
            'payment_session_id': payment_session_id,
            'amount': total_amount,
            'session_id': str(session_uuid),
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

        # Generate a fake Cashfree order ID for simulation
        cf_order_id = f"sim_{session_uuid.hex[:12]}"

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
                    cashfree_order_id=cf_order_id,
                    cashfree_payment_id=f'sim_pay_{session_uuid.hex[:8]}',
                    transaction_id=f'sim_txn_{session_uuid.hex[:12]}',
                    full_name=request.user.get_full_name() or '',
                    email=request.user.email,
                )
                Payment.objects.create(
                    order=order,
                    cashfree_order_id=cf_order_id,
                    cashfree_payment_id=f'sim_pay_{session_uuid.hex[:8]}',
                    amount=item_total, status='completed',
                    payment_method='simulated',
                    transaction_id=f'sim_txn_{session_uuid.hex[:12]}',
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
            'cashfree_order_id': cf_order_id,
        })


# ============= CASHFREE PAYMENT VERIFICATION =============

class CashfreeVerifyPaymentView(APIView):
    """
    Verify Cashfree payment and update order status.
    Handles both:
      - Frontend verification (POST from authenticated user after redirect)
      - Webhook notifications (POST from Cashfree servers with signature)
    
    POST /api/orders/verify-cashfree-payment/  (frontend)
    POST /api/payment/webhook/                 (webhook)
    """
    permission_classes = [permissions.AllowAny]  # Allows both authenticated and unauthenticated (webhook)

    def post(self, request):
        # ── Determine request source: webhook vs frontend verification ─────────────
        signature = request.headers.get('x-cashfree-signature') or request.headers.get('X-Cashfree-Signature')
        is_webhook = False
        if signature:
            # Verify Cashfree webhook signature
            secret = getattr(settings, 'CASHFREE_WEBHOOK_SECRET', '')
            if not secret:
                logger.error("Cashfree webhook secret not configured")
                return Response({'error': 'Server misconfigured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            body = request.body
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                body,
                hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected_signature):
                logger.warning("Cashfree webhook signature mismatch")
                return Response({'error': 'Invalid signature'}, status=status.HTTP_403_FORBIDDEN)
            is_webhook = True
        else:
            # Frontend verification — require authentication
            if not request.user.is_authenticated:
                return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        order_id = request.data.get('order_id')
        if not order_id:
            return Response({'error': 'order_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        # For Cashfree, verify by checking the order status via API
        cf_order = _cf_get_order(order_id)
        if not cf_order:
            return Response({'error': 'Order not found in Cashfree'}, status=status.HTTP_404_NOT_FOUND)

        payment_status = cf_order.get('payment_status', '').upper()
        is_success = payment_status == 'SUCCESS'

        return self._process_payment(order_id, is_success, cf_order, is_webhook=is_webhook)

    def _process_payment(self, cf_order_id, is_success, cf_data, is_webhook=False):
        """
        Update EbookPurchase, Order, or CartCheckoutSession based on Cashfree confirmation.
        """
        try:
            cf_payment_id = cf_data.get('cf_payment_id', '')

            if is_success:
                # 1. EbookPurchase
                try:
                    purchase = EbookPurchase.objects.get(
                        cashfree_order_id=cf_order_id,
                        payment_status='initiated'
                    )
                    with transaction.atomic():
                        purchase.payment_status = 'completed'
                        purchase.cashfree_payment_id = cf_payment_id
                        purchase.transaction_id = cf_payment_id
                        purchase.save(update_fields=['payment_status', 'cashfree_payment_id', 'transaction_id'])

                        # Add to user library
                        UserLibrary.objects.get_or_create(
                            user=purchase.user, book=purchase.book, defaults={'order': None}
                        )

                        _send_admin_email_for_purchase(purchase)
                        _send_customer_email(
                            customer_email=purchase.email,
                            customer_name=purchase.user_name,
                            book_titles=purchase.book.title,
                            order_type='ebook',
                            amount=float(purchase.price),
                            order_id=str(purchase.id),
                        )

                    logger.info(f"Cashfree e-book purchase completed: purchase_id={purchase.id}")
                    return Response({
                        'status': 'success',
                        'paid': True,
                        'type': 'ebook',
                        'purchase_id': str(purchase.id),
                        'book_title': purchase.book.title,
                    })
                except EbookPurchase.DoesNotExist:
                    pass

                # 2. Order (from CreateOrderView)
                try:
                    order = Order.objects.get(
                        cashfree_order_id=cf_order_id,
                        payment_status='pending'
                    )
                    with transaction.atomic():
                        Payment.objects.create(
                            order=order,
                            cashfree_order_id=cf_order_id,
                            cashfree_payment_id=cf_payment_id,
                            amount=order.total_price,
                            status='completed',
                            payment_method='cashfree',
                            transaction_id=cf_payment_id,
                        )
                        order.payment_status = 'paid'
                        order.status = 'completed'
                        order.cashfree_payment_id = cf_payment_id
                        order.transaction_id = cf_payment_id
                        order.save(update_fields=['payment_status', 'status', 'cashfree_payment_id', 'transaction_id'])

                        # Grant ebook access if applicable
                        if order.order_type == 'ebook':
                            UserLibrary.objects.get_or_create(
                                user=order.user, book=order.book, defaults={'order': order}
                            )

                        _send_customer_email(
                            customer_email=order.email or order.user.email,
                            customer_name=order.full_name or order.user.email,
                            book_titles=order.book.title,
                            order_type=order.order_type,
                            amount=float(order.total_price),
                            order_id=str(order.id),
                            estimated_delivery=(
                                order.estimated_delivery_date.strftime('%d %b %Y')
                                if order.estimated_delivery_date else None
                            ),
                        )

                    logger.info(f"Cashfree order completed: order_id={order.id}")
                    return Response({
                        'status': 'success',
                        'paid': True,
                        'type': order.order_type,
                        'order_id': str(order.id),
                        'book_title': order.book.title,
                    })
                except Order.DoesNotExist:
                    pass

                # 3. CartCheckoutSession
                try:
                    cart_session = CartCheckoutSession.objects.get(
                        cashfree_order_id=cf_order_id,
                        status='pending'
                    )
                    # Determine which user to assign orders to
                    if is_webhook:
                        user = cart_session.user
                    else:
                        user = self.request.user
                    self._complete_cart(user, cart_session, cf_order_id, cf_data)
                    return Response({
                        'status': 'success',
                        'paid': True,
                        'type': 'cart',
                    })
                except CartCheckoutSession.DoesNotExist:
                    pass

                # No matching order found
                logger.error(f"Cashfree: No matching order found for cf_order_id={cf_order_id}")
                return Response(
                    {'error': 'Order not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            else:  # Payment failed
                with transaction.atomic():
                    EbookPurchase.objects.filter(
                        cashfree_order_id=cf_order_id,
                        payment_status='initiated'
                    ).update(payment_status='failed')
                    Order.objects.filter(
                        cashfree_order_id=cf_order_id,
                        payment_status='pending'
                    ).update(payment_status='failed', status='cancelled')
                    CartCheckoutSession.objects.filter(
                        cashfree_order_id=cf_order_id,
                        status='pending'
                    ).update(status='failed')

                logger.info(f"Cashfree payment failed for order_id={cf_order_id}")
                return Response({
                    'status': 'failure',
                    'paid': False,
                })

        except Exception as e:
            logger.error(f"Cashfree payment processing error: {e}", exc_info=True)
            return Response(
                {'error': 'Payment processing failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _complete_cart(self, user, cart_session, cf_order_id, cf_data):
        """Create Order records from cart session after successful payment."""
        from apps.books.models import Book

        items = cart_session.items
        total_amount = cart_session.total_amount

        physical_total = sum(
            float(i.get('price', 0)) * int(i.get('qty', 1))
            for i in items if i.get('book_type', 'physical') != 'ebook'
        )
        total_delivery = calculate_delivery_charge(physical_total)
        delivery_assigned = False
        book_titles = []
        cf_payment_id = cf_data.get('cf_payment_id', '')

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
                        user=user, book=book,
                        order_type=item.get('book_type', 'physical'),
                        quantity=item.get('qty', 1),
                        book_price=item.get('price', 0),
                        delivery_charge=item_delivery,
                        total_price=item_total,
                        status='completed',
                        delivery_status='pending',
                        payment_status='paid',
                        cashfree_order_id=cf_order_id,
                        cashfree_payment_id=cf_payment_id,
                        transaction_id=cf_payment_id,
                        full_name=user.get_full_name() or '',
                        email=user.email,
                    )
                    Payment.objects.create(
                        order=order,
                        cashfree_order_id=cf_order_id,
                        cashfree_payment_id=cf_payment_id,
                        amount=item_total,
                        status='completed',
                        payment_method='cashfree',
                        transaction_id=cf_payment_id,
                    )
                    if order.order_type == 'ebook':
                        UserLibrary.objects.get_or_create(
                            user=user, book=book, defaults={'order': order}
                        )
                    book_titles.append(book.title)
                except Book.DoesNotExist:
                    continue

            cart_session.status = 'completed'
            cart_session.save(update_fields=['status'])

        # Send confirmation email
        _send_customer_email(
            customer_email=user.email,
            customer_name=user.get_full_name() or user.email,
            book_titles=book_titles,
            order_type='physical',
            amount=float(total_amount),
            order_id=cf_order_id,
        )

        logger.info(f"Cashfree cart order completed: cart_id={cart_session.id}, orders={len(book_titles)}")


class CalculateDeliveryView(APIView):
    """Public endpoint — calculate delivery charge."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        items_total = float(request.data.get('items_total', 0) or 0)
        delivery_charge = calculate_delivery_charge(items_total)
        return Response({
            'items_total': round(items_total, 2),
            'delivery_charge': delivery_charge,
            'final_total': round(items_total + delivery_charge, 2),
        })
