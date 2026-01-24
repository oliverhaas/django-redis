import pickle

import pytest
from django.core.exceptions import ImproperlyConfigured

from django_redis.serializers.json import JSONSerializer
from django_redis.serializers.pickle import PickleSerializer


class TestJSONSerializer:
    def test_basic_roundtrip(self):
        serializer = JSONSerializer({})
        data = {"key": "value", "number": 42, "nested": {"list": [1, 2, 3]}}
        encoded = serializer.dumps(data)
        decoded = serializer.loads(encoded)
        assert decoded == data

    def test_regular_string_not_modified(self):
        serializer = JSONSerializer({})
        data = {"message": "Hello world", "code": "ABC-123"}
        encoded = serializer.dumps(data)
        decoded = serializer.loads(encoded)
        assert decoded == data
        assert isinstance(decoded["message"], str)


class TestPickleSerializer:
    def test_invalid_pickle_version_provided(self):
        with pytest.raises(
            ImproperlyConfigured,
            match="PICKLE_VERSION value must be an integer",
        ):
            PickleSerializer({"PICKLE_VERSION": "not-an-integer"})

    def test_setup_pickle_version_not_explicitly_specified(self):
        serializer = PickleSerializer({})
        assert serializer._pickle_version == pickle.DEFAULT_PROTOCOL

    def test_setup_pickle_version_too_high(self):
        with pytest.raises(
            ImproperlyConfigured,
            match=f"PICKLE_VERSION can't be higher than pickle.HIGHEST_PROTOCOL: {pickle.HIGHEST_PROTOCOL}",
        ):
            PickleSerializer({"PICKLE_VERSION": pickle.HIGHEST_PROTOCOL + 1})
