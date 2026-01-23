# Compression

django-redis supports several compression backends to reduce memory usage.

## Zlib Compression

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
        }
    }
}
```

## Gzip Compression

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "COMPRESSOR": "django_redis.compressors.gzip.GzipCompressor",
        }
    }
}
```

## LZMA Compression

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "COMPRESSOR": "django_redis.compressors.lzma.LzmaCompressor",
        }
    }
}
```

## LZ4 Compression

Requires the `lz4` library:

```console
pip install lz4
```

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "COMPRESSOR": "django_redis.compressors.lz4.Lz4Compressor",
        }
    }
}
```

## Zstandard (zstd) Compression

On Python 3.14+, zstd compression uses the built-in `compression.zstd` module.
On older Python versions, it falls back to `backports-zstd`.

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "COMPRESSOR": "django_redis.compressors.zstd.ZStdCompressor",
        }
    }
}
```

## Compressor Fallback (Migration Support)

When migrating from one compressor to another, you can specify a list of compressors.
The first compressor is used for writing new data, while all compressors are tried
when reading (using magic byte detection for efficient format identification).

This allows safe migration between compression formats without data loss:

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            # First compressor used for writing, all tried for reading
            "COMPRESSOR": [
                "django_redis.compressors.zstd.ZStdCompressor",  # New format
                "django_redis.compressors.gzip.GzipCompressor",  # Old format
                None,  # Uncompressed data (IdentityCompressor)
            ],
        }
    }
}
```

### Migration Example

1. **Before migration** - using gzip:
   ```python
   "COMPRESSOR": "django_redis.compressors.gzip.GzipCompressor"
   ```

2. **During migration** - write zstd, read both:
   ```python
   "COMPRESSOR": [
       "django_redis.compressors.zstd.ZStdCompressor",
       "django_redis.compressors.gzip.GzipCompressor",
       None,
   ]
   ```

3. **After migration** - all data refreshed with zstd:
   ```python
   "COMPRESSOR": "django_redis.compressors.zstd.ZStdCompressor"
   ```

### How It Works

Each compressor has a `check()` method that uses magic byte detection:

| Compressor | Magic Bytes |
|------------|-------------|
| Gzip | `\x1f\x8b` |
| Zlib | `\x78\x01`, `\x78\x9c`, `\x78\xda` |
| Zstandard | `\x28\xb5\x2f\xfd` |
| LZ4 | `\x04\x22\x4d\x18` |
| LZMA | `\xfd7zXZ\x00` |
| Identity | Always matches (catch-all) |

When decompressing, each compressor's `check()` is called. If it returns `True`,
decompression is attempted. If decompression fails, the next compressor is tried.

**Note:** Place `None` (IdentityCompressor) last in the list as it matches any data.

## Compression Comparison

| Compressor | Speed | Ratio | Dependencies |
|------------|-------|-------|--------------|
| Zlib | Medium | Good | Built-in |
| Gzip | Medium | Good | Built-in |
| LZMA | Slow | Best | Built-in |
| LZ4 | Fast | Moderate | `lz4` |
| Zstandard | Fast | Good | `pyzstd` |
