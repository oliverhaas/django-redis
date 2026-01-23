# Changelog

## 6.0.0 (Unreleased)

This is the first release of django-redis-ng, a fork of django-redis.

### Changes from django-redis

- Migrated to `pyproject.toml` with hatchling build system
- Switched to UV for package management
- Modernized CI/CD with GitHub Actions
- Added MkDocs documentation with Material theme
- Package name changed to `django-redis-ng` (import namespace remains `django_redis`)
- Removed ShardClient and HerdClient (not commonly used, untested)
- Tests now use testcontainers instead of docker-compose

### New Features

- **ClusterClient**: New client for Redis Cluster deployments with server-side sharding
- **Hash operations**: `hset`, `hdel`, `hexists`, `hget`, `hgetall`, `hincrby`, `hincrbyfloat`, `hlen`, `hmget`, `hmset`, `hsetnx`, `hvals`
- **Sorted set operations**: `zadd`, `zcard`, `zcount`, `zincrby`, `zrange`, `zrangebyscore`, `zrank`, `zrevrank`, `zrem`, `zremrangebyrank`, `zscore`, `zmscore`
- **List operations**: `llen`, `lpush`, `rpush`, `lpop`, `rpop`, `lindex`, `lrange`, `lset`, `ltrim`, `lpos`, `lmove`

### Features

All features from django-redis 5.x are included:

- Full-featured Redis cache backend
- Session backend support
- Pluggable clients (Default, Sentinel, Cluster)
- Pluggable serializers (Pickle, JSON, MsgPack)
- Pluggable compressors (Zlib, Gzip, LZMA, LZ4, Zstandard)
- Connection pooling
- Primary/replica replication
- Redis Sentinel support
- Distributed locks
- TTL operations
- Bulk key operations

---

## Previous Releases

For the changelog of the original django-redis project, see the [django-redis repository](https://github.com/jazzband/django-redis/blob/master/CHANGELOG.rst).
