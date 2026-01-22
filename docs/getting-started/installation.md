# Installation

## Requirements

- Python 3.9+
- Django 4.2+
- redis-py 4.0.2+
- Redis server 2.8+

## Install with pip

```console
pip install django-redis-ng
```

## Install with hiredis (recommended)

For better performance, install with the hiredis parser:

```console
pip install django-redis-ng[hiredis]
```

The hiredis package provides a C-based parser that can significantly improve performance when parsing Redis replies.

## Verify Installation

```python
>>> import django_redis
>>> django_redis.__version__
'6.0.0'
```
