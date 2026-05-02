"""
URL configuration for Kavithedal Publications Backend.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from apps.books import views
from apps.orders.views import CashfreeVerifyPaymentView


def health_check(request):
    """Simple health-check endpoint — Render uses this to verify the service is up."""
    return JsonResponse({'status': 'ok'})


urlpatterns = [
    path('admin/', admin.site.urls),

    # Health check (Render pings this to confirm deployment succeeded)
    path('health/', health_check, name='health-check'),

    # API endpoints
    path('api/', include('apps.accounts.urls')),
    path('api/books/', include('apps.books.urls')),
    path('api/authors/', include('apps.authors.urls')),
    path('api/testimonials/', include('apps.testimonials.urls')),
    path('api/contests/', include('apps.contests.urls')),
    path('api/orders/', include('apps.orders.urls')),
    path('api/wishlist/', include('apps.wishlist.urls')),

    # Cashfree payment webhook endpoint
    path('api/payment/webhook/', CashfreeVerifyPaymentView.as_view(), name='cashfree-webhook'),

    # Secure PDF file access (requires authentication + purchase)
    path('api/books/<uuid:book_id>/pdf/', views.SecureFileView.as_view(), name='secure-pdf'),
    path('api/books/<uuid:book_id>/check-access/', views.check_pdf_access, name='check-pdf-access'),
]

# Serve media files:
#   - Always in development (DEBUG=True)
#   - In production ONLY when Cloudinary is not configured (local disk storage fallback)
#     Cloudinary serves its own files via CDN — no local route needed in that case.
# WhiteNoise handles only STATIC files, not MEDIA files.
_using_cloudinary = getattr(settings, 'DEFAULT_FILE_STORAGE', '').startswith('cloudinary')
if settings.DEBUG or not _using_cloudinary:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
