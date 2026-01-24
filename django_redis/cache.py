"""Cache module - provides RedisCache as an alias to RedisCacheClient."""

from django_redis.client import RedisCacheClient

# Alias for existing BACKEND configurations using django_redis.cache.RedisCache
RedisCache = RedisCacheClient

__all__ = ["RedisCache"]
