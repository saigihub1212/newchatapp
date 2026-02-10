"""
Django settings for chat_project project.
"""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY
# In production, override this via environment variable DJANGO_SECRET_KEY
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "change-this-in-production-very-secret-key")

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "13.50.236.152"]

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"


# APPLICATIONS
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # WebSockets
    'channels',

    # CORS
    'corsheaders',

    # Local app
    'chat_backend',

    # DRF
    'rest_framework',
]

# MIDDLEWARE
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',

    # CORS (must be high, before CommonMiddleware)
    'corsheaders.middleware.CorsMiddleware',

    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',

    # ⚠️ KEEP THIS — but we DISABLE DRF AUTH BELOW
    'django.contrib.auth.middleware.AuthenticationMiddleware',

    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'chat_project.urls'

# TEMPLATES
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ASGI / CHANNELS
ASGI_APPLICATION = 'chat_project.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

# WSGI (not used, but Django needs it)
WSGI_APPLICATION = 'chat_project.wsgi.application'

# DATABASE
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# PASSWORD VALIDATION (not really used since you use custom auth)
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# INTERNATIONALIZATION
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# STATIC FILES
STATIC_URL = 'static/'

# MEDIA FILES (for chat attachments)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# DEFAULT PRIMARY KEY FIELD
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CORS
# For development, allow all origins. Change to explicit list in production.
CORS_ALLOW_ALL_ORIGINS = True

# 🔥🔥🔥 VERY IMPORTANT FIX 🔥🔥🔥
# Disable Django + DRF authentication completely
# Because you use CUSTOM JWT + MyUser (not Django User)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
}
