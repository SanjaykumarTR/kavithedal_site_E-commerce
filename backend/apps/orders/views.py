"""
Views for Orders App - Order management and Razorpay payment integration.
"""
import hashlib
import hmac
import json
import logging
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db import transaction

try:
    import razorpay
except ImportError:
    razorpay = None

logger = logging.getLogger('apps')


def _razorpay_configured():
    """Return True when both Razorpay credentials are set in the environment."""
    return bool(
        getattr(settings, 'RAZORPAY_KEY_ID', '') and
        getattr(settings, 'RAZORPAY_KEY_SECRET', '')
    )


def calculate_delivery_charge(total_price):
    """
    Calculate delivery charge for physical books based on order total.
    Rules:
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
    else:
        return 20


def _get_razorpay_client():
    """Return a configured Razorpay client (razorpay must be installed)."""
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


def _send_customer_email(customer_email, customer_name, book_titles,
                          order_type, amount, order_id, estimated_delivery=None):
    """
    Send order confirmation + payment success email to the customer.
    Called after every successful payment verification.
    book_titles: str (single book) or list of str (cart checkout)
    """
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

    subject = f'Order Confirmed — Kavithedal Publications'
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

For any queries, reply to this email or contact us at kavithedalpublications@gmail.com

Warm regards,
Kavithedal Publications
"""
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [customer_email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.error('Failed to send customer email to %s: %s', customer_email, exc)


from .models import Order, Payment, UserLibrary, DeliveryZone, EbookPurchase
from .serializers import (
    OrderSerializer, OrderCreateSerializer,
    PaymentSerializer, PaymentCreateSerializer,
    UserLibrarySerializer, UserLibraryListSerializer,
    DeliveryZoneSerializer
)
from apps.accounts.utils import is_authorized_admin


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Custom permission to only allow owners to edit their objects."""
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user or is_authorized_admin(request.user)


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
        """Simulate payment — development/testing only. Blocked in production."""
        # Refuse simulation when real Razorpay credentials are present
        if _razorpay_configured():
            return Response(
                {'error': 'Payment simulation is not available when Razorpay is configured.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        order = self.get_object()

        if order.status != 'pending':
            return Response(
                {'error': 'Payment already processed or cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create simulated payment
        payment = Payment.objects.create(
            order=order,
            razorpay_order_id=f'simulated_{order.id}',
            razorpay_payment_id=f'simulated_payment_{order.id}',
            amount=order.total_price,
            status='completed',
            payment_method='simulated',
            transaction_id=f'sim_txn_{order.id}'
        )
        
        # Complete the order
        order.status = 'completed'
        order.save()
        
        # Add to user's library if it's an ebook
        if order.order_type == 'ebook':
            UserLibrary.objects.get_or_create(
                user=order.user,
                book=order.book,
                defaults={'order': order}
            )
        
        return Response({
            'status': 'Payment successful',
            'order_id': str(order.id),
            'message': 'Payment simulated successfully!'
        })
    
    @action(detail=True, methods=['post'])
    def initiate_payment(self, request, pk=None):
        """Legacy endpoint - redirects to simulated payment."""
        return self.simulate_payment(request, pk)
    
    @action(detail=True, methods=['post'])
    def verify_payment(self, request, pk=None):
        """Legacy endpoint - redirects to simulated payment."""
        return self.simulate_payment(request, pk)


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing payments."""
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if is_authorized_admin(user):
            return Payment.objects.all().select_related('order', 'order__book')
        return Payment.objects.filter(order__user=user).select_related('order', 'order__book')


class DeliveryZoneViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Delivery Zones - read only for customers."""
    serializer_class = DeliveryZoneSerializer
    permission_classes = [permissions.AllowAny]  # Public access for checking delivery
    
    def get_queryset(self):
        return DeliveryZone.objects.filter(is_active=True)
    
    @action(detail=False, methods=['get'])
    def by_pincode(self, request):
        """Look up delivery zone by PIN code."""
        pincode = request.query_params.get('pincode')
        
        if not pincode:
            return Response(
                {'error': 'pincode is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            zone = DeliveryZone.objects.get(pincode=pincode, is_active=True)
            serializer = DeliveryZoneSerializer(zone)
            return Response(serializer.data)
        except DeliveryZone.DoesNotExist:
            # Return default delivery info if PIN code not found
            return Response({
                'pincode': pincode,
                'city': 'Unknown',
                'state': 'Unknown',
                'zone_type': 'national',
                'delivery_charge': '100.00',
                'min_delivery_days': 5,
                'max_delivery_days': 10,
                'delivery_time': '5-10 Days',
                'is_active': True,
                'message': 'Delivery available with standard charges'
            })
    
    @action(detail=False, methods=['post'])
    def calculate_delivery(self, request):
        """
        Calculate delivery charge based on book price (price-based tiers).
        PIN code is used only to estimate delivery time.

        Delivery charge tiers (by order total):
          < ₹500  → ₹40
          ₹500–₹999 → ₹30
          ≥ ₹1000 → ₹20
        """
        pincode = request.data.get('pincode', '')
        book_price = request.data.get('book_price', 0)

        book_price_float = float(book_price) if book_price else 0

        # Price-based delivery charge
        delivery_charge = calculate_delivery_charge(book_price_float)

        # Pincode used only for delivery time estimate
        pincode = pincode.strip() if pincode else ''
        if pincode.startswith('636'):
            zone_type = 'local'
            min_days, max_days = 2, 3
        elif pincode.startswith('600'):
            zone_type = 'nearby'
            min_days, max_days = 3, 5
        else:
            zone_type = 'standard'
            min_days, max_days = 5, 7

        total_price = book_price_float + delivery_charge

        from datetime import date, timedelta
        estimated_date = date.today() + timedelta(days=max_days)

        return Response({
            'pincode': pincode,
            'delivery_charge': delivery_charge,
            'book_price': book_price_float,
            'total_price': total_price,
            'min_delivery_days': min_days,
            'max_delivery_days': max_days,
            'estimated_delivery_date': estimated_date.strftime('%Y-%m-%d'),
            'zone_type': zone_type,
            'message': 'Delivery charge calculated successfully'
        })


class UserLibraryViewSet(viewsets.ModelViewSet):
    """ViewSet for user's library."""
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
        """Check if user has access to a specific book's PDF."""
        book_id = request.query_params.get('book_id')
        
        if not book_id:
            return Response(
                {'error': 'book_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        has_access = UserLibrary.objects.filter(
            user=request.user,
            book_id=book_id
        ).exists()
        
        return Response({
            'has_access': has_access,
            'book_id': book_id
        })


class CreateOrderView(APIView):
    """
    API View to create an order and initiate Razorpay payment.

    For physical books:
    - Calculate delivery charge based on PIN code
    - Returns Razorpay order details for frontend checkout

    For ebooks:
    - Direct purchase without delivery charge
    - Returns Razorpay order details for frontend checkout
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        book_id = request.data.get('book_id')
        order_type = request.data.get('order_type', 'physical')  # 'ebook' or 'physical'
        # simulate is ONLY allowed when no Razorpay keys are configured (local dev)
        _razorpay_configured = bool(
            getattr(settings, 'RAZORPAY_KEY_ID', '') and
            getattr(settings, 'RAZORPAY_KEY_SECRET', '')
        )
        simulate = not _razorpay_configured
        
        if not book_id:
            return Response(
                {'error': 'book_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from apps.books.models import Book
        
        try:
            book = Book.objects.get(id=book_id, is_active=True)
        except Book.DoesNotExist:
            return Response(
                {'error': 'Book not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if user already owns this book
        if UserLibrary.objects.filter(user=request.user, book=book).exists() and order_type == 'ebook':
            return Response(
                {'error': 'You already own this eBook'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the appropriate price
        if order_type == 'ebook':
            unit_price = book.ebook_price
            if not unit_price:
                return Response(
                    {'error': 'eBook price not set'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            delivery_charge = 0
            total_price = unit_price
        else:
            unit_price = book.physical_price or book.price
            if not unit_price:
                return Response(
                    {'error': 'Physical book price not set'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            delivery_charge = calculate_delivery_charge(float(unit_price))
            total_price = float(unit_price) + delivery_charge
        
        # Get shipping details
        shipping_pincode = request.data.get('shipping_pincode', '')
        estimated_delivery_date = None
        if order_type == 'physical' and shipping_pincode:
            from datetime import date, timedelta
            # Calculate delivery days based on PIN code
            if shipping_pincode.startswith('636'):
                max_days = 3
            elif shipping_pincode.startswith('600'):
                max_days = 5
            else:
                max_days = 7
            estimated_delivery_date = date.today() + timedelta(days=max_days)
        
        # Create order
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
        
        # If simulation mode, directly complete the order
        if simulate:
            # Create a simulated payment record
            payment = Payment.objects.create(
                order=order,
                razorpay_order_id=f'simulated_{order.id}',
                razorpay_payment_id=f'simulated_payment_{order.id}',
                amount=total_price,
                status='completed',
                payment_method='simulated',
                transaction_id=f'sim_txn_{order.id}'
            )
            
            # Complete the order
            order.status = 'completed'
            order.payment_status = 'paid'
            order.save()
            
            # Add to user's library if it's an ebook
            if order.order_type == 'ebook':
                UserLibrary.objects.get_or_create(
                    user=order.user,
                    book=order.book,
                    defaults={'order': order}
                )
            
            return Response({
                'order_id': str(order.id),
                'status': 'completed',
                'message': 'Order completed successfully!',
                'order_type': order_type,
                'book_title': book.title,
                'book_price': float(unit_price),
                'delivery_charge': delivery_charge,
                'total_price': float(total_price),
                'book_cover': book.cover_image.url if book.cover_image else None,
                'estimated_delivery_date': estimated_delivery_date.strftime('%Y-%m-%d') if estimated_delivery_date else None,
                'purchased': True
            })
        
        # If not simulating, return order details for payment
        return Response({
            'order_id': str(order.id),
            'status': 'pending',
            'amount': float(total_price),
            'book_price': float(unit_price),
            'delivery_charge': delivery_charge,
            'currency': 'INR',
            'book_title': book.title,
            'book_cover': book.cover_image.url if book.cover_image else None,
            'estimated_delivery_date': estimated_delivery_date.strftime('%Y-%m-%d') if estimated_delivery_date else None,
            'shipping_details': {
                'full_name': order.full_name,
                'address': order.shipping_address,
                'city': order.shipping_city,
                'state': order.shipping_state,
                'pincode': order.shipping_pincode,
            }
        })


class VerifyPaymentView(APIView):
    """
    API View to verify Razorpay payment signature and complete the order.
    When Razorpay is not configured (local dev), falls back to simulation.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        order_id = request.data.get('order_id')
        razorpay_payment_id = request.data.get('razorpay_payment_id')
        razorpay_signature = request.data.get('razorpay_signature')
        razorpay_order_id = request.data.get('razorpay_order_id')

        if not order_id:
            return Response(
                {'error': 'order_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        if order.status == 'completed':
            return Response({
                'status': 'already_completed',
                'order_id': str(order.id),
                'message': 'Order already completed',
            })

        _razorpay_configured = bool(
            getattr(settings, 'RAZORPAY_KEY_ID', '') and
            getattr(settings, 'RAZORPAY_KEY_SECRET', '')
        )

        if _razorpay_configured:
            # --- Real Razorpay signature verification ---
            if not all([razorpay_payment_id, razorpay_signature, razorpay_order_id]):
                return Response(
                    {'error': 'Missing required fields: razorpay_payment_id, razorpay_signature, razorpay_order_id'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                client = razorpay.Client(
                    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
                )
                client.utility.verify_payment_signature({
                    'razorpay_order_id': razorpay_order_id,
                    'razorpay_payment_id': razorpay_payment_id,
                    'razorpay_signature': razorpay_signature,
                })
            except razorpay.errors.SignatureVerificationError:
                return Response(
                    {'error': 'Payment verification failed — invalid signature'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                payment, _ = Payment.objects.get_or_create(
                    order=order,
                    defaults={
                        'razorpay_order_id': razorpay_order_id,
                        'razorpay_payment_id': razorpay_payment_id,
                        'razorpay_signature': razorpay_signature,
                        'amount': order.total_price,
                        'status': 'completed',
                        'payment_method': 'razorpay',
                        'transaction_id': razorpay_payment_id,
                    }
                )
                if payment.status != 'completed':
                    payment.razorpay_payment_id = razorpay_payment_id
                    payment.razorpay_signature = razorpay_signature
                    payment.status = 'completed'
                    payment.transaction_id = razorpay_payment_id
                    payment.save()

                order.status = 'completed'
                order.payment_status = 'paid'
                order.razorpay_payment_id = razorpay_payment_id
                order.transaction_id = razorpay_payment_id
                order.save()

                if order.order_type == 'ebook':
                    UserLibrary.objects.get_or_create(
                        user=order.user,
                        book=order.book,
                        defaults={'order': order},
                    )
        else:
            # --- Simulation mode (no Razorpay keys configured — local dev only) ---
            with transaction.atomic():
                Payment.objects.create(
                    order=order,
                    razorpay_order_id=f'sim_{order.id}',
                    razorpay_payment_id=f'sim_pay_{order.id}',
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
                        user=order.user,
                        book=order.book,
                        defaults={'order': order},
                    )

        # Send order confirmation email to customer
        customer_email = order.email or request.user.email
        customer_name = order.full_name or request.user.get_full_name() or customer_email
        _send_customer_email(
            customer_email=customer_email,
            customer_name=customer_name,
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
            'status': 'Payment successful',
            'order_id': str(order.id),
            'message': 'Your purchase was successful!',
        })


class EbookPurchaseView(APIView):
    """
    API View for eBook purchases with Razorpay payment integration.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Create a new eBook purchase and initiate Razorpay payment."""
        book_id = request.data.get('book_id')
        user_name = request.data.get('user_name')
        email = request.data.get('email')
        phone = request.data.get('phone')
        address = request.data.get('address')
        
        # Validate required fields
        if not all([book_id, user_name, email, phone, address]):
            return Response(
                {'error': 'All fields are required: book_id, user_name, email, phone, address'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from apps.books.models import Book
        
        try:
            book = Book.objects.get(id=book_id, is_active=True)
        except Book.DoesNotExist:
            return Response(
                {'error': 'Book not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if user already owns this eBook
        if UserLibrary.objects.filter(user=request.user, book=book).exists():
            return Response(
                {'error': 'You already own this eBook'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get eBook price
        unit_price = book.ebook_price
        if not unit_price:
            return Response(
                {'error': 'eBook price not set'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create purchase record
        purchase = EbookPurchase.objects.create(
            user=request.user,
            book=book,
            user_name=user_name,
            email=email,
            phone=phone,
            address=address,
            price=unit_price,
            payment_status='initiated'
        )
        
        if _razorpay_configured():
            try:
                client = _get_razorpay_client()
                razorpay_order = client.order.create({
                    'amount': int(float(unit_price) * 100),
                    'currency': 'INR',
                    'receipt': str(purchase.id),
                    'notes': {
                        'book_title': book.title,
                        'user_email': email,
                    }
                })
                purchase.razorpay_order_id = razorpay_order['id']
                purchase.save()
                return Response({
                    'purchase_id': str(purchase.id),
                    'razorpay_order_id': razorpay_order['id'],
                    'amount': float(unit_price),
                    'currency': 'INR',
                    'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                    'book_title': book.title,
                    'book_cover': book.cover_image.url if book.cover_image else None,
                })
            except Exception as e:
                logger.error('Razorpay order creation failed for purchase %s: %s', purchase.id, e)
                purchase.delete()
                return Response(
                    {'error': 'Payment gateway error. Please try again.'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

        # Simulation mode — only when Razorpay is NOT configured (local dev)
        try:
            purchase.payment_status = 'completed'
            purchase.transaction_id = f'test_txn_{purchase.id}'
            purchase.save()
            
            # Add to user's library
            UserLibrary.objects.get_or_create(
                user=request.user,
                book=book
            )
            
            # Send email notification to admin
            self.send_admin_email(purchase)
            
            return Response({
                'purchase_id': str(purchase.id),
                'status': 'completed',
                'message': 'Purchase completed successfully!',
                'book_title': book.title
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to process purchase: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def send_admin_email(self, purchase):
        """Send email notification to admin about new eBook purchase."""
        from django.core.mail import send_mail
        from django.conf import settings
        
        subject = f'New eBook Purchase: {purchase.book.title}'
        
        message = f"""
New eBook Purchase Details:

Customer Name: {purchase.user_name}
Customer Email: {purchase.email}
Phone Number: {purchase.phone}
Address: {purchase.address}

Book Name: {purchase.book.title}
Book Price: ₹{purchase.price}
Payment Status: {purchase.payment_status}
Order Date: {purchase.order_date}

This is an automated notification from Kavithedal Publications.
"""
        
        admin_email = getattr(settings, 'ADMIN_EMAIL', settings.DEFAULT_FROM_EMAIL)
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [admin_email],
                fail_silently=False,
            )
        except Exception as e:
            logger.error('Failed to send admin email for purchase %s: %s', purchase.id, e)


class VerifyEbookPaymentView(APIView):
    """
    API View to verify Razorpay payment for eBook purchase.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Verify payment and complete the eBook purchase."""
        purchase_id = request.data.get('purchase_id')
        razorpay_payment_id = request.data.get('razorpay_payment_id')
        razorpay_signature = request.data.get('razorpay_signature')
        razorpay_order_id = request.data.get('razorpay_order_id')
        
        if not all([purchase_id, razorpay_payment_id, razorpay_signature]):
            return Response(
                {'error': 'Missing required fields: purchase_id, razorpay_payment_id, razorpay_signature'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            purchase = EbookPurchase.objects.get(id=purchase_id, user=request.user)
        except EbookPurchase.DoesNotExist:
            return Response(
                {'error': 'Purchase not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if purchase.payment_status == 'completed':
            return Response({
                'status': 'already_completed',
                'message': 'Purchase already completed',
            })

        # Verify Razorpay signature before completing the purchase
        _razorpay_configured = bool(
            getattr(settings, 'RAZORPAY_KEY_ID', '') and
            getattr(settings, 'RAZORPAY_KEY_SECRET', '')
        )
        if _razorpay_configured:
            try:
                client = razorpay.Client(
                    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
                )
                client.utility.verify_payment_signature({
                    'razorpay_order_id': razorpay_order_id,
                    'razorpay_payment_id': razorpay_payment_id,
                    'razorpay_signature': razorpay_signature,
                })
            except razorpay.errors.SignatureVerificationError:
                return Response(
                    {'error': 'Payment verification failed — invalid signature'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        with transaction.atomic():
            purchase.razorpay_payment_id = razorpay_payment_id
            purchase.razorpay_signature = razorpay_signature
            purchase.razorpay_order_id = razorpay_order_id
            purchase.payment_status = 'completed'
            purchase.transaction_id = razorpay_payment_id
            purchase.save()

            # Add to user's library
            UserLibrary.objects.get_or_create(
                user=request.user,
                book=purchase.book,
            )
        
        # Send admin email
        subject = f'New eBook Purchase: {purchase.book.title}'
        message = f"""
New eBook Purchase Details:

Customer Name: {purchase.user_name}
Customer Email: {purchase.email}
Phone Number: {purchase.phone}
Address: {purchase.address}

Book Name: {purchase.book.title}
Book Price: ₹{purchase.price}
Payment Status: {purchase.payment_status}
Order Date: {purchase.order_date}

This is an automated notification from Kavithedal Publications.
"""
        
        from django.core.mail import send_mail
        from django.conf import settings
        
        admin_email = getattr(settings, 'ADMIN_EMAIL', settings.DEFAULT_FROM_EMAIL)
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [admin_email],
                fail_silently=False,
            )
        except Exception as e:
            logger.error('Failed to send admin email for purchase %s: %s', purchase.id, e)

        # Send order confirmation email to customer
        _send_customer_email(
            customer_email=purchase.email,
            customer_name=purchase.user_name,
            book_titles=purchase.book.title,
            order_type='ebook',
            amount=float(purchase.price),
            order_id=str(purchase.id),
        )

        return Response({
            'status': 'Payment successful',
            'purchase_id': str(purchase.id),
            'message': 'Your eBook purchase was successful! You can now access it in your library.',
            'book_title': purchase.book.title
        })


class CalculateDeliveryView(APIView):
    """
    Public API to calculate delivery charge based on physical books total.
    Returns items_total, delivery_charge, and final_total.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        items_total = request.data.get('items_total', 0)
        try:
            items_total = float(items_total)
        except (TypeError, ValueError):
            return Response({'error': 'items_total must be a number'}, status=status.HTTP_400_BAD_REQUEST)

        delivery_charge = calculate_delivery_charge(items_total)
        return Response({
            'items_total': round(items_total, 2),
            'delivery_charge': delivery_charge,
            'final_total': round(items_total + delivery_charge, 2),
        })


class CartCheckoutView(APIView):
    """
    API View to create a Razorpay order for cart checkout.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Create a Razorpay order for cart items."""
        if not _razorpay_configured():
            return Response(
                {'error': 'Payment gateway is not configured. Contact support.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        items = request.data.get('items', [])
        total_amount = request.data.get('total_amount', 0)

        if not items:
            return Response(
                {'error': 'No items in cart'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if total_amount <= 0:
            return Response(
                {'error': 'Invalid total amount'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Convert to paise (Razorpay uses paise)
        amount_in_paise = int(float(total_amount) * 100)
        
        # Create receipt ID
        import uuid
        receipt_id = f'receipt_{uuid.uuid4().hex[:12]}'
        
        try:
            client = _get_razorpay_client()
            razorpay_order = client.order.create({
                'amount': amount_in_paise,
                'currency': 'INR',
                'receipt': receipt_id,
                'payment_capture': 1,
                'notes': {
                    'user_id': str(request.user.id),
                    'username': request.user.username or request.user.email
                }
            })
            
            return Response({
                'razorpay_order_id': razorpay_order['id'],
                'amount': razorpay_order['amount'],
                'currency': razorpay_order['currency'],
                'key_id': settings.RAZORPAY_KEY_ID,
                'receipt': receipt_id,
                'status': razorpay_order['status']
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to create order: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CartPaymentVerifyView(APIView):
    """
    API View to verify Razorpay payment for cart checkout.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Verify payment and create orders for cart items."""
        razorpay_payment_id = request.data.get('razorpay_payment_id')
        razorpay_signature = request.data.get('razorpay_signature')
        razorpay_order_id = request.data.get('razorpay_order_id')
        items = request.data.get('items', [])
        total_amount = request.data.get('total_amount', 0)
        
        if not all([razorpay_payment_id, razorpay_signature, razorpay_order_id]):
            return Response(
                {'error': 'Missing required payment details'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not items:
            return Response(
                {'error': 'No items provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Verify Razorpay signature
            client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
            
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            
            # Verify the signature
            client.utility.verify_payment_signature(params_dict)
            
            # Payment verified successfully - create orders for each item
            from apps.books.models import Book
            created_orders = []

            # Calculate delivery charge based on physical books total
            physical_total = sum(
                float(item.get('price', 0)) * int(item.get('qty', 1))
                for item in items
                if item.get('book_type', 'physical') != 'ebook'
            )
            total_delivery_charge = calculate_delivery_charge(physical_total)

            # Assign delivery charge to first physical item only
            delivery_charge_assigned = False

            for item in items:
                book_id = item.get('book_id')
                quantity = item.get('qty', 1)
                item_book_type = item.get('book_type', 'physical')

                try:
                    book = Book.objects.get(id=book_id)

                    item_delivery = 0
                    if item_book_type != 'ebook' and not delivery_charge_assigned:
                        item_delivery = total_delivery_charge
                        delivery_charge_assigned = True

                    item_total = float(item.get('price', 0)) * quantity + item_delivery

                    # Create order for this item
                    order = Order.objects.create(
                        user=request.user,
                        book=book,
                        order_type=item_book_type,
                        quantity=quantity,
                        book_price=item.get('price', 0),
                        delivery_charge=item_delivery,
                        total_price=item_total,
                        status='completed',
                        delivery_status='pending',
                        payment_status='completed',
                        razorpay_order_id=razorpay_order_id,
                        razorpay_payment_id=razorpay_payment_id,
                        transaction_id=razorpay_payment_id,
                        full_name=request.user.get_full_name() or '',
                        email=request.user.email,
                    )

                    # Create payment record
                    Payment.objects.create(
                        order=order,
                        razorpay_order_id=razorpay_order_id,
                        razorpay_payment_id=razorpay_payment_id,
                        razorpay_signature=razorpay_signature,
                        amount=item_total,
                        status='completed',
                        payment_method='razorpay',
                        transaction_id=razorpay_payment_id
                    )
                    
                    created_orders.append(str(order.id))
                    
                except Book.DoesNotExist:
                    continue

            # Send order confirmation email to customer
            book_titles = [item.get('title', 'Book') for item in items]
            _send_customer_email(
                customer_email=request.user.email,
                customer_name=request.user.get_full_name() or request.user.email,
                book_titles=book_titles,
                order_type='physical',  # cart may have mixed types; physical label is generic
                amount=float(total_amount),
                order_id=razorpay_payment_id,
            )

            return Response({
                'status': 'Payment successful',
                'message': f'{len(created_orders)} order(s) created successfully',
                'order_ids': created_orders,
                'transaction_id': razorpay_payment_id
            })
            
        except razorpay.errors.SignatureVerificationError:
            return Response(
                {'error': 'Payment verification failed - Invalid signature'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Payment verification failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class RazorpayWebhookView(APIView):
    """
    Razorpay Webhook endpoint.

    Razorpay sends POST requests here for payment events.
    We verify the X-Razorpay-Signature header using HMAC-SHA256 and the
    RAZORPAY_WEBHOOK_SECRET environment variable before processing any event.

    Events handled:
      payment.captured  — mark order/purchase paid
      order.paid        — same as above (belt-and-suspenders)
      payment.failed    — mark order/purchase failed
    """
    authentication_classes = []          # No JWT — Razorpay sends no auth header
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        webhook_secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', '')
        if not webhook_secret:
            logger.error('RazorpayWebhookView: RAZORPAY_WEBHOOK_SECRET not configured')
            return Response({'error': 'Webhook not configured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 1. Verify HMAC-SHA256 signature
        received_sig = request.headers.get('X-Razorpay-Signature', '')
        if not received_sig:
            logger.warning('RazorpayWebhookView: missing X-Razorpay-Signature header')
            return Response({'error': 'Missing signature'}, status=status.HTTP_400_BAD_REQUEST)

        expected_sig = hmac.new(
            key=webhook_secret.encode('utf-8'),
            msg=request.body,
            digestmod=hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected_sig, received_sig):
            logger.warning('RazorpayWebhookView: signature mismatch — possible spoofed request')
            return Response({'error': 'Invalid signature'}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Parse payload
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return Response({'error': 'Invalid JSON'}, status=status.HTTP_400_BAD_REQUEST)

        event = payload.get('event', '')
        payment_entity = payload.get('payload', {}).get('payment', {}).get('entity', {})
        razorpay_payment_id = payment_entity.get('id', '')
        razorpay_order_id = payment_entity.get('order_id', '')

        logger.info('RazorpayWebhookView: received event=%s payment=%s order=%s',
                    event, razorpay_payment_id, razorpay_order_id)

        # 3. Handle events
        if event in ('payment.captured', 'order.paid'):
            with transaction.atomic():
                # Update Order records
                updated_orders = Order.objects.filter(
                    razorpay_order_id=razorpay_order_id,
                    payment_status='pending',
                )
                for order in updated_orders.select_related('book', 'user'):
                    order.payment_status = 'paid'
                    order.status = 'completed'
                    order.razorpay_payment_id = razorpay_payment_id
                    order.transaction_id = razorpay_payment_id
                    order.save(update_fields=['payment_status', 'status',
                                              'razorpay_payment_id', 'transaction_id'])
                    # Add ebooks to library
                    if order.order_type == 'ebook':
                        UserLibrary.objects.get_or_create(
                            user=order.user,
                            book=order.book,
                            defaults={'order': order},
                        )

                # Update EbookPurchase records
                EbookPurchase.objects.filter(
                    razorpay_order_id=razorpay_order_id,
                    payment_status='initiated',
                ).update(
                    payment_status='completed',
                    razorpay_payment_id=razorpay_payment_id,
                    transaction_id=razorpay_payment_id,
                )

            logger.info('RazorpayWebhookView: %s processed successfully', event)

        elif event == 'payment.failed':
            with transaction.atomic():
                Order.objects.filter(
                    razorpay_order_id=razorpay_order_id,
                    payment_status='pending',
                ).update(payment_status='failed', status='cancelled')

                EbookPurchase.objects.filter(
                    razorpay_order_id=razorpay_order_id,
                    payment_status='initiated',
                ).update(payment_status='failed')

            logger.info('RazorpayWebhookView: payment.failed processed for order %s', razorpay_order_id)

        # Always return 200 — Razorpay retries on non-2xx
        return Response({'status': 'ok'})
