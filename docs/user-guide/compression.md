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

Requires the `pyzstd` library:

```console
pip install pyzstd
```

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

## Compression Comparison

| Compressor | Speed | Ratio | Dependencies |
|------------|-------|-------|--------------|
| Zlib | Medium | Good | Built-in |
| Gzip | Medium | Good | Built-in |
| LZMA | Slow | Best | Built-in |
| LZ4 | Fast | Moderate | `lz4` |
| Zstandard | Fast | Good | `pyzstd` |
