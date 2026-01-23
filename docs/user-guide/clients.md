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
