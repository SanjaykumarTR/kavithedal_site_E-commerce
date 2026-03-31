"""
Django settings for Kavithedal Publications Backend.
Production-ready configuration — all secrets loaded from environment variables.
"""
import os
import logging
import dj_database_url
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv
from corsheaders.defaults import default_headers

# ─── Base directory ───────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file for local development. On Render, env vars are set in the
# dashboard so this call is a safe no-op there.
load_dotenv(BASE_DIR / '.env')


# ─── Cloudinary — check early so INSTALLED_APPS can be built conditionally ────
# Support both individual vars and CLOUDINARY_URL (cloudinary://key:secret@cloud)
_cloudinary_url = os.environ.get('CLOUDINARY_URL', '')
if _cloudinary_url and _cloudinary_url.startswith('cloudinary://'):
    # Parse cloudinary://api_key:api_secret@cloud_name
    try:
        _parts = _cloudinary_url[len('cloudinary://'):].split('@')
        _cloud_name = _parts[1] if len(_parts) == 2 else ''
        _key_secret = _parts[0].split(':') if _parts else []
        _api_key = _key_secret[0] if _key_secret else ''
        _api_secret = _key_secret[1] if len(_key_secret) > 1 else ''
        if _cloud_name and _api_key and _api_secret:
            os.environ.setdefault('CLOUDINARY_CLOUD_NAME', _cloud_name)
            os.environ.setdefault('CLOUDINARY_API_KEY', _api_key)
            os.environ.setdefault('CLOUDINARY_API_SECRET', _api_secret)
    except Exception:
        pass

_cloudinary_configured = bool(
    os.environ.get('CLOUDINARY_CLOUD_NAME') and
    os.environ.get('CLOUDINARY_API_KEY') and
    os.environ.get('CLOUDINARY_API_SECRET')
)

# Log Cloudinary status at startup so it's visible in Render logs
logging.basicConfig()
_startup_logger = logging.getLogger('config.settings')
if _cloudinary_configured:
    _startup_logger.warning(
        'Cloudinary ACTIVE — cloud=%s', os.environ.get('CLOUDINARY_CLOUD_NAME')
    )
else:
    _startup_logger.warning(
        'Cloudinary NOT configured — media files will use local storage. '
        'Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET in env.'
    )


# ─── Core Security ────────────────────────────────────────────────────────────

# Never commit a real secret key. Generate one with:
#   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
SECRET_KEY = os.environ['SECRET_KEY']  # Required — raises KeyError if missing

# DEBUG must be False in production. Set DEBUG=True only in local .env
DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 'yes')

# Render assigns RENDER_EXTERNAL_HOSTNAME automatically for deployed services.
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')

_allowed_hosts_env = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts_env.split(',') if h.strip()]

if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Custom domains — always allowed regardless of env var value.
# Add every domain (with and without www) that the frontend or admin may use.
for _custom_host in (
    'kavithedal.com', 'www.kavithedal.com',
    'kavithedalpublication.store', 'www.kavithedalpublication.store',
    'kavithedal-web.onrender.com',
):
    if _custom_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_custom_host)


# ─── Application Definition ───────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',

    # Local apps
    'apps.accounts',
    'apps.books',
    'apps.authors',
    'apps.testimonials',
    'apps.contests',
    'apps.orders',
    'apps.wishlist',
]

# Cloudinary apps only loaded when credentials are present — avoids startup
# crash when CLOUDINARY_* env vars are not yet configured.
if _cloudinary_configured:
    INSTALLED_APPS += ['cloudinary', 'cloudinary_storage']

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise must come directly after SecurityMiddleware
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# ─── Database ─────────────────────────────────────────────────────────────────
# Uses DATABASE_URL env var when set (Render PostgreSQL / any 12-factor DB).
# Falls back to local SQLite for development when DATABASE_URL is not set.
_DATABASE_URL = os.environ.get('DATABASE_URL')

if _DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            _DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# ─── Password Validation ──────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ─── Custom User Model ────────────────────────────────────────────────────────
AUTH_USER_MODEL = 'accounts.AdminUser'


# ─── Internationalisation ─────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True  # Always True — use timezone-aware datetimes throughout


# ─── Static Files ─────────────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# ─── Storage Backends (Django 5.x — DEFAULT_FILE_STORAGE was removed in 5.0) ─
# Must use STORAGES dict. Set default here; overridden below when Cloudinary
# is configured. WhiteNoise handles staticfiles.
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}


# ─── Media Files ──────────────────────────────────────────────────────────────
# NOTE: Render disk is ephemeral — uploaded media is lost on redeploy.
# For persistent media, configure Cloudinary (see bottom of this file).
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# ─── Default Primary Key ──────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ─── Email (Gmail SMTP) ───────────────────────────────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get(
    'DEFAULT_FROM_EMAIL',
    'Kavithedal Publications <noreply@kavithedal.com>'
)


# ─── Django REST Framework ────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'apps.accounts.authentication.CustomJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 12,
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    # Rate limiting protects login, contact, testimonial and contest endpoints
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '60/hour',
        'user': '300/hour',
    },
}


