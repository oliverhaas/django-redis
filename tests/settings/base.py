"""Base Django settings for tests."""

SECRET_KEY = "django_tests_secret_key"

# Include django.contrib.auth and django.contrib.contenttypes for mypy/django-stubs
# See: https://github.com/typeddjango/django-stubs/issues/318
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
]

USE_TZ = False

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# HerdClient timeout setting (used for thundering herd protection)
CACHE_HERD_TIMEOUT = 2

# Base CACHES configuration - overridden by test fixtures for parametrized tests.
# The 'doesnotexist' cache points to an invalid port for testing exception handling.
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379?db=1",
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    },
    "doesnotexist": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:56379?db=1",
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    },
    "with_prefix": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379?db=1",
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "KEY_PREFIX": "test-prefix",
    },
}
