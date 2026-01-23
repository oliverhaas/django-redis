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
- [x] Add more Redis method support via mixins
  - ListMixin: lpush, rpush, lpop, rpop, lrange, lindex, llen, lrem, ltrim, lset, linsert
  - SetMixin: sadd, scard, sdiff, sdiffstore, sinter, sinterstore, sismember, smembers, smove, spop, srandmember, srem, sscan, sscan_iter, sunion, sunionstore
  - HashMixin: hset, hdel, hlen, hkeys, hexists
  - SortedSetMixin: zadd, zcard, zcount, zincrby, zpopmax, zpopmin, zrange, zrangebyscore, zrank, zrem, zremrangebyscore, zrevrange, zrevrangebyscore, zscore
  - Fixed hash method parameter semantics (key/field vs name/key)
- [ ] Add more methods to existing mixins as needed (hget, hgetall, lpos, etc.)
- [ ] Use Python 3.14 builtin zstd when available (with backport fallback)

## Compression & Serialization

- [ ] Multiple compressor fallback for backwards compatibility on read
  - e.g., `["zstd", None]` tries zstd first, falls back to uncompressed
  - Allows safe migration when changing compression settings
  - Same pattern for serializers (e.g., migrate from pickle to msgpack)
- [ ] Conditional compression based on value size
  - Only compress values above a threshold (e.g., 1KB)
  - With fallback list like `["zstd", None]`, reading works reliably
  - Alternative: detect compression by inspecting value (magic bytes, length heuristics)
- [ ] Benchmarks for compression/serialization overhead
  - Measure latency impact of different compressors
  - Find optimal threshold for conditional compression
  - Compare serializer performance (pickle vs msgpack vs json)

## Client Architecture

- [ ] Add ClusterClient for Redis Cluster support
  - Native Redis Cluster (since Redis 3.0, 2015) uses server-side sharding
  - Subclass DefaultClient, override `get_next_client_index()` (return 0) and `connect()` (validate RedisCluster)
  - Add ClusterConnectionFactory using `redis.cluster.RedisCluster`
  - Multi-key ops (mget, set_many, delete_many) need hash tags `{prefix}key` for same-slot
  - Add cluster container (bitnami/redis-cluster, 3 nodes) to testcontainers fixtures
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
