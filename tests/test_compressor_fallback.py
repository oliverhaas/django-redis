"""Tests for compressor fallback functionality."""

import gzip
import zlib


class TestDefaultClientCompressorConfig:
    """Tests for DefaultClient compressor configuration handling."""

    def test_single_string_config_backwards_compatible(self, redis_container):
        """Test that single string compressor config still works."""
        from django.test import override_settings

        host, port = redis_container.host, redis_container.port

        caches = {
            "default": {
                "BACKEND": "django_redis.cache.RedisCache",
                "LOCATION": f"redis://{host}:{port}?db=10",
                "OPTIONS": {
                    "compressor": "django_redis.compressors.gzip.GzipCompressor",
                },
            },
        }

        with override_settings(CACHES=caches):
            from django.core.cache import cache

            cache.set("test_key", "test_value" * 100)
            assert cache.get("test_key") == "test_value" * 100
            cache.delete("test_key")

    def test_list_config_with_fallback(self, redis_container):
        """Test that list compressor config with fallback works."""
        from django.test import override_settings

        host, port = redis_container.host, redis_container.port

        caches = {
            "default": {
                "BACKEND": "django_redis.cache.RedisCache",
                "LOCATION": f"redis://{host}:{port}?db=11",
                "OPTIONS": {
                    "compressor": [
                        "django_redis.compressors.gzip.GzipCompressor",
                        None,  # Identity compressor
                    ],
                },
            },
        }

        with override_settings(CACHES=caches):
            from django.core.cache import cache

            # Write with gzip
            cache.set("test_key", "test_value" * 100)
            assert cache.get("test_key") == "test_value" * 100
            cache.delete("test_key")

    def test_migration_scenario(self, redis_container):
        """Test migrating from one compressor to another."""
        from django.test import override_settings

        host, port = redis_container.host, redis_container.port

        # Step 1: Write with zlib
        caches_zlib = {
            "default": {
                "BACKEND": "django_redis.cache.RedisCache",
                "LOCATION": f"redis://{host}:{port}?db=12",
                "OPTIONS": {
                    "compressor": "django_redis.compressors.zlib.ZlibCompressor",
                },
            },
        }

        with override_settings(CACHES=caches_zlib):
            from django.core.cache import cache

            cache.set("old_key", "old_value" * 100)

        # Step 2: Switch to gzip with zlib fallback
        caches_gzip_fallback = {
            "default": {
                "BACKEND": "django_redis.cache.RedisCache",
                "LOCATION": f"redis://{host}:{port}?db=12",
                "OPTIONS": {
                    "compressor": [
                        "django_redis.compressors.gzip.GzipCompressor",
                        "django_redis.compressors.zlib.ZlibCompressor",
                        None,
                    ],
                },
            },
        }

        with override_settings(CACHES=caches_gzip_fallback):
            from django.core.cache import cache

            # Should read old zlib-compressed data via fallback
            assert cache.get("old_key") == "old_value" * 100

            # Write new data with gzip
            cache.set("new_key", "new_value" * 100)
            assert cache.get("new_key") == "new_value" * 100

            cache.delete("old_key")
            cache.delete("new_key")


class TestHasCompressionEnabled:
    """Tests for _has_compression_enabled() with list config."""

    def test_string_identity_returns_false(self):
        """Test that identity compressor string returns False."""
        from unittest.mock import MagicMock

        from django_redis.client.default import DefaultClient

        backend = MagicMock()
        backend.key_prefix = ""
        backend.version = 1
        backend.key_func = lambda k, p, v: k

        client = DefaultClient(
            server=["redis://localhost:6379"],
            params={
                "OPTIONS": {
                    "compressor": "django_redis.compressors.identity.IdentityCompressor",
                },
            },
            backend=backend,
        )

        assert client._has_compression_enabled() is False

    def test_string_gzip_returns_true(self):
        """Test that gzip compressor string returns True."""
        from unittest.mock import MagicMock

        from django_redis.client.default import DefaultClient

        backend = MagicMock()
        backend.key_prefix = ""
        backend.version = 1
        backend.key_func = lambda k, p, v: k

        client = DefaultClient(
            server=["redis://localhost:6379"],
            params={
                "OPTIONS": {
                    "compressor": "django_redis.compressors.gzip.GzipCompressor",
                },
            },
            backend=backend,
        )

        assert client._has_compression_enabled() is True

    def test_list_with_identity_first_returns_false(self):
        """Test that list with identity first returns False."""
        from unittest.mock import MagicMock

        from django_redis.client.default import DefaultClient

        backend = MagicMock()
        backend.key_prefix = ""
        backend.version = 1
        backend.key_func = lambda k, p, v: k

        client = DefaultClient(
            server=["redis://localhost:6379"],
            params={
                "OPTIONS": {
                    "compressor": [
                        "django_redis.compressors.identity.IdentityCompressor",
                        "django_redis.compressors.gzip.GzipCompressor",
                    ],
                },
            },
            backend=backend,
        )

        assert client._has_compression_enabled() is False

    def test_list_with_none_first_returns_false(self):
        """Test that list with None first returns False."""
        from unittest.mock import MagicMock

        from django_redis.client.default import DefaultClient

        backend = MagicMock()
        backend.key_prefix = ""
        backend.version = 1
        backend.key_func = lambda k, p, v: k

        client = DefaultClient(
            server=["redis://localhost:6379"],
            params={
                "OPTIONS": {
                    "compressor": [
                        None,
                        "django_redis.compressors.gzip.GzipCompressor",
                    ],
                },
            },
            backend=backend,
        )

        assert client._has_compression_enabled() is False

    def test_list_with_gzip_first_returns_true(self):
        """Test that list with gzip first returns True."""
        from unittest.mock import MagicMock

        from django_redis.client.default import DefaultClient

        backend = MagicMock()
        backend.key_prefix = ""
        backend.version = 1
        backend.key_func = lambda k, p, v: k

        client = DefaultClient(
            server=["redis://localhost:6379"],
            params={
                "OPTIONS": {
                    "compressor": [
                        "django_redis.compressors.gzip.GzipCompressor",
                        None,
                    ],
                },
            },
            backend=backend,
        )

        assert client._has_compression_enabled() is True


