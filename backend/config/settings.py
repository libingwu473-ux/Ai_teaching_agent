import os
from pathlib import Path
from datetime import timedelta
from decouple import config as env_config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = env_config('SECRET_KEY', default='django-insecure-dify-edu-secret-key-change-in-production')

DEBUG = env_config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = ['*']

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
    'corsheaders',
    'django_filters',
    # Local apps
    'apps.users',
    'apps.dify_integration',
    'apps.chat_logs',
    'apps.scoring',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
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
        'DIRS': [],
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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
]

LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'users.User'

# ─── REST Framework ───────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
}

# ─── JWT ──────────────────────────────────────────────────────
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ─── CORS ─────────────────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = False  # 必须为 False 才能支持 Authorization header 的跨域请求
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:5177',
    'http://127.0.0.1:5177',
    'http://localhost:5178',
    'http://127.0.0.1:5178',
]
CORS_ALLOW_CREDENTIALS = True

# ─── Dify Platform Config ────────────────────────────────────
# 注意：运行时配置存于数据库表 dify_config（教师端可改）；以下仅作为首次初始化的默认值。
DIFY_CONFIG = {
    'API_BASE_URL': env_config('DIFY_API_BASE_URL', default='https://dify.chat.43d.cn/v1'),
    'API_KEY': env_config('DIFY_API_KEY', default='app-Hxdaf8CIkQp7Avoysg8AtVHx'),
    'APP_ID': env_config('DIFY_APP_ID', default=''),
    'CHATFLOW_ID': env_config('DIFY_CHATFLOW_ID', default='6f0ca55a-b8ef-4f7d-a6a4-a0a3e18584ca'),
    'RESPONSE_MODE': 'streaming',
    'TIMEOUT': 60,
    'MAX_RETRIES': 3,
    'VERIFY_SSL': env_config('DIFY_VERIFY_SSL', default=False, cast=bool),
}

# ─── Scoring Engine Config ────────────────────────────────────
# 注意：运行时这些值从 DB 表 scoring_config 读取（教师端可改）；以下仅作为首次初始化的默认值。
SCORING_CONFIG = {
    'STAGE_COMPLETION_WEIGHT': 0.40,
    'SEQUENCE_ADHERENCE_WEIGHT': 0.25,
    'TIME_INVESTMENT_WEIGHT': 0.15,
    'ENGAGEMENT_WEIGHT': 0.20,
    'MIN_SESSION_MINUTES': 1,
    'MAX_SCORE': 100,
}

# ─── Sync Config ─────────────────────────────────────────────
SYNC_CONFIG = {
    'INTERVAL_MINUTES': 2,
    'BATCH_SIZE': 50,
}