# ─── JWT Settings ─────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}


# ─── CORS ─────────────────────────────────────────────────────────────────────
# Set CORS_ALLOWED_ORIGINS as comma-separated URLs in env, e.g.:
#   https://kavithedal.onrender.com,https://kavithedal.com
_cors_env = os.environ.get('CORS_ALLOWED_ORIGINS', '')
# Always include the production custom domain and both Render URLs so that
# a missing or misconfigured env var never silently blocks the live site.
_cors_always = [
    'https://www.kavithedalpublication.store',
    'https://kavithedalpublication.store',
    'https://kavithedal-frontend-sgki.onrender.com',
]
if _cors_env:
    _cors_from_env = [o.strip() for o in _cors_env.split(',') if o.strip()]
    CORS_ALLOWED_ORIGINS = list(dict.fromkeys(_cors_from_env + _cors_always))
    CORS_ALLOW_ALL_ORIGINS = False
else:
    # Development fallback — allow all only when DEBUG=True
    CORS_ALLOW_ALL_ORIGINS = DEBUG
    CORS_ALLOWED_ORIGINS = [
        'http://localhost:5173',
        'http://localhost:3000',
        'http://127.0.0.1:5173',
    ] + _cors_always

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]


# ─── CSRF Trusted Origins ─────────────────────────────────────────────────────
# Django 4.0+ requires CSRF_TRUSTED_ORIGINS for POST requests behind a proxy.
# Render terminates SSL at the load balancer, so the Origin header must be trusted.
_csrf_origins = [
    'https://www.kavithedalpublication.store',
    'https://kavithedalpublication.store',
    'https://kavithedal-web.onrender.com',
    'https://kavithedal-frontend-sgki.onrender.com',
]
if RENDER_EXTERNAL_HOSTNAME:
    _reh = f'https://{RENDER_EXTERNAL_HOSTNAME}'
    if _reh not in _csrf_origins:
        _csrf_origins.append(_reh)
for _h in ALLOWED_HOSTS:
    if _h not in ('localhost', '127.0.0.1', '*') and f'https://{_h}' not in _csrf_origins:
        _csrf_origins.append(f'https://{_h}')
CSRF_TRUSTED_ORIGINS = _csrf_origins


# ─── Production Security Headers ──────────────────────────────────────────────
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'


# ─── File Upload Limits ───────────────────────────────────────────────────────
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10 MB


# ─── Cashfree Payment Gateway ─────────────────────────────────────────────────
# Get credentials from https://merchant.cashfree.com → Developers → API Keys
CASHFREE_APP_ID = os.environ.get('CASHFREE_APP_ID', '')
CASHFREE_SECRET_KEY = os.environ.get('CASHFREE_SECRET_KEY', '')
CASHFREE_WEBHOOK_SECRET = os.environ.get('CASHFREE_WEBHOOK_SECRET', '')

# Cashfree Base URL - sandbox for testing, production for live
CASHFREE_BASE_URL = os.environ.get('CASHFREE_BASE_URL', '')

# 'sandbox' for testing, 'production' for live payments
CASHFREE_ENV = os.environ.get('CASHFREE_ENV', 'sandbox')

# Frontend URL — used to build Cashfree return_url after payment
# Set to your deployed frontend URL in production, e.g. https://kavithedal.com
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:5173')


# ─── Admin Email ──────────────────────────────────────────────────────────────
# The single email address allowed to access the admin panel (OTP-protected).
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', '')


# ─── Logging ──────────────────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING' if not DEBUG else 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING' if not DEBUG else 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}


# ─── Cloudinary for Persistent Media Storage ──────────────────────────────────
# Render filesystem is ephemeral — Cloudinary keeps book covers, PDFs, and
# author photos alive across redeploys.
# Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET in env.
# (_cloudinary_configured is computed near the top of this file, before INSTALLED_APPS)

if _cloudinary_configured:
    CLOUDINARY_STORAGE = {
        'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME'),
        'API_KEY':    os.environ.get('CLOUDINARY_API_KEY'),
        'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET'),
    }
    # Django 5.0+ removed DEFAULT_FILE_STORAGE — must use STORAGES dict.
    STORAGES['default'] = {
        'BACKEND': 'cloudinary_storage.storage.MediaCloudinaryStorage',
    }
    # Also call cloudinary.config() directly to ensure the SDK is configured
    # even if cloudinary_storage's app_settings hasn't run yet.
    try:
        import cloudinary
        cloudinary.config(
            cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
            api_key=os.environ.get('CLOUDINARY_API_KEY'),
            api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
            secure=True,
        )
    except ImportError:
        pass
    # NOTE: Do NOT set MEDIA_URL to the Cloudinary CDN root here.
    # django-cloudinary-storage 0.3.x builds file URLs as MEDIA_URL + filename,
    # which produces malformed Cloudinary URLs (missing /image/upload/ segment).
    # Correct Cloudinary URLs are built in serializers via field_file.url.
