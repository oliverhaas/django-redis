# Advanced Usage

## Pickle Version

By default, django-redis uses `pickle.DEFAULT_PROTOCOL`. To set a specific version:

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "PICKLE_VERSION": -1  # Highest protocol available
        }
    }
}
```

## TTL Operations

### Get TTL

```python
from django.core.cache import cache

cache.set("foo", "value", timeout=25)
cache.ttl("foo")      # Returns 25
cache.ttl("missing")  # Returns 0 (key doesn't exist)
```

Returns:

- `0` - Key doesn't exist or already expired
- `None` - Key exists but has no expiration
- `int` - Seconds until expiration

### Get TTL in Milliseconds

```python
cache.set("foo", "value", timeout=25)
cache.pttl("foo")  # Returns 25000
```

## Expire & Persist

### Set Expiration

```python
cache.set("foo", "bar", timeout=22)
cache.expire("foo", timeout=5)
cache.ttl("foo")  # Returns 5
```

### Set Expiration in Milliseconds

```python
cache.set("foo", "bar", timeout=22)
cache.pexpire("foo", timeout=5500)
cache.pttl("foo")  # Returns 5500
```

### Expire at Specific Time

```python
from datetime import datetime, timedelta

cache.set("foo", "bar", timeout=22)
cache.expire_at("foo", datetime.now() + timedelta(hours=1))
cache.ttl("foo")  # Returns ~3600
```

### Expire at Specific Time (milliseconds precision)

```python
cache.set("foo", "bar", timeout=22)
cache.pexpire_at("foo", datetime.now() + timedelta(milliseconds=900, hours=1))
cache.pttl("foo")  # Returns ~3600900
```

### Remove Expiration

```python
cache.set("foo", "bar", timeout=22)
cache.persist("foo")
cache.ttl("foo")  # Returns None (no expiration)
```

## Locks

Redis distributed locks with the same interface as `threading.Lock`:

```python
from django.core.cache import cache

with cache.lock("somekey"):
    do_some_thing()
```

## Bulk Operations

### Search Keys

```python
from django.core.cache import cache

# Get all matching keys (not recommended for large datasets)
cache.keys("foo_*")  # Returns ["foo_1", "foo_2"]
```

### Iterate Keys (Recommended)

For large datasets, use server-side cursors:

```python
# Returns a generator
for key in cache.iter_keys("foo_*"):
    print(key)
```

### Delete by Pattern

```python
cache.delete_pattern("foo_*")
```

For better performance with many keys:

```python
cache.delete_pattern("foo_*", itersize=100_000)
```

Or set globally:

```python
DJANGO_REDIS_SCAN_ITERSIZE = 100_000
```

## Atomic Operations

### SETNX (Set if Not Exists)

```python
cache.set("key", "value1", nx=True)  # Returns True
cache.set("key", "value2", nx=True)  # Returns False
cache.get("key")  # Returns "value1"
```

### Increment/Decrement

```python
cache.set("counter", 0)
cache.incr("counter")  # Returns 1
cache.incr("counter", delta=5)  # Returns 6
cache.decr("counter")  # Returns 5
```

## Raw Client Access

Access the underlying redis-py client:

```python
from django_redis import get_redis_connection

conn = get_redis_connection("default")
conn.set("raw_key", "raw_value")
conn.hset("hash_key", "field", "value")
```

!!! warning
    Not all pluggable clients support this feature.
