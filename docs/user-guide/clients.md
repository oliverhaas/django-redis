# Pluggable Clients

django-redis provides several pluggable client implementations for different use cases.

## Default Client

The default client supports primary/replica replication:

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": [
            "redis://127.0.0.1:6379/1",  # Primary
            "redis://127.0.0.1:6378/1",  # Replica
        ],
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}
```

!!! warning
    Replication setup is not heavily tested in production environments.

## Shard Client

Client-side sharding across multiple Redis instances:

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": [
            "redis://127.0.0.1:6379/1",
            "redis://127.0.0.1:6379/2",
        ],
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.ShardClient",
        }
    }
}
```

!!! warning
    Shard client is experimental. Use with caution in production.

## Herd Client

Helps deal with the [thundering herd problem](https://en.wikipedia.org/wiki/Thundering_herd_problem):

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.HerdClient",
        }
    }
}
```

### Herd Client Settings

- `CACHE_HERD_TIMEOUT`: Default herd timeout (default: 60 seconds)

## Sentinel Client

For Redis Sentinel high availability setups. See [Sentinel](sentinel.md) for detailed configuration.

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://service_name/db",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.SentinelClient",
            "SENTINELS": [
                ("sentinel-1", 26379),
                ("sentinel-2", 26379),
            ],
        },
    },
}
```
