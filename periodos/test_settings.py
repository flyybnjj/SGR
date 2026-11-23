from config.settings import *  # noqa: F403

INSTALLED_APPS = [*INSTALLED_APPS, 'periodos'] if 'periodos' not in INSTALLED_APPS else INSTALLED_APPS
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:', 'OPTIONS': {'transaction_mode': 'IMMEDIATE'}}}
ROOT_URLCONF = 'config.urls'
STORAGES = {'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}}
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
