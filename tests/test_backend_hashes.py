"""Tests for hash operations."""

import pytest

from django_redis.cache import RedisCache
from django_redis.client import ShardClient


class TestHashOperations:
    def test_hset(self, cache: RedisCache):
        if isinstance(cache.client, ShardClient):
            pytest.skip("ShardClient doesn't support hash operations")
        cache.hset("foo_hash1", "foo1", "bar1")
        cache.hset("foo_hash1", "foo2", "bar2")
        assert cache.hlen("foo_hash1") == 2
        assert cache.hexists("foo_hash1", "foo1")
        assert cache.hexists("foo_hash1", "foo2")

    def test_hdel(self, cache: RedisCache):
        if isinstance(cache.client, ShardClient):
            pytest.skip("ShardClient doesn't support hash operations")
        cache.hset("foo_hash2", "foo1", "bar1")
        cache.hset("foo_hash2", "foo2", "bar2")
        assert cache.hlen("foo_hash2") == 2
        deleted_count = cache.hdel("foo_hash2", "foo1")
        assert deleted_count == 1
        assert cache.hlen("foo_hash2") == 1
        assert not cache.hexists("foo_hash2", "foo1")
        assert cache.hexists("foo_hash2", "foo2")

    def test_hlen(self, cache: RedisCache):
        if isinstance(cache.client, ShardClient):
            pytest.skip("ShardClient doesn't support hash operations")
        assert cache.hlen("foo_hash3") == 0
        cache.hset("foo_hash3", "foo1", "bar1")
        assert cache.hlen("foo_hash3") == 1
        cache.hset("foo_hash3", "foo2", "bar2")
        assert cache.hlen("foo_hash3") == 2

    def test_hkeys(self, cache: RedisCache):
        if isinstance(cache.client, ShardClient):
            pytest.skip("ShardClient doesn't support hash operations")
        cache.hset("foo_hash4", "foo1", "bar1")
        cache.hset("foo_hash4", "foo2", "bar2")
        cache.hset("foo_hash4", "foo3", "bar3")
        keys = cache.hkeys("foo_hash4")
        assert len(keys) == 3
        for i in range(len(keys)):
            assert keys[i] == f"foo{i + 1}"

    def test_hexists(self, cache: RedisCache):
        if isinstance(cache.client, ShardClient):
            pytest.skip("ShardClient doesn't support hash operations")
        cache.hset("foo_hash5", "foo1", "bar1")
        assert cache.hexists("foo_hash5", "foo1")
        assert not cache.hexists("foo_hash5", "foo")
