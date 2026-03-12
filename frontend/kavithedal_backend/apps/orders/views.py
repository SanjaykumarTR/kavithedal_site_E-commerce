"""
Views for Orders App - Order management and Razorpay payment integration.
"""
import razorpay
from django.conf import settings
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db import transaction

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
        """Simulate payment for an order - no actual payment required."""
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
        Calculate delivery charge for a given PIN code.
        
        Delivery charges based on PIN code distance from Dharmapuri:
        - PIN codes starting with 636 → ₹40 (Local)
        - PIN codes starting with 600 → ₹70 (Nearby)
        - All other locations → ₹90 (Standard)
        """
        pincode = request.data.get('pincode')
        book_price = request.data.get('book_price', 0)
        
        if not pincode:
            return Response(
                {'error': 'pincode is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Clean PIN code (remove any spaces or special characters)
        pincode = pincode.strip()
        
        # Calculate delivery charge based on PIN code prefix
        if pincode.startswith('636'):
            delivery_charge = 40.00
            zone_type = 'local'
            min_days = 2
            max_days = 3
        elif pincode.startswith('600'):
            delivery_charge = 70.00
            zone_type = 'nearby'
            min_days = 3
            max_days = 5
        else:
            delivery_charge = 90.00
            zone_type = 'standard'
            min_days = 5
            max_days = 7
        
        book_price_float = float(book_price) if book_price else 0
        total_price = book_price_float + delivery_charge
        
        # Calculate estimated delivery date
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
            if not book.pdf_file:
                return Response(
                    {'error': 'eBook not available for this book'},
                    status=status.HTTP_400_BAD_REQUEST
                )
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
            # Get delivery charge from request or calculate
            delivery_charge = float(request.data.get('delivery_charge', 0))
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
        if not book.pdf_file:
            return Response(
                {'error': 'eBook not available for this book'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
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
        
        # In production, you would create a Razorpay order here
        # For now, we'll simulate the payment
        from django.conf import settings
        
        # Check if Razorpay is configured
        razorpay_configured = (
            hasattr(settings, 'RAZORPAY_KEY_ID') and 
            settings.RAZORPAY_KEY_ID and
            hasattr(settings, 'RAZORPAY_KEY_SECRET') and
            settings.RAZORPAY_KEY_SECRET
        )
        
        if razorpay_configured:
            try:
                import razorpay
                
                # Initialize Razorpay client
                client = razorpay.Client(
                    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
                )
                
                # Create Razorpay order
                razorpay_order = client.order.create({
                    'amount': int(float(unit_price) * 100),  # Amount in paise
                    'currency': 'INR',
                    'receipt': str(purchase.id),
                    'notes': {
                        'book_title': book.title,
                        'user_email': email
                    }
                })
                
                # Update purchase with Razorpay order ID
                purchase.razorpay_order_id = razorpay_order['id']
                purchase.save()
                
                return Response({
                    'purchase_id': str(purchase.id),
                    'razorpay_order_id': razorpay_order['id'],
                    'amount': float(unit_price),
                    'currency': 'INR',
                    'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                    'book_title': book.title,
                    'book_cover': book.cover_image.url if book.cover_image else None
                })
                
            except Exception as e:
                pass  # Fall through to simulated payment
        
        # Simulated payment (when Razorpay is not configured)
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
            print(f"Failed to send admin email: {e}")


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
            print(f"Failed to send admin email: {e}")
        
        return Response({
            'status': 'Payment successful',
            'purchase_id': str(purchase.id),
            'message': 'Your eBook purchase was successful! You can now access it in your library.',
            'book_title': purchase.book.title
        })


class CartCheckoutView(APIView):
    """
    API View to create a Razorpay order for cart checkout.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Create a Razorpay order for cart items."""
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
            # Initialize Razorpay client
            client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
            
            # Create Razorpay order
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
            
            for item in items:
                book_id = item.get('book_id')
                quantity = item.get('qty', 1)
                
                try:
                    book = Book.objects.get(id=book_id)
                    
                    # Create order for this item
                    order = Order.objects.create(
                        user=request.user,
                        book=book,
                        order_type='physical',
                        quantity=quantity,
                        book_price=item.get('price', 0),
                        delivery_charge=0,
                        total_price=float(item.get('price', 0)) * quantity,
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
                        amount=float(item.get('price', 0)) * quantity,
                        status='completed',
                        payment_method='razorpay',
                        transaction_id=razorpay_payment_id
                    )
                    
                    created_orders.append(str(order.id))
                    
                except Book.DoesNotExist:
                    continue
            
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
