"""Tests for increment and decrement operations."""

import pytest

from django_redis.cache import RedisCache
from django_redis.client import ShardClient, herd


class TestIncrDecrOperations:
    def test_incr(self, cache: RedisCache):
        if isinstance(cache.client, herd.HerdClient):
            pytest.skip("HerdClient doesn't support incr")

        cache.set("num", 1)

        cache.incr("num")
        res = cache.get("num")
        assert res == 2

        cache.incr("num", 10)
        res = cache.get("num")
        assert res == 12

        # max 64 bit signed int
        cache.set("num", 9223372036854775807)

        cache.incr("num")
        res = cache.get("num")
        assert res == 9223372036854775808

        cache.incr("num", 2)
        res = cache.get("num")
        assert res == 9223372036854775810

        cache.set("num", 3)

        cache.incr("num", 2)
        res = cache.get("num")
        assert res == 5

    def test_incr_no_timeout(self, cache: RedisCache):
        if isinstance(cache.client, herd.HerdClient):
            pytest.skip("HerdClient doesn't support incr")

        cache.set("num", 1, timeout=None)

        cache.incr("num")
        res = cache.get("num")
        assert res == 2

        cache.incr("num", 10)
        res = cache.get("num")
        assert res == 12

        # max 64 bit signed int
        cache.set("num", 9223372036854775807, timeout=None)

        cache.incr("num")
        res = cache.get("num")
        assert res == 9223372036854775808

        cache.incr("num", 2)
        res = cache.get("num")
        assert res == 9223372036854775810

        cache.set("num", 3, timeout=None)

        cache.incr("num", 2)
        res = cache.get("num")
        assert res == 5

    def test_incr_error(self, cache: RedisCache):
        if isinstance(cache.client, herd.HerdClient):
            pytest.skip("HerdClient doesn't support incr")

        with pytest.raises(ValueError):
            # key does not exist
            cache.incr("numnum")

    def test_incr_ignore_check(self, cache: RedisCache):
        if isinstance(cache.client, ShardClient):
            pytest.skip("ShardClient doesn't support argument ignore_key_check to incr")
        if isinstance(cache.client, herd.HerdClient):
            pytest.skip("HerdClient doesn't support incr")

        # key exists check will be skipped and the value will be incremented by
        # '1' which is the default delta
        cache.incr("num", ignore_key_check=True)
        res = cache.get("num")
        assert res == 1
        cache.delete("num")

        # since key doesnt exist it is set to the delta value, 10 in this case
        cache.incr("num", 10, ignore_key_check=True)
        res = cache.get("num")
        assert res == 10
        cache.delete("num")

        # following are just regression checks to make sure it still works as
        # expected with incr max 64 bit signed int
        cache.set("num", 9223372036854775807)

        cache.incr("num", ignore_key_check=True)
        res = cache.get("num")
        assert res == 9223372036854775808

        cache.incr("num", 2, ignore_key_check=True)
        res = cache.get("num")
        assert res == 9223372036854775810

        cache.set("num", 3)

        cache.incr("num", 2, ignore_key_check=True)
        res = cache.get("num")
        assert res == 5

    def test_decr(self, cache: RedisCache):
        if isinstance(cache.client, herd.HerdClient):
            pytest.skip("HerdClient doesn't support decr")

        cache.set("num", 20)

        cache.decr("num")
        res = cache.get("num")
        assert res == 19

        cache.decr("num", 20)
        res = cache.get("num")
        assert res == -1

        cache.decr("num", 2)
        res = cache.get("num")
        assert res == -3

        cache.set("num", 20)

        cache.decr("num")
        res = cache.get("num")
        assert res == 19

        # max 64 bit signed int + 1
        cache.set("num", 9223372036854775808)

        cache.decr("num")
        res = cache.get("num")
        assert res == 9223372036854775807

        cache.decr("num", 2)
        res = cache.get("num")
        assert res == 9223372036854775805
