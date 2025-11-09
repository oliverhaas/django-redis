"""
Test configuration for Valkey client.

This configuration tests the DefaultValkeyClient which uses valkey-py
instead of redis-py. The valkey:// URL scheme triggers automatic client
selection.
"""

SECRET_KEY = "django_tests_secret_key"
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        # Using valkey:// scheme to auto-detect DefaultValkeyClient
        "LOCATION": ["valkey://127.0.0.1:6379?db=1", "valkey://127.0.0.1:6379?db=1"],
        # Client class will be auto-detected from URL scheme
        "OPTIONS": {},
    },
    "doesnotexist": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "valkey://127.0.0.1:56379?db=1",
        "OPTIONS": {},
    },
    "sample": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "valkey://127.0.0.1:6379:1,valkey://127.0.0.1:6379:1",
        "OPTIONS": {},
    },
    "with_prefix": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "valkey://127.0.0.1:6379?db=1",
        "OPTIONS": {},
        "KEY_PREFIX": "test-prefix",
    },
}

# Include `django.contrib.auth` and `django.contrib.contenttypes` for mypy /
# django-stubs.

# See:
# - https://github.com/typeddjango/django-stubs/issues/318
# - https://github.com/typeddjango/django-stubs/issues/534
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
]

USE_TZ = False
