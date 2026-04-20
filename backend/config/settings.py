"""
Django settings for RankToRole project.
"""

import os
from datetime import timedelta
from pathlib import Path

import dj_database_url

# ---------------------------------------------------------------------------
# Base directory
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-local-dev-fallback-key-do-not-use-in-production'
)

DEBUG = os.environ.get('DEBUG', 'True') == 'True'

_allowed_hosts_env = os.environ.get('ALLOWED_HOSTS', '')
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts_env.split(',')
                 if h.strip()] or ['localhost', '127.0.0.1']

if not DEBUG and ALLOWED_HOSTS == ['localhost', '127.0.0.1']:
    import warnings
    warnings.warn(
        "ALLOWED_HOSTS is not set. Defaulting to localhost only. "
        "Set ALLOWED_HOSTS in your production .env.",
        stacklevel=2,
    )

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------
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
    'social_django',
    # Local apps
    'translate_app',
    'user_app',
    'contact_app',
    'onet_app',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'social_django.middleware.SocialAuthExceptionMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
_database_url = os.environ.get('DATABASE_URL', '')

if _database_url:
    DATABASES = {
        'default': dj_database_url.parse(_database_url, conn_max_age=600)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = 'user_app.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTHENTICATION_BACKENDS = [
    'social_core.backends.google.GoogleOAuth2',
    'django.contrib.auth.backends.ModelBackend',
]

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'EXCEPTION_HANDLER': 'translate_app.throttles.tiered_throttle_exception_handler',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'login': '5/min',
        'register': '5/hour',
        'user_draft': '1/day',
        'user_chat': '10/day',
        'user_upload': '3/day',
        'user_finalize': '3/day',
        'user_onet': '10/day',
        'user_recon_enrich': '15/day',
        'billing_checkout': '5/min',
    },
}

# ---------------------------------------------------------------------------
# Cache — Redis when REDIS_URL is set, LocMemCache fallback otherwise.
# Shared across gunicorn workers via Redis. Tests override to LocMemCache
# via root conftest autouse fixture.
# ---------------------------------------------------------------------------
REDIS_URL = os.environ.get('REDIS_URL', '')

if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'SOCKET_CONNECT_TIMEOUT': 5,
                'SOCKET_TIMEOUT': 5,
                # Fail loud on Redis outages so healthcheck catches them
                # instead of silently bypassing throttles. Do not flip to True
                # without adding view-level graceful degradation first.
                'IGNORE_EXCEPTIONS': False,
            },
            'KEY_PREFIX': 'rtr',
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'ranktorole-cache',
        }
    }

# ---------------------------------------------------------------------------
# Tiered Throttle Rates
# ---------------------------------------------------------------------------
# TieredThrottle subclasses look up rates here by scope + user.tier.
# Falls back to DEFAULT_THROTTLE_RATES if tier not found.
TIERED_THROTTLE_RATES = {
    # Per-user daily caps by tier. Rebalanced for launch based on
    # per-draft cost (~$0.057 Sonnet 4) and realistic pro usage patterns
    # (~10-15 drafts across an active job search, burst days of 3-5).
    # Global 500/day ceiling in RECON_ENRICH_DAILY_CEILING caps total
    # spend regardless of these values.
    'user_upload':       {'free': '3/day',  'pro': '20/day'},
    'user_draft':        {'free': '1/day',  'pro': '15/day'},
    'user_chat':         {'free': '10/day', 'pro': '75/day'},
    'user_finalize':     {'free': '3/day',  'pro': '20/day'},
    'user_onet':         {'free': '10/day', 'pro': '30/day'},
    'user_recon_enrich': {'free': '15/day', 'pro': '25/day'},
}

# ---------------------------------------------------------------------------
# Recon Enrichment — cost controls
# ---------------------------------------------------------------------------
RECON_ENRICH_CACHE_TTL = 7 * 24 * 60 * 60  # 7 days in seconds

RECON_ENRICH_DAILY_CEILING = int(os.environ.get('RECON_ENRICH_DAILY_CEILING', '500'))

RECON_ENRICH_TIMEOUT_SECONDS = 15.0

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {name} {message}',
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
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'translate_app': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'user_app': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'onet_app': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ---------------------------------------------------------------------------
# SimpleJWT
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
_cors_origins_env = os.environ.get('CORS_ALLOWED_ORIGINS', '')
CORS_ALLOWED_ORIGINS = [
    o.strip() for o in _cors_origins_env.split(',') if o.strip()
] or [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]

CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------------
# CSRF Trusted Origins — required by Django 4.2+ behind HTTPS proxy
# ---------------------------------------------------------------------------
_csrf_trusted_env = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in _csrf_trusted_env.split(',') if o.strip()
] or [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]

if not DEBUG and not _cors_origins_env.strip():
    import warnings
    warnings.warn(
        "CORS_ALLOWED_ORIGINS is not set. All browser requests will "
        "be blocked in production. Set CORS_ALLOWED_ORIGINS in your "
        ".env to your EC2 public URL.",
        stacklevel=2,
    )

# ---------------------------------------------------------------------------
# Social Auth (Google OAuth 2.0)
# ---------------------------------------------------------------------------
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ.get('GOOGLE_CLIENT_ID', '')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
GOOGLE_OAUTH_REDIRECT_URI = os.environ.get(
    'GOOGLE_OAUTH_REDIRECT_URI',
    'http://localhost:5173/auth/google/callback',
)

SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.user.create_user',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
)

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# ---------------------------------------------------------------------------
# Default primary key field type
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# External API keys
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
ONET_USERNAME = os.environ.get('ONET_USERNAME', '')
ONET_PASSWORD = os.environ.get('ONET_PASSWORD', '')
ONET_API_KEY = os.environ.get('ONET_API_KEY', '')

# ---------------------------------------------------------------------------
# Stripe Billing
# ---------------------------------------------------------------------------
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
STRIPE_PRICE_ID = os.environ.get('STRIPE_PRICE_ID', '')  # Pro plan recurring price
STRIPE_CHECKOUT_SUCCESS_URL = os.environ.get(
    'STRIPE_CHECKOUT_SUCCESS_URL',
    'http://localhost:5173/billing/success?session_id={CHECKOUT_SESSION_ID}',
)
STRIPE_CHECKOUT_CANCEL_URL = os.environ.get(
    'STRIPE_CHECKOUT_CANCEL_URL',
    'http://localhost:5173/billing/cancel',
)

# Free-tier daily usage limits (enforced by IsProOrUnderLimit permission).
# Pro users (subscription_status == 'active') bypass these entirely.
FREE_TIER_DAILY_LIMITS = {
    'resume_tailor_count': 1,
}

# Free-tier permanent (non-resetting) per-resume chat turn limit.
# Enforced by ChatTurnLimit against resume.chat_turn_count.
FREE_TIER_CHAT_LIMIT = 10

# ---------------------------------------------------------------------------
# Security headers — all gated on not DEBUG, inert in local dev
# ---------------------------------------------------------------------------

# Required for Nginx + EC2: tells Django that X-Forwarded-Proto: https
# means the original request was HTTPS (Nginx terminates SSL internally)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Redirect HTTP → HTTPS at Django level as a backstop behind Nginx
SECURE_SSL_REDIRECT = not DEBUG

# Flip cookies to Secure=True in production
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# HSTS — set to 0 in dev; activate to 31536000 ONLY after SSL cert is
# confirmed working on EC2, or browsers will be locked out for 1 year
SECURE_HSTS_SECONDS = 0 if DEBUG else 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

# These two are safe in dev — just add response headers, no redirects
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
