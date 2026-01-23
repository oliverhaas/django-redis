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

## Cluster Client

For Redis Cluster deployments with server-side sharding across multiple nodes:

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:7000",  # Any cluster node
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.ClusterClient",
            "CONNECTION_FACTORY": "django_redis.pool.ClusterConnectionFactory",
        }
    }
}
```

With password and timeouts:

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:7000",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.ClusterClient",
            "CONNECTION_FACTORY": "django_redis.pool.ClusterConnectionFactory",
            "PASSWORD": "your-password",
            "SOCKET_TIMEOUT": 5,
            "SOCKET_CONNECT_TIMEOUT": 3,
        }
    }
}
```

!!! note "Cluster Behavior"
    - The cluster handles routing to the correct node automatically
    - Multi-key operations (`get_many`, `delete_many`, `set_many`) are cluster-aware and handle cross-slot keys automatically by grouping operations
    - Use hash tags like `{prefix}key` to ensure related keys go to the same slot for better performance
    - Automatic failover is handled by the cluster
    - `clear()` flushes all primary nodes in the cluster