class TestDecompressFallback:
    """Tests for the _decompress fallback logic."""

    def test_decompress_gzip_with_multiple_compressors(self):
        """Test that _decompress correctly decompresses gzip data."""
        from unittest.mock import MagicMock

        from django_redis.client.default import DefaultClient

        backend = MagicMock()
        backend.key_prefix = ""
        backend.version = 1
        backend.key_func = lambda k, p, v: k

        client = DefaultClient(
            server=["redis://localhost:6379"],
            params={
                "OPTIONS": {
                    "compressor": [
                        "django_redis.compressors.gzip.GzipCompressor",
                        "django_redis.compressors.zlib.ZlibCompressor",
                        None,
                    ],
                },
            },
            backend=backend,
        )

        data = b"Test data for compression! " * 50
        gzip_data = gzip.compress(data)

        assert client._decompress(gzip_data) == data

    def test_decompress_zlib_with_fallback(self):
        """Test that _decompress falls back to zlib for zlib-compressed data."""
        from unittest.mock import MagicMock

        from django_redis.client.default import DefaultClient

        backend = MagicMock()
        backend.key_prefix = ""
        backend.version = 1
        backend.key_func = lambda k, p, v: k

        client = DefaultClient(
            server=["redis://localhost:6379"],
            params={
                "OPTIONS": {
                    "compressor": [
                        "django_redis.compressors.gzip.GzipCompressor",
                        "django_redis.compressors.zlib.ZlibCompressor",
                        None,
                    ],
                },
            },
            backend=backend,
        )

        data = b"Test data for compression! " * 50
        zlib_data = zlib.compress(data)

        # gzip will fail, zlib should succeed
        assert client._decompress(zlib_data) == data

    def test_decompress_returns_raw_when_all_fail(self):
        """Test that _decompress returns raw bytes when all compressors fail."""
        from unittest.mock import MagicMock

        from django_redis.client.default import DefaultClient

        backend = MagicMock()
        backend.key_prefix = ""
        backend.version = 1
        backend.key_func = lambda k, p, v: k

        # Only gzip, no identity fallback
        client = DefaultClient(
            server=["redis://localhost:6379"],
            params={
                "OPTIONS": {
                    "compressor": [
                        "django_redis.compressors.gzip.GzipCompressor",
                    ],
                },
            },
            backend=backend,
        )

        # Plain data that isn't gzip
        data = b"Plain uncompressed data"
        assert client._decompress(data) == data

    def test_decompress_with_identity_catches_all(self):
        """Test that identity compressor at end catches uncompressed data."""
        from unittest.mock import MagicMock

        from django_redis.client.default import DefaultClient

        backend = MagicMock()
        backend.key_prefix = ""
        backend.version = 1
        backend.key_func = lambda k, p, v: k

        client = DefaultClient(
            server=["redis://localhost:6379"],
            params={
                "OPTIONS": {
                    "compressor": [
                        "django_redis.compressors.gzip.GzipCompressor",
                        None,  # Identity
                    ],
                },
            },
            backend=backend,
        )

        data = b"Plain uncompressed data"
        # gzip fails, identity returns as-is
        assert client._decompress(data) == data

    def test_decompress_continues_on_failure(self):
        """Test that _decompress continues to next compressor on failure."""
        from unittest.mock import MagicMock

        from django_redis.client.default import DefaultClient

        backend = MagicMock()
        backend.key_prefix = ""
        backend.version = 1
        backend.key_func = lambda k, p, v: k

        client = DefaultClient(
            server=["redis://localhost:6379"],
            params={
                "OPTIONS": {
                    "compressor": [
                        "django_redis.compressors.gzip.GzipCompressor",
                        None,
                    ],
                },
            },
            backend=backend,
        )

        # Data that looks like it could be gzip but isn't valid
        fake_gzip = b"\x1f\x8bNot actually valid gzip data"
        # gzip fails, falls through to identity
        assert client._decompress(fake_gzip) == fake_gzip
