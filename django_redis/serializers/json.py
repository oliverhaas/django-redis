import json
import re
from datetime import date, datetime, time, timedelta
from typing import Any

from django.core.serializers.json import DjangoJSONEncoder
from django.utils.dateparse import parse_date, parse_datetime, parse_duration, parse_time

from django_redis.exceptions import SerializerError
from django_redis.serializers.base import BaseSerializer

# Patterns to quickly identify potential ISO 8601 strings
# These are loose checks - actual parsing validates the format
_DATETIME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}")
_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME_PATTERN = re.compile(r"^\d{2}:\d{2}:\d{2}")
_DURATION_PATTERN = re.compile(r"^P(?:\d+[YMWD])*(?:T(?:\d+[HMS])*)?$")


def _try_parse_datetime_string(value: str) -> str | datetime | date | time | timedelta:
    """Attempt to parse a string as a datetime, date, time, or duration.

    Returns the parsed object if successful, otherwise the original string.
    """
    # Try datetime first (most common case)
    if _DATETIME_PATTERN.match(value):
        result = parse_datetime(value)
        if result is not None:
            return result

    # Try date (YYYY-MM-DD)
    if _DATE_PATTERN.match(value):
        result = parse_date(value)
        if result is not None:
            return result

    # Try time (HH:MM:SS or HH:MM:SS.ffffff)
    if _TIME_PATTERN.match(value):
        result = parse_time(value)
        if result is not None:
            return result

    # Try duration (ISO 8601 duration like P1DT2H30M)
    if _DURATION_PATTERN.match(value):
        result = parse_duration(value)
        if result is not None:
            return result

    return value


def _decode_datetime_recursive(obj: Any) -> Any:
    """Recursively walk through a structure and decode datetime strings."""
    if isinstance(obj, str):
        return _try_parse_datetime_string(obj)
    if isinstance(obj, dict):
        return {key: _decode_datetime_recursive(val) for key, val in obj.items()}
    if isinstance(obj, list):
        return [_decode_datetime_recursive(item) for item in obj]
    return obj


class JSONSerializer(BaseSerializer):
    """JSON serializer with datetime support.

    Uses DjangoJSONEncoder for encoding, which handles:
    - datetime.datetime -> ISO 8601 string
    - datetime.date -> ISO 8601 string
    - datetime.time -> ISO 8601 string (naive only)
    - datetime.timedelta -> ISO 8601 duration string
    - decimal.Decimal -> string
    - uuid.UUID -> string

    On decoding, attempts to parse ISO 8601 strings back to their
    original types. This can be disabled by setting decode_datetime=False.
    """

    encoder_class = DjangoJSONEncoder

    def __init__(self, options: dict[str, Any] | None = None) -> None:
        super().__init__(options)
        # Allow disabling datetime decoding for performance
        self._decode_datetime = True
        if options:
            self._decode_datetime = options.get("JSON_DECODE_DATETIME", True)

    def dumps(self, value: Any) -> bytes:
        return json.dumps(value, cls=self.encoder_class).encode()

    def loads(self, value: bytes) -> Any:
        try:
            result = json.loads(value.decode())
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise SerializerError from e
        else:
            if self._decode_datetime:
                result = _decode_datetime_recursive(result)
            return result
