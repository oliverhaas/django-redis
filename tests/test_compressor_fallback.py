"""Tests for compressor fallback functionality."""

import gzip
import zlib

from django_redis.compressors.gzip import GzipCompressor
from django_redis.compressors.identity import IdentityCompressor
from django_redis.compressors.zlib import ZlibCompressor


class TestCompressorCheck:
    """Tests for the check() method on compressors."""

    def test_gzip_check_detects_gzip_data(self):
        """Test that GzipCompressor.check() detects gzip-compressed data."""
        compressor = GzipCompressor({})
        data = b"Test data for compression! " * 50
        compressed = gzip.compress(data)
        assert compressor.check(compressed) is True

    def test_gzip_check_rejects_non_gzip_data(self):
        """Test that GzipCompressor.check() rejects non-gzip data."""
        compressor = GzipCompressor({})
        assert compressor.check(b"Plain text data") is False
        assert compressor.check(b"") is False

    def test_zlib_check_detects_zlib_data(self):
        """Test that ZlibCompressor.check() detects zlib-compressed data."""
        compressor = ZlibCompressor({})
        data = b"Test data for compression! " * 50
        compressed = zlib.compress(data)
        assert compressor.check(compressed) is True

    def test_zlib_check_rejects_non_zlib_data(self):
        """Test that ZlibCompressor.check() rejects non-zlib data."""
        compressor = ZlibCompressor({})
        assert compressor.check(b"Plain text data") is False

    def test_identity_check_always_returns_true(self):
        """Test that IdentityCompressor.check() always returns True."""
        compressor = IdentityCompressor({})
        assert compressor.check(b"Anything") is True
        assert compressor.check(b"") is True
        assert compressor.check(gzip.compress(b"data")) is True

    def test_gzip_check_with_zlib_data_returns_false(self):
        """Test that GzipCompressor.check() returns False for zlib data."""
        gzip_compressor = GzipCompressor({})
        data = b"Test data" * 50
        zlib_compressed = zlib.compress(data)
        assert gzip_compressor.check(zlib_compressed) is False

    def test_zlib_check_with_gzip_data_returns_false(self):
        """Test that ZlibCompressor.check() returns False for gzip data."""
        zlib_compressor = ZlibCompressor({})
        data = b"Test data" * 50
        gzip_compressed = gzip.compress(data)
        assert zlib_compressor.check(gzip_compressed) is False


class TestDefaultClientCompressorConfig:
    """Tests for DefaultClient compressor configuration handling."""

    def test_single_string_config_backwards_compatible(self, redis_container):
        """Test that single string COMPRESSOR config still works."""
        from django.test import override_settings

        host, port = redis_container

        caches = {
            "default": {
                "BACKEND": "django_redis.cache.RedisCache",
                "LOCATION": f"redis://{host}:{port}?db=10",
                "OPTIONS": {
                    "COMPRESSOR": "django_redis.compressors.gzip.GzipCompressor",
                },
            },
        }

        with override_settings(CACHES=caches):
            from django.core.cache import cache

            cache.set("test_key", "test_value" * 100)
            assert cache.get("test_key") == "test_value" * 100
            cache.delete("test_key")

    def test_list_config_with_fallback(self, redis_container):
        """Test that list COMPRESSOR config with fallback works."""
        from django.test import override_settings

        host, port = redis_container

        caches = {
            "default": {
                "BACKEND": "django_redis.cache.RedisCache",
                "LOCATION": f"redis://{host}:{port}?db=11",
                "OPTIONS": {
                    "COMPRESSOR": [
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

        host, port = redis_container

        # Step 1: Write with zlib
        caches_zlib = {
            "default": {
                "BACKEND": "django_redis.cache.RedisCache",
                "LOCATION": f"redis://{host}:{port}?db=12",
                "OPTIONS": {
                    "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
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
                    "COMPRESSOR": [
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
                    "COMPRESSOR": "django_redis.compressors.identity.IdentityCompressor",
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
                    "COMPRESSOR": "django_redis.compressors.gzip.GzipCompressor",
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
                    "COMPRESSOR": [
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
                    "COMPRESSOR": [
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
                    "COMPRESSOR": [
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

    def test_decompress_detects_gzip_with_multiple_compressors(self):
        """Test that _decompress correctly detects and decompresses gzip data."""
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
                    "COMPRESSOR": [
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

    def test_decompress_detects_zlib_with_multiple_compressors(self):
        """Test that _decompress correctly detects and decompresses zlib data."""
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
                    "COMPRESSOR": [
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

        assert client._decompress(zlib_data) == data

    def test_decompress_returns_raw_when_no_match(self):
        """Test that _decompress returns raw bytes when no compressor matches."""
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
                    "COMPRESSOR": [
                        "django_redis.compressors.gzip.GzipCompressor",
                    ],
                },
            },
            backend=backend,
        )

        # Plain data that doesn't look like gzip
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
                    "COMPRESSOR": [
                        "django_redis.compressors.gzip.GzipCompressor",
                        None,  # Identity
                    ],
                },
            },
            backend=backend,
        )

        data = b"Plain uncompressed data"
        # Identity compressor's check() returns True and decompress returns as-is
        assert client._decompress(data) == data

    def test_decompress_continues_on_decompression_failure(self):
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
                    "COMPRESSOR": [
                        "django_redis.compressors.gzip.GzipCompressor",
                        None,
                    ],
                },
            },
            backend=backend,
        )

        # Data that starts with gzip magic bytes but isn't valid gzip
        # This will make check() return True but decompress() will fail
        fake_gzip = b"\x1f\x8bNot actually valid gzip data"
        # Should fall through to identity and return as-is
        assert client._decompress(fake_gzip) == fake_gzip
