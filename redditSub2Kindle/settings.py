import json
from pathlib import Path

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

DJANGO_COLORS = True

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

try:
	with open(Path(__file__).parent / Path('secret.txt'), 'r') as f:
		# SECURITY WARNING: keep the secret key used in production secret!
		SECRET_KEY = f.read()
except FileNotFoundError as e:
	raise Exception(f'Create secret.txt in {Path(__file__).parent} containing some arbitrary string')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
#
ALLOWED_HOSTS = [
	'127.0.0.1',
	'10.0.10.10',
	'10.10.10.10',
]

INTERNAL_IPS = ALLOWED_HOSTS

# Application definition
INSTALLED_APPS = [
	'website',
	'bootstrap4',
	'django.contrib.admin',
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.messages',
	'django.contrib.staticfiles',
]

MIDDLEWARE = [
	'django.middleware.security.SecurityMiddleware',
	'django.contrib.sessions.middleware.SessionMiddleware',
	'django.middleware.common.CommonMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
	'django.middleware.clickjacking.XFrameOptionsMiddleware',
	'csp.middleware.CSPMiddleware',
	'website.middleware.Headers',
]

ROOT_URLCONF = 'redditSub2Kindle.urls'

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

WSGI_APPLICATION = 'redditSub2Kindle.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = {
	'default': {
		'ENGINE': 'django.db.backends.sqlite3',
		'NAME': BASE_DIR / 'db.sqlite3',
	}
}

CACHES = {
	'default': {
		'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
		'LOCATION': 'django_cache',
		'OPTIONS': {
			'MAX_ENTRIES': 1000000000
		}
	}
}


#import logging

#handler = logging.StreamHandler()
#handler.setLevel(logging.DEBUG)
#for logger_name in ("praw", "prawcore"):
#   logger = logging.getLogger(logger_name)
#   logger.setLevel(logging.DEBUG)
#   logger.addHandler(handler)


# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = []


# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = False

USE_L10N = False

USE_TZ = False

SESSION_COOKIE_SAMESITE = 'Strict'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

STATIC_URL = 'static/'

SHORT_DATE_FORMAT = 'Y-m-d'
SHORT_DATETIME_FORMAT = 'Y-m-d H:M:S'
TIME_FORMAT = 'H:M:S'

SECURE_BROWSER_XSS_FILTER = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# You suck if your domain can't do this, git gud, https for lyf
SECURE_HSTS_PRELOAD = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365 * 3

SECURE_REFERRER_POLICY = 'same-origin'

CSP_DEFAULT_SRC = [ "'none'" ]
CSP_IMG_SRC = [ "'self'" ]
CSP_STYLE_SRC = [ "'self'" ]
CSP_SCRIPT_SRC = [ "'self'" ]
CSP_CONNECT_SRC = [ "'self'" ]
CSP_FONT_SRC = [ "'self'" ]

CSP_BASE_URI = [ "'none'" ]
CSP_FORM_ACTION = [ "'self'" ]
CSP_FRAME_ANCESTORS = [ "'none'" ]
CSP_NAVIGATE_TO = [ "'self'", 'https://www.reddit.com', 'https://i.reddit.com' ]

CSP_SANDBOX = [
	'allow-downloads',
	'allow-scripts',
	'allow-forms',
	'allow-popups',
	'allow-same-origin',
]

CSP_REPORT_TO = [ 'csp' ]

BOOTSTRAP4 = {
	"css_url": "/static/bootstrap.css",
	'theme_url': '/static/custom.css',
	"javascript_url": "/static/bootstrap.js",
	"popper_url": "/static/popper.js",
	'jquery_url': '/static/jquery-3.5.1.js',
	'include_jquery': True,
}

try:
	with open(Path(__file__).parent / Path('sentry.json'), 'r') as f:
		# SECURITY WARNING: keep the secret key used in production secret!
		SENTRY_CONFIG = json.load(f)
except FileNotFoundError as e:
	raise Exception(f'Create sentry.json in {Path(__file__).parent} containing a dsn')


def trace_sampler_filter(sampling_context):
	if sampling_context['wsgi_environ']['PATH_INFO'] == '/favicon.ico':
		return 0

	return 1.0


def strip_sensitive_data(event, hint):
	# modify event here
	return event

sentry_sdk.init(
	dsn=SENTRY_CONFIG['dsn'],
	integrations=[DjangoIntegration()],

	traces_sampler=trace_sampler_filter,

	# If you wish to associate users to errors (assuming you are using
	# django.contrib.auth) you may enable sending PII data.
	send_default_pii=True,

	with_locals=False,
)
