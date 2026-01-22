# Changelog

## 6.0.0 (Unreleased)

This is the first release of django-redis-ng, a fork of django-redis.

### Changes from django-redis

- Migrated to `pyproject.toml` with hatchling build system
- Switched to UV for package management
- Modernized CI/CD with GitHub Actions
- Added MkDocs documentation with Material theme
- Package name changed to `django-redis-ng` (import namespace remains `django_redis`)

### Features

All features from django-redis 5.x are included:

- Full-featured Redis cache backend
- Session backend support
- Pluggable clients (Default, Shard, Herd, Sentinel)
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
