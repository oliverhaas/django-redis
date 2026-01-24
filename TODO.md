# django-redis-ng TODO

Features and changes we want to make.

## Compatibility

- Redis server 6.x and 7.x (redis-py 5.x)
- Python 3.12, 3.13, 3.14
- Django 5.2, 6.0

## Planned Features

- [x] Support Valkey client (valkey-py)
  - Branches: `research/valkey-py`, `research/valkey-glide`
  - Added valkey-py as optional dependency `[valkey]` and `[libvalkey]`
  - Test fixtures couple server images with client libraries (redis→redis-py, valkey→valkey-py)
  - Added native parser support (hiredis for redis-py, libvalkey for valkey-py)
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
- [x] Multiple serializer fallback for backwards compatibility on read
  - List-based SERIALIZER config: `["path.to.JSONSerializer", "path.to.PickleSerializer"]`
  - First serializer used for writing, all tried for reading
  - Exception-based fallback: tries each serializer until one succeeds
- [x] Conditional compression based on value size
  - `BaseCompressor.min_length = 256` - values below this size are not compressed
  - Subclasses can override if needed
- [ ] Consider removing IdentityCompressor
  - `_decompress()` already returns raw value when all compressors fail
  - May still be useful as explicit "no compression" config option
- [x] Benchmarks for compression/serialization overhead
  - Compression exception handling: ~0.5µs (vs ~0.06µs for magic byte check)
  - Serialization: pickle ~0.28µs, JSON ~1.03µs, exception overhead ~60% for JSON
  - Conclusion: exception-based fallback is fast enough, simpler code wins

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

## Naming / API

- [ ] Consider renaming "redis" terminology now that Valkey is supported
  - Package name: `django_redis` → `django_kvstore` or similar?
  - Class names: `RedisCache`, `get_redis_connection()`
  - Option names: `REDIS_CLIENT_CLASS`, `REDIS_CLIENT_KWARGS`
  - Would require major version bump and deprecation period
  - May not be worth the churn if "Redis" remains the dominant term
- [ ] API stability policy
  - Document what is public API vs internal
  - Semantic versioning guarantees
  - Deprecation policy (warnings for N versions before removal)

## Additional Redis Features

- [ ] Investigate Pub/Sub support
  - `publish()`, `subscribe()`, channel patterns
  - May need async support first
- [ ] Investigate Redis Streams support
  - `xadd()`, `xread()`, `xrange()`, `xlen()`, `xdel()`, `xtrim()`
  - Consumer groups: `xgroup_create()`, `xreadgroup()`, `xack()`
- [ ] Investigate Lua scripting support
  - `eval()`, `evalsha()`, `script_load()`
  - Useful for atomic operations
- [ ] Pipeline/transaction support
  - `pipeline()` context manager for batching
  - `MULTI`/`EXEC` transaction support
- [x] Blocking list operations
  - `blpop()`, `brpop()`, `blmove()` with timeout handling
- [x] Add `blocking` parameter to `cache.lock()` (like django-redis has)
  - Made signature explicit: sleep, blocking, blocking_timeout, thread_local
- [ ] JSON serializer with datetime round-trip support (optional)
  - Currently uses DjangoJSONEncoder for encoding (same as django-redis)
  - Decoding returns strings, not datetime objects (same as django-redis)
  - Could add optional auto-detection of ISO 8601 strings in the future

## Testing

- [x] Use testcontainers with Redis and Valkey images instead of Docker Compose
  - Parametrized session fixture for Redis/Valkey/redis-stack-server
- [ ] Fake cache backend (locmem-style or fakeredis) for testing without Redis
- [ ] Performance/benchmark tests
  - Measure serialization overhead
  - Measure compression overhead
  - Compare with Django builtin redis backend
  - Compare with django-redis
- [ ] Edge case coverage review
  - Large values (> 512MB)
  - Unicode edge cases
  - Connection failure scenarios
  - Timeout edge cases
- [ ] Integration tests with real Redis Cluster (multi-node)
  - Currently using single-container cluster image

## Code Quality

- [x] Full type annotations up to Django layer (user-facing typing support)
  - Added cast() for redis-py type annotations
  - Created types.py with type aliases (KeyT, TimeoutT, EncodedT, protocols)
  - Proper type signatures on cache.py methods
- [x] Enable more ruff rules (disable/exclude instead of explicit enable, like django-nested-values)
  - Using `select = ["ALL"]` with minimal ignores
  - Per-file ignores for source code and tests
  - Fixed code quality issues: ClassVar, __slots__, dict comprehensions, etc.
- [x] Stricter mypy configuration
  - Enabled error codes: return-value, union-attr, operator, misc
  - Still disabled due to redis-py: arg-type (key types), assignment (Redis/RedisCluster), type-var (zadd)
  - mypy now passes with 0 errors
- [ ] Review `[[tool.mypy.overrides]]` for optional dependencies
  - Currently using `ignore_missing_imports = true` for: lz4, xdist, backports, compression, msgpack, redis, valkey
  - As these libraries improve their type annotations, we may be able to remove some overrides
- [ ] Clean up config as changes are made
- [ ] Consider removing CacheKey
  - Marker class to prevent double-prefixing in `make_key()`
  - `make_key()` is only called internally, so double-prefixing shouldn't happen
  - May be unnecessary defensive programming
- [ ] Add docstrings incrementally
  - Currently using `"D"` ignore in ruff for docstrings
  - Start with public API methods
  - Use Google-style docstrings
- [ ] Verify py.typed marker is present for PEP 561
  - Allows type checkers to use our type hints

## Tooling/Infrastructure

- [x] Migrate to pyproject.toml with hatchling
- [x] Switch to UV for package management
- [x] MkDocs documentation with Material theme
- [x] Modern CI/CD with auto-tagging and publishing
- [x] Update CI matrix for Python 3.12-3.14 and Django 5.2-6.0
- [ ] Add SECURITY.md with security policy
  - How to report vulnerabilities
  - Supported versions
  - Security considerations (pickle, etc.)
- [ ] Document release process
  - Versioning strategy (SemVer)
  - Changelog maintenance
  - PyPI publishing workflow

## Documentation

- [ ] Migration guide from django-redis
  - Configuration differences
  - API differences
  - Feature comparison
- [ ] Migration guide from Django's builtin redis backend
  - What you gain by switching
  - Configuration mapping
- [ ] Compare features with competing packages
  - django-redis (jazzband): https://github.com/jazzband/django-redis
  - django-valkey: https://github.com/django-commons/django-valkey
  - Django builtin: django.core.cache.backends.redis
  - Document what we have that others don't, and vice versa
- [ ] Performance tuning guide
  - Connection pool sizing
  - Serializer selection
  - Compression tradeoffs
  - Replica routing
- [ ] Troubleshooting guide
  - Common errors and solutions
  - Connection issues
  - Serialization issues
- [ ] More examples/recipes
  - Session storage setup
  - Rate limiting pattern
  - Cache invalidation patterns
  - Multi-tenant caching
- [ ] Review API reference completeness
  - Ensure all public methods documented
  - Add examples for each method
  - Document all OPTIONS parameters
- [ ] Document all configuration options in one place
  - Currently spread across multiple doc pages
  - Single reference page with all OPTIONS
