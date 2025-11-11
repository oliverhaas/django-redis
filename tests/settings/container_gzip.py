"""Container-based settings with gzip compression."""

import os

SECRET_KEY = "django_tests_secret_key"

# Get Redis connection info from environment variables set by conftest.py
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": [
            f"redis://{REDIS_HOST}:{REDIS_PORT}?db=2",
            f"redis://{REDIS_HOST}:{REDIS_PORT}?db=2",
        ],
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "COMPRESSOR": "django_redis.compressors.gzip.GzipCompressor",
        },
    },
    "doesnotexist": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:56379?db=2",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "COMPRESSOR": "django_redis.compressors.gzip.GzipCompressor",
        },
    },
    "sample": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}?db=2,redis://{REDIS_HOST}:{REDIS_PORT}?db=2",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "COMPRESSOR": "django_redis.compressors.gzip.GzipCompressor",
        },
    },
    "with_prefix": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}?db=2",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "COMPRESSOR": "django_redis.compressors.gzip.GzipCompressor",
        },
        "KEY_PREFIX": "test-prefix",
    },
}

INSTALLED_APPS = ["django.contrib.sessions"]

USE_TZ = False
