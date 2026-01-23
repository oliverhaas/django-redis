# django-redis-ng TODO

Features and changes we want to make.

## Compatibility

- Redis server 6.x and 7.x (redis-py 5.x)
- Python 3.12, 3.13, 3.14
- Django 5.2, 6.0

## Planned Features

- [ ] Support Valkey client (valkey-py)
  - Branches: `research/valkey-py`, `research/valkey-glide`
- [ ] Add async Django cache interface (official Django async cache API)
  - Branch: `feat/async-support`
- [ ] Add async API for all other methods
- [ ] Full compatibility with Django's builtin Redis backend (django.core.cache.backends.redis)
  - Drop-in replacement with extended functionality
  - Match configuration options where applicable
- [x] Add more Redis method support via mixins
  - ListMixin: lpush, rpush, lpop, rpop, lrange, lindex, llen, lrem, ltrim, lset, linsert, lpos, lmove
  - SetMixin: sadd, scard, sdiff, sdiffstore, sinter, sinterstore, sismember, smembers, smove, spop, srandmember, srem, sscan, sscan_iter, sunion, sunionstore
  - HashMixin: hset, hdel, hlen, hkeys, hexists, hget, hgetall, hmget, hmset, hincrby, hincrbyfloat, hsetnx, hvals
  - SortedSetMixin: zadd, zcard, zcount, zincrby, zpopmax, zpopmin, zrange, zrangebyscore, zrank, zrem, zremrangebyscore, zrevrange, zrevrangebyscore, zscore, zrevrank, zmscore, zremrangebyrank
  - Fixed hash method parameter semantics (key/field vs name/key)
- [x] Use Python 3.14 builtin zstd when available (with backport fallback)
  - Uses `compression.zstd` on Python 3.14+, `backports.zstd` on older versions

## Compression & Serialization

- [x] Multiple compressor fallback for backwards compatibility on read
  - List-based COMPRESSOR config: `["path.to.ZstdCompressor", "path.to.GzipCompressor"]`
  - First compressor used for writing, all tried for reading
  - Exception-based fallback: tries each compressor until one succeeds
  - Same pattern could be added for serializers later (e.g., migrate from pickle to msgpack)
- [x] Conditional compression based on value size
  - `BaseCompressor.min_length = 256` - values below this size are not compressed
  - Subclasses can override if needed
- [ ] Consider removing IdentityCompressor
  - `_decompress()` already returns raw value when all compressors fail
  - May still be useful as explicit "no compression" config option
- [ ] Benchmarks for compression/serialization overhead
  - Measure latency impact of different compressors
  - Compare serializer performance (pickle vs msgpack vs json)

## Client Architecture

- [x] Add ClusterClient for Redis Cluster support
  - ClusterClient subclasses DefaultClient
  - ClusterConnectionFactory using `redis.cluster.RedisCluster`
  - Multi-key ops (`get_many`, `delete_many`, `set_many`) handle cross-slot keys by grouping
  - Key iteration (`keys`, `iter_keys`, `delete_pattern`) scans all primary nodes
  - `clear()` flushes all primary nodes
  - 30 unit tests for ClusterClient and ClusterConnectionFactory
  - Note: Hash tags `{prefix}key` still recommended for performance (fewer round-trips)
- [x] Remove ShardClient (obsolete client-side sharding from pre-Cluster era)
- [x] Remove HerdClient (thundering herd protection)
  - Complex implementation that packed timeout with value
  - Didn't support incr/decr and many other methods
  - If needed, could be re-implemented as optional middleware in the future

## Testing

- [x] Use testcontainers with Redis and Valkey images instead of Docker Compose
  - Parametrized session fixture for Redis/Valkey/redis-stack-server
- [ ] Fake cache backend (locmem-style or fakeredis) for testing without Redis

## Code Quality

- [ ] Full type annotations up to Django layer (user-facing typing support)
  - 73 mypy errors remaining
- [ ] Enable more ruff rules (disable/exclude instead of explicit enable, like django-nested-values)
- [ ] Stricter mypy configuration
- [ ] Clean up config as changes are made

## Tooling/Infrastructure

- [x] Migrate to pyproject.toml with hatchling
- [x] Switch to UV for package management
- [x] MkDocs documentation with Material theme
- [x] Modern CI/CD with auto-tagging and publishing
- [x] Update CI matrix for Python 3.12-3.14 and Django 5.2-6.0
