from pathlib import Path
import os
from dotenv import load_dotenv
import logging
import dj_database_url

# Initialize logger
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-8$5$hs$_hs$_hs$_hs$_hs$_hs$_hs$_hs$_hs$_hs$_hs$_hs$')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = ['https://alya-166a.onrender.com/', 'localhost', '127.0.0.1','alya-166a.onrender.com','*']

CSRF_TRUSTED_ORIGINS = [
    'https://alya-166a.onrender.com',
    'http://localhost:8000',
    'http://127.0.0.1:8000'
]

# Ajouter SSL_LINK aux origines de confiance s'il est défini
if os.getenv('SSL_LINK'):
    CSRF_TRUSTED_ORIGINS.append(os.getenv('SSL_LINK'))

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'alyawebapp'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'alyaprojet.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'alyawebapp/templates'),
        ],
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

WSGI_APPLICATION = 'alyaprojet.wsgi.application'

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases
DATABASES = {
    'default': dj_database_url.config(default=os.getenv('DATABASE_URL'))
}
#DATABASES = {
#  'default': {
#        'ENGINE': 'django.db.backends.sqlite3',
#        'NAME': BASE_DIR / 'db.sqlite3',
#    }
#}

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

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

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'fr-fr'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'alyawebapp/static'),
]

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'alyawebapp.CustomUser'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'compte'
LOGOUT_REDIRECT_URL = 'home'

# OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')  # Load from .env file

ADMIN_STYLE = {
    'css': 'admin/css/custom_admin.css',
}

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
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'alyawebapp': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

# HubSpot Configuration
HUBSPOT_CLIENT_ID = os.getenv('HUBSPOT_CLIENT_ID')
HUBSPOT_CLIENT_SECRET = os.getenv('HUBSPOT_CLIENT_SECRET')
HUBSPOT_REDIRECT_URI = os.getenv('HUBSPOT_REDIRECT_URI')

# Vérification au démarrage
if not all([HUBSPOT_CLIENT_ID, HUBSPOT_CLIENT_SECRET, HUBSPOT_REDIRECT_URI]):
    logger.warning("Configuration HubSpot incomplète!")

# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 86400  # 24 heures en secondes
SESSION_COOKIE_SECURE = False  # Mettre à True en production

# Trello Configuration
TRELLO_API_KEY = os.getenv('TRELLO_API_KEY')
TRELLO_API_SECRET = os.getenv('TRELLO_API_SECRET')
TRELLO_REDIRECT_URI = os.getenv('TRELLO_REDIRECT_URI', default='http://localhost:8000/trello/callback/')
TRELLO_API_URL = 'https://api.trello.com/1'

# Mailchimp Configuration
MAILCHIMP_CLIENT_ID = os.getenv('MAILCHIMP_CLIENT_ID')
MAILCHIMP_CLIENT_SECRET = os.getenv('MAILCHIMP_CLIENT_SECRET')
MAILCHIMP_REDIRECT_URI = os.getenv('MAILCHIMP_REDIRECT_URI')
MAILCHIMP_AUTHORIZATION_URL = 'https://login.mailchimp.com/oauth2/authorize'
MAILCHIMP_TOKEN_URL = 'https://login.mailchimp.com/oauth2/token'

# Vérification de la configuration Mailchimp
if not all([MAILCHIMP_CLIENT_ID, MAILCHIMP_CLIENT_SECRET, MAILCHIMP_REDIRECT_URI]):
    logger.warning("⚠️ Configuration Mailchimp incomplète!")
    logger.debug(f"MAILCHIMP_CLIENT_ID: {MAILCHIMP_CLIENT_ID}")
    logger.debug(f"MAILCHIMP_REDIRECT_URI: {MAILCHIMP_REDIRECT_URI}")
