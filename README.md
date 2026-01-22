# Django Redis NG

[![PyPI version](https://img.shields.io/pypi/v/django-redis-ng.svg?style=flat)](https://pypi.org/project/django-redis-ng/)
[![Python versions](https://img.shields.io/pypi/pyversions/django-redis-ng.svg)](https://pypi.org/project/django-redis-ng/)
[![CI](https://github.com/oliverhaas/django-redis-ng/actions/workflows/ci.yml/badge.svg)](https://github.com/oliverhaas/django-redis-ng/actions/workflows/ci.yml)

Full featured Redis cache and session backend for Django (Next Generation fork).

## Installation

```console
pip install django-redis-ng
```

## Quick Start

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

## Features

- Native redis-py URL connection strings
- Pluggable clients, serializers, and compressors
- Primary/replica replication support
- Redis Sentinel support
- Distributed locks
- Comprehensive test suite

## Documentation

Full documentation at [oliverhaas.github.io/django-redis-ng](https://oliverhaas.github.io/django-redis-ng/)

## About This Fork

django-redis-ng is a "Next Generation" fork of [django-redis](https://github.com/jazzband/django-redis). It maintains API compatibility while enabling faster iteration on improvements. The goal is to merge changes upstream when possible.

## Requirements

- Python 3.9+
- Django 4.2+
- redis-py 4.0.2+

## License

BSD-3-Clause
