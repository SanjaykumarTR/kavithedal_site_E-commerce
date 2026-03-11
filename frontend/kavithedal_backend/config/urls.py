"""
URL configuration for Kavithedal Publications Backend.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from apps.books import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/', include('apps.accounts.urls')),
    path('api/books/', include('apps.books.urls')),
    path('api/authors/', include('apps.authors.urls')),
    path('api/testimonials/', include('apps.testimonials.urls')),
    path('api/contests/', include('apps.contests.urls')),
    path('api/orders/', include('apps.orders.urls')),
    
    # Secure file access
    path('api/books/<uuid:book_id>/pdf/', views.SecureFileView.as_view(), name='secure-pdf'),
    path('api/books/<uuid:book_id>/check-access/', views.check_pdf_access, name='check-pdf-access'),
    
    # Health check
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
]

# Media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
