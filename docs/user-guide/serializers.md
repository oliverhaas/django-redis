# Serializers

django-redis supports pluggable serializers for data before sending to Redis.

## Pickle Serializer (Default)

The default serializer uses Python's `pickle` module:

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # Uses pickle by default
        }
    }
}
```

### Configure Pickle Version

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "PICKLE_VERSION": -1  # Highest protocol available
        }
    }
}
```

## JSON Serializer

For JSON-serializable data only:

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SERIALIZER": "django_redis.serializers.json.JSONSerializer",
        }
    }
}
```

## MsgPack Serializer

Requires the `msgpack` library:

```console
pip install msgpack
```

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SERIALIZER": "django_redis.serializers.msgpack.MSGPackSerializer",
        }
    }
}
```

## Custom Serializer

Create a custom serializer by implementing `dumps` and `loads` methods:

```python
from django_redis.serializers.base import BaseSerializer

class MySerializer(BaseSerializer):
    def dumps(self, value):
        # Convert value to bytes
        return my_encode(value)

    def loads(self, value):
        # Convert bytes to value
        return my_decode(value)
```

Then configure:

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "SERIALIZER": "myapp.serializers.MySerializer",
        }
    }
}
```
