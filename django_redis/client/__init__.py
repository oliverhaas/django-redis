# Unified cache clients
from django_redis.client.base import (
    # Generic base classes
    KeyValueCacheClient,
    KeyValueClusterCacheClient,
    KeyValueSentinelCacheClient,
    # Redis implementations
    ClusterCacheClient,  # Backwards compat alias for RedisClusterCacheClient
    RedisCacheClient,
    RedisClusterCacheClient,
    RedisSentinelCacheClient,
    SentinelCacheClient,  # Backwards compat alias for RedisSentinelCacheClient
    # Valkey implementations
    ValkeyCacheClient,
    ValkeyClusterCacheClient,
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
