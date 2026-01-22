# Django Redis NG

Full featured Redis cache and session backend for Django (Next Generation fork).

[![PyPI version](https://img.shields.io/pypi/v/django-redis-ng.svg?style=flat)](https://pypi.org/project/django-redis-ng/)
[![Python versions](https://img.shields.io/pypi/pyversions/django-redis-ng.svg)](https://pypi.org/project/django-redis-ng/)
[![Django versions](https://img.shields.io/pypi/frameworkversions/django/django-redis-ng.svg)](https://pypi.org/project/django-redis-ng/)

## Why django-redis-ng?

- Uses native redis-py URL notation connection strings
- Pluggable clients
- Pluggable parsers
- Pluggable serializers
- Primary/replica support in the default client
- Comprehensive test suite
- Used in production in several projects as cache and session storage
- Supports infinite timeouts
- Facilities for raw access to Redis client/connection pool
- Highly configurable (can emulate memcached exception behavior, for example)
- Unix sockets supported by default

## Requirements

- Python 3.9+
- Django 4.2+
- redis-py 4.0.2+
- Redis server 2.8+

## Quick Start

Install with pip:

```console
pip install django-redis-ng
```

Configure as cache backend:

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}
```

## About This Fork

django-redis-ng is a "Next Generation" fork of the original [django-redis](https://github.com/jazzband/django-redis) project. It aims to be a drop-in replacement while allowing for faster iteration on new features and improvements.

The goal is to eventually merge changes back upstream when possible.

## License

BSD-3-Clause License. See [LICENSE](https://github.com/oliverhaas/django-redis-ng/blob/main/LICENSE) for details.
