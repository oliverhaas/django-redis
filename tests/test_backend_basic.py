"""Tests for basic cache operations: set, get, add, delete, get_many, set_many."""

import datetime
from unittest.mock import patch

import pytest
from pytest_mock import MockerFixture

from django_redis.cache import RedisCache
from django_redis.client import ShardClient, herd
from django_redis.serializers.json import JSONSerializer
from django_redis.serializers.msgpack import MSGPackSerializer
from tests.settings_wrapper import SettingsWrapper


class TestBasicCacheOperations:
    def test_setnx(self, cache: RedisCache):
        # we should ensure there is no test_key_nx in redis
        cache.delete("test_key_nx")
        res = cache.get("test_key_nx")
        assert res is None

        res = cache.set("test_key_nx", 1, nx=True)
        assert bool(res) is True
        # test that second set will have
        res = cache.set("test_key_nx", 2, nx=True)
        assert res is False
        res = cache.get("test_key_nx")
        assert res == 1

        cache.delete("test_key_nx")
        res = cache.get("test_key_nx")
        assert res is None

    def test_unicode_keys(self, cache: RedisCache):
        cache.set("ключ", "value")
        res = cache.get("ключ")
        assert res == "value"

    def test_save_and_integer(self, cache: RedisCache):
        cache.set("test_key", 2)
        res = cache.get("test_key", "Foo")

        assert isinstance(res, int)
        assert res == 2

    def test_save_string(self, cache: RedisCache):
        cache.set("test_key", "hello" * 1000)
        res = cache.get("test_key")

        assert isinstance(res, str)
        assert res == "hello" * 1000

        cache.set("test_key", "2")
        res = cache.get("test_key")

        assert isinstance(res, str)
        assert res == "2"

    def test_save_unicode(self, cache: RedisCache):
        cache.set("test_key", "heló")
        res = cache.get("test_key")

        assert isinstance(res, str)
        assert res == "heló"

    def test_save_dict(self, cache: RedisCache):
        if isinstance(cache.client._serializer, JSONSerializer | MSGPackSerializer):
            # JSONSerializer and MSGPackSerializer use the isoformat for
            # datetimes.
            now_dt: str | datetime.datetime = datetime.datetime.now().isoformat()
        else:
            now_dt = datetime.datetime.now()

        test_dict = {"id": 1, "date": now_dt, "name": "Foo"}

        cache.set("test_key", test_dict)
        res = cache.get("test_key")

        assert isinstance(res, dict)
        assert res["id"] == 1
        assert res["name"] == "Foo"
        assert res["date"] == now_dt

    def test_save_float(self, cache: RedisCache):
        float_val = 1.345620002

        cache.set("test_key", float_val)
        res = cache.get("test_key")

        assert isinstance(res, float)
        assert res == float_val

    def test_get_set_bool(self, cache: RedisCache):
        cache.set("bool", True)
        res = cache.get("bool")

        assert isinstance(res, bool)
        assert res is True

        cache.set("bool", False)
        res = cache.get("bool")

        assert isinstance(res, bool)
        assert res is False

    def test_set_add(self, cache: RedisCache):
        cache.set("add_key", "Initial value")
        res = cache.add("add_key", "New value")
        assert res is False

        res = cache.get("add_key")
        assert res == "Initial value"
        res = cache.add("other_key", "New value")
        assert res is True

    def test_get_many(self, cache: RedisCache):
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)

        res = cache.get_many(["a", "b", "c"])
        assert res == {"a": 1, "b": 2, "c": 3}

    def test_get_many_unicode(self, cache: RedisCache):
        cache.set("a", "1")
        cache.set("b", "2")
        cache.set("c", "3")

        res = cache.get_many(["a", "b", "c"])
        assert res == {"a": "1", "b": "2", "c": "3"}

    def test_set_many(self, cache: RedisCache):
        cache.set_many({"a": 1, "b": 2, "c": 3})
        res = cache.get_many(["a", "b", "c"])
        assert res == {"a": 1, "b": 2, "c": 3}

    def test_set_call_empty_pipeline(
        self,
        cache: RedisCache,
        mocker: MockerFixture,
        settings: SettingsWrapper,
    ):
        if isinstance(cache.client, ShardClient):
            pytest.skip("ShardClient doesn't support get_client")

        pipeline = cache.client.get_client(write=True).pipeline()
        key = "key"
        value = "value"

        mocked_set = mocker.patch.object(pipeline, "set")
        cache.set(key, value, client=pipeline)

        if isinstance(cache.client, herd.HerdClient):
            default_timeout = cache.client._backend.default_timeout
            herd_timeout = (default_timeout + settings.CACHE_HERD_TIMEOUT) * 1000
            herd_pack_value = cache.client._pack(value, default_timeout)
            mocked_set.assert_called_once_with(
                cache.client.make_key(key, version=None),
                cache.client.encode(herd_pack_value),
                nx=False,
                px=herd_timeout,
                xx=False,
            )
        else:
            mocked_set.assert_called_once_with(
                cache.client.make_key(key, version=None),
                cache.client.encode(value),
                nx=False,
                px=cache.client._backend.default_timeout * 1000,
                xx=False,
            )

    def test_delete(self, cache: RedisCache):
        cache.set_many({"a": 1, "b": 2, "c": 3})
        res = cache.delete("a")
        assert bool(res) is True

        res = cache.get_many(["a", "b", "c"])
        assert res == {"b": 2, "c": 3}

        res = cache.delete("a")
        assert bool(res) is False

    @patch("django_redis.cache.DJANGO_VERSION", (3, 1, 0, "final", 0))
    def test_delete_return_value_type_new31(self, cache: RedisCache):
        """delete() returns a boolean instead of int since django version 3.1"""
        cache.set("a", 1)
        res = cache.delete("a")
        assert isinstance(res, bool)
        assert res is True
        res = cache.delete("b")
        assert isinstance(res, bool)
        assert res is False

    @patch("django_redis.cache.DJANGO_VERSION", new=(3, 0, 1, "final", 0))
    def test_delete_return_value_type_before31(self, cache: RedisCache):
        """delete() returns a int before django version 3.1"""
        cache.set("a", 1)
        res = cache.delete("a")
        assert isinstance(res, int)
        assert res == 1
        res = cache.delete("b")
        assert isinstance(res, int)
        assert res == 0

    def test_delete_many(self, cache: RedisCache):
        cache.set_many({"a": 1, "b": 2, "c": 3})
        res = cache.delete_many(["a", "b"])
        assert bool(res) is True

        res = cache.get_many(["a", "b", "c"])
        assert res == {"c": 3}

        res = cache.delete_many(["a", "b"])
        assert bool(res) is False

    def test_delete_many_generator(self, cache: RedisCache):
        cache.set_many({"a": 1, "b": 2, "c": 3})
        res = cache.delete_many(key for key in ["a", "b"])
        assert bool(res) is True

        res = cache.get_many(["a", "b", "c"])
        assert res == {"c": 3}

        res = cache.delete_many(["a", "b"])
        assert bool(res) is False

    def test_delete_many_empty_generator(self, cache: RedisCache):
        from typing import cast

        res = cache.delete_many(key for key in cast("list[str]", []))
        assert bool(res) is False

    def test_clear(self, cache: RedisCache):
        cache.set("foo", "bar")
        value_from_cache = cache.get("foo")
        assert value_from_cache == "bar"
        cache.clear()
        value_from_cache_after_clear = cache.get("foo")
        assert value_from_cache_after_clear is None

    def test_close(self, cache: RedisCache, settings: SettingsWrapper):
        settings.DJANGO_REDIS_CLOSE_CONNECTION = True
        cache.set("f", "1")
        cache.close()

    def test_close_client(self, cache: RedisCache, mocker: MockerFixture):
        mock = mocker.patch.object(cache.client, "close")
        cache.close()
        assert mock.called
