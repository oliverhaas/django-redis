"""Tests for key operations: version, delete_pattern, iter_keys, etc."""

from collections.abc import Iterable
from contextlib import suppress
from typing import cast
from unittest.mock import patch

import pytest
from django.core.cache import caches
from django.test import override_settings

from django_redis.cache import RedisCache
from tests.settings_wrapper import SettingsWrapper


@pytest.fixture
def patch_itersize_setting() -> Iterable[None]:
    # destroy cache to force recreation with overriden settings
    with suppress(AttributeError):
        del caches["default"]
    with override_settings(DJANGO_REDIS_SCAN_ITERSIZE=30):
        yield
    # destroy cache to force recreation with original settings
    with suppress(AttributeError):
        del caches["default"]


class TestVersionOperations:
    def test_version(self, cache: RedisCache):
        cache.set("keytest", 2, version=2)
        res = cache.get("keytest")
        assert res is None

        res = cache.get("keytest", version=2)
        assert res == 2

    def test_incr_version(self, cache: RedisCache):
        cache.set("keytest", 2)
        cache.incr_version("keytest")

        res = cache.get("keytest")
        assert res is None

        res = cache.get("keytest", version=2)
        assert res == 2

    def test_ttl_incr_version_no_timeout(self, cache: RedisCache):
        cache.set("my_key", "hello world!", timeout=None)

        cache.incr_version("my_key")

        my_value = cache.get("my_key", version=2)

        assert my_value == "hello world!"


class TestDeletePatternOperations:
    def test_delete_pattern(self, cache: RedisCache):
        for key in ["foo-aa", "foo-ab", "foo-bb", "foo-bc"]:
            cache.set(key, "foo")

        res = cache.delete_pattern("*foo-a*")
        assert bool(res) is True

        keys = cache.keys("foo*")
        assert set(keys) == {"foo-bb", "foo-bc"}

        res = cache.delete_pattern("*foo-a*")
        assert bool(res) is False

    @patch("django_redis.cache.RedisCache.client")
    def test_delete_pattern_with_custom_count(self, client_mock, cache: RedisCache):
        for key in ["foo-aa", "foo-ab", "foo-bb", "foo-bc"]:
            cache.set(key, "foo")

        cache.delete_pattern("*foo-a*", itersize=2)

        client_mock.delete_pattern.assert_called_once_with("*foo-a*", version=None, itersize=2)

    @patch("django_redis.cache.RedisCache.client")
    def test_delete_pattern_with_settings_default_scan_count(
        self,
        client_mock,
        patch_itersize_setting,
        cache: RedisCache,
        settings: SettingsWrapper,
    ):
        for key in ["foo-aa", "foo-ab", "foo-bb", "foo-bc"]:
            cache.set(key, "foo")
        expected_count = settings.DJANGO_REDIS_SCAN_ITERSIZE

        cache.delete_pattern("*foo-a*")

        client_mock.delete_pattern.assert_called_once_with(
            "*foo-a*",
            version=None,
            itersize=expected_count,
        )


class TestIterKeysOperations:
    def test_iter_keys(self, cache: RedisCache):
        cache.set("foo1", 1)
        cache.set("foo2", 1)
        cache.set("foo3", 1)

        # Test simple result
        result = set(cache.iter_keys("foo*"))
        assert result == {"foo1", "foo2", "foo3"}

    def test_iter_keys_itersize(self, cache: RedisCache):
        cache.set("foo1", 1)
        cache.set("foo2", 1)
        cache.set("foo3", 1)

        # Test limited result
        result = list(cache.iter_keys("foo*", itersize=2))
        assert len(result) == 3

    def test_iter_keys_generator(self, cache: RedisCache):
        cache.set("foo1", 1)
        cache.set("foo2", 1)
        cache.set("foo3", 1)

        # Test generator object
        result = cache.iter_keys("foo*")
        next_value = next(result)
        assert next_value is not None


class TestClientSwitching:
    def test_primary_replica_switching(self, cache: RedisCache):
        from django_redis.client.cluster import ClusterClient

        cache = cast("RedisCache", caches["sample"])
        client = cache.client
        # ClusterClient doesn't support primary/replica switching - cluster handles routing
        if isinstance(client, ClusterClient):
            pytest.skip("ClusterClient doesn't support primary/replica switching")
        client._server = ["foo", "bar"]
        client._clients = ["Foo", "Bar"]

        assert client.get_client(write=True) == "Foo"
        assert client.get_client(write=False) == "Bar"

    def test_primary_replica_switching_with_index(self, cache: RedisCache):
        from django_redis.client.cluster import ClusterClient

        cache = cast("RedisCache", caches["sample"])
        client = cache.client
        # ClusterClient doesn't support primary/replica switching - cluster handles routing
        if isinstance(client, ClusterClient):
            pytest.skip("ClusterClient doesn't support primary/replica switching")
        client._server = ["foo", "bar"]
        client._clients = ["Foo", "Bar"]

        assert client.get_client_with_index(write=True) == ("Foo", 0)
        assert client.get_client_with_index(write=False) == ("Bar", 1)
