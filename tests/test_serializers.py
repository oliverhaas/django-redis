import pickle
from datetime import UTC, date, datetime, time, timedelta

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

    def test_datetime_roundtrip(self):
        serializer = JSONSerializer({})
        dt = datetime(2025, 1, 15, 10, 30, 45, tzinfo=UTC)
        encoded = serializer.dumps(dt)
        decoded = serializer.loads(encoded)
        assert decoded == dt
        assert isinstance(decoded, datetime)

    def test_date_roundtrip(self):
        serializer = JSONSerializer({})
        d = date(2025, 1, 15)
        encoded = serializer.dumps(d)
        decoded = serializer.loads(encoded)
        assert decoded == d
        assert isinstance(decoded, date)

    def test_time_roundtrip(self):
        serializer = JSONSerializer({})
        t = time(10, 30, 45)
        encoded = serializer.dumps(t)
        decoded = serializer.loads(encoded)
        assert decoded == t
        assert isinstance(decoded, time)

    def test_timedelta_roundtrip(self):
        serializer = JSONSerializer({})
        td = timedelta(days=1, hours=2, minutes=30)
        encoded = serializer.dumps(td)
        decoded = serializer.loads(encoded)
        assert decoded == td
        assert isinstance(decoded, timedelta)

    def test_datetime_in_dict(self):
        serializer = JSONSerializer({})
        data = {
            "created": datetime(2025, 1, 15, 10, 30, 45, tzinfo=UTC),
            "date": date(2025, 1, 15),
            "time": time(10, 30, 45),
            "duration": timedelta(hours=2),
        }
        encoded = serializer.dumps(data)
        decoded = serializer.loads(encoded)
        assert decoded["created"] == data["created"]
        assert decoded["date"] == data["date"]
        assert decoded["time"] == data["time"]
        assert decoded["duration"] == data["duration"]

    def test_datetime_in_list(self):
        serializer = JSONSerializer({})
        data = [datetime(2025, 1, 15, tzinfo=UTC), date(2025, 1, 16), time(12, 0, 0)]
        encoded = serializer.dumps(data)
        decoded = serializer.loads(encoded)
        assert decoded[0] == data[0]
        assert decoded[1] == data[1]
        assert decoded[2] == data[2]

    def test_datetime_decode_disabled(self):
        serializer = JSONSerializer({"JSON_DECODE_DATETIME": False})
        dt = datetime(2025, 1, 15, 10, 30, 45, tzinfo=UTC)
        encoded = serializer.dumps(dt)
        decoded = serializer.loads(encoded)
        # Should remain as string when decoding is disabled
        assert isinstance(decoded, str)

    def test_regular_string_not_parsed(self):
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
