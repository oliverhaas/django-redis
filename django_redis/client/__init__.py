# Unified cache clients
from django_redis.client.cluster import (
    ClusterCacheClient,  # Backwards compat alias for RedisClusterCacheClient
    KeyValueClusterCacheClient,
    RedisClusterCacheClient,
    ValkeyClusterCacheClient,
)
from django_redis.client.default import (
    KeyValueCacheClient,
    RedisCacheClient,
    ValkeyCacheClient,
)
from django_redis.client.sentinel import (
    KeyValueSentinelCacheClient,
    RedisSentinelCacheClient,
    SentinelCacheClient,  # Backwards compat alias for RedisSentinelCacheClient
    ValkeySentinelCacheClient,
)

__all__ = [
    # Generic base classes
    "KeyValueCacheClient",
    "KeyValueSentinelCacheClient",
    "KeyValueClusterCacheClient",
    # Redis implementations
    "RedisCacheClient",
    "RedisSentinelCacheClient",
    "RedisClusterCacheClient",
    # Backwards compat aliases
    "SentinelCacheClient",
    "ClusterCacheClient",
    # Valkey implementations
    "ValkeyCacheClient",
    "ValkeySentinelCacheClient",
    "ValkeyClusterCacheClient",
]
