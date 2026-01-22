# API Reference

## Cache Methods

### Standard Django Cache Methods

All standard Django cache methods are supported:

| Method | Description |
|--------|-------------|
| `get(key, default=None)` | Get a value |
| `set(key, value, timeout=DEFAULT)` | Set a value |
| `delete(key)` | Delete a key |
| `get_many(keys)` | Get multiple values |
| `set_many(mapping, timeout=DEFAULT)` | Set multiple values |
| `delete_many(keys)` | Delete multiple keys |
| `clear()` | Clear the cache |
| `has_key(key)` | Check if key exists |
| `incr(key, delta=1)` | Increment a value |
| `decr(key, delta=1)` | Decrement a value |
| `close()` | Close connections |

### Extended Methods

django-redis adds these Redis-specific methods:

| Method | Description |
|--------|-------------|
| `ttl(key)` | Get TTL in seconds |
| `pttl(key)` | Get TTL in milliseconds |
| `expire(key, timeout)` | Set expiration in seconds |
| `pexpire(key, timeout)` | Set expiration in milliseconds |
| `expire_at(key, when)` | Set expiration at datetime |
| `pexpire_at(key, when)` | Set expiration at datetime (ms precision) |
| `persist(key)` | Remove expiration |
| `lock(key, ...)` | Get a distributed lock |
| `keys(pattern)` | Get keys matching pattern |
| `iter_keys(pattern)` | Iterate keys matching pattern |
| `delete_pattern(pattern)` | Delete keys matching pattern |

### Set Method Options

```python
cache.set(key, value, timeout=300, nx=False, xx=False)
```

| Parameter | Description |
|-----------|-------------|
| `timeout` | Expiration in seconds (`None` = never, `0` = immediate) |
| `nx` | Only set if key doesn't exist (SETNX) |
| `xx` | Only set if key exists |

## Helper Functions

### get_redis_connection

```python
from django_redis import get_redis_connection

conn = get_redis_connection(alias="default", write=True)
```

| Parameter | Description |
|-----------|-------------|
| `alias` | Cache alias from settings (default: `"default"`) |
| `write` | Get write connection for primary (default: `True`) |

Returns the underlying `redis.Redis` client instance.

## Lock Interface

```python
lock = cache.lock(key, timeout=None, sleep=0.1, blocking=True, blocking_timeout=None)
```

| Parameter | Description |
|-----------|-------------|
| `key` | Lock name |
| `timeout` | Lock auto-release timeout |
| `sleep` | Time between acquire attempts |
| `blocking` | Wait for lock if held |
| `blocking_timeout` | Max wait time for lock |

Compatible with `threading.Lock`:

```python
# Context manager
with cache.lock("mylock"):
    do_work()

# Manual acquire/release
lock = cache.lock("mylock")
if lock.acquire():
    try:
        do_work()
    finally:
        lock.release()
```

## Settings Reference

### Cache OPTIONS

| Option | Description |
|--------|-------------|
| `CLIENT_CLASS` | Client implementation class |
| `SERIALIZER` | Serializer class |
| `COMPRESSOR` | Compressor class |
| `PASSWORD` | Redis password |
| `SOCKET_CONNECT_TIMEOUT` | Connection timeout |
| `SOCKET_TIMEOUT` | Read/write timeout |
| `IGNORE_EXCEPTIONS` | Ignore connection errors |
| `PICKLE_VERSION` | Pickle protocol version |
| `CONNECTION_POOL_CLASS` | Custom pool class |
| `CONNECTION_POOL_KWARGS` | Pool configuration |
| `REDIS_CLIENT_CLASS` | Custom Redis client |
| `REDIS_CLIENT_KWARGS` | Client configuration |
| `CLOSE_CONNECTION` | Close connections on cache close |
| `SENTINELS` | Sentinel server list |
| `SENTINEL_KWARGS` | Sentinel configuration |

### Global Settings

| Setting | Description |
|---------|-------------|
| `DJANGO_REDIS_CONNECTION_FACTORY` | Connection factory class |
| `DJANGO_REDIS_IGNORE_EXCEPTIONS` | Global exception handling |
| `DJANGO_REDIS_LOG_IGNORED_EXCEPTIONS` | Log ignored exceptions |
| `DJANGO_REDIS_LOGGER` | Logger name for exceptions |
| `DJANGO_REDIS_CLOSE_CONNECTION` | Global close behavior |
| `DJANGO_REDIS_SCAN_ITERSIZE` | Default scan batch size |
