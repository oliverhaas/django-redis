"""Cache fixture and configuration builders."""

from collections.abc import Iterable
from typing import TYPE_CHECKING

import pytest
from django.test import override_settings

from django_redis.cache import BaseCache

if TYPE_CHECKING:
    from tests.fixtures.containers import RedisContainerInfo, SentinelContainerInfo

# Available compressors (None means no compression)
COMPRESSORS = {
    None: None,
    "gzip": "django_redis.compressors.gzip.GzipCompressor",
    "lz4": "django_redis.compressors.lz4.Lz4Compressor",
    "zlib": "django_redis.compressors.zlib.ZlibCompressor",
    "zstd": "django_redis.compressors.zstd.ZStdCompressor",
}

# Available serializers (None means default pickle)
SERIALIZERS = {
    None: None,
    "json": "django_redis.serializers.json.JSONSerializer",
    "msgpack": "django_redis.serializers.msgpack.MSGPackSerializer",
}

# Available client classes
CLIENT_CLASSES = {
    "default": "django_redis.client.DefaultClient",
    "sentinel": "django_redis.client.SentinelClient",
    "cluster": "django_redis.client.ClusterClient",
}

# Connection factories for specific client types
CONNECTION_FACTORIES = {
    "cluster": "django_redis.pool.ClusterConnectionFactory",
}

# Client library configurations: maps client_library -> (client_class, connection_pool_class, parser_class)
# parser_class is the Python parser, native_parser_class is hiredis/libvalkey parser
CLIENT_LIBRARY_CONFIGS = {
    "redis": {
        "client_class": "redis.client.Redis",
        "connection_pool_class": "redis.connection.ConnectionPool",
        "parser_class": "redis._parsers.resp2._RESP2Parser",  # Python parser
        "native_parser_class": "redis._parsers.hiredis._HiredisParser",
    },
    "valkey": {
        "client_class": "valkey.Valkey",
        "connection_pool_class": "valkey.connection.ConnectionPool",
        "parser_class": "valkey._parsers.resp2._RESP2Parser",  # Python parser
        "native_parser_class": "valkey._parsers.libvalkey._LibvalkeyParser",
    },
}


# Parametrized fixtures - tests opt-in by requesting these
@pytest.fixture(params=[None, "gzip", "lz4", "zlib", "zstd"])
def compressors(request) -> str | None:
    """Parametrized compressor fixture. Request this to test all compressors."""
    return request.param


@pytest.fixture(params=[None, "json", "msgpack"])
def serializers(request) -> str | None:
    """Parametrized serializer fixture. Request this to test all serializers."""
    return request.param


@pytest.fixture(params=["default", "cluster"])
def client_class(request) -> str:
    """Parametrized client class fixture."""
    return request.param


@pytest.fixture(params=[False, "sentinel", "sentinel_opts"])
def sentinel_mode(request) -> str | bool:
    """Parametrized sentinel mode fixture."""
    return request.param


@pytest.fixture(params=[False, True], ids=["python-parser", "native-parser"])
def native_parser(request) -> bool:
    """Parametrized native parser fixture.

    When True, uses hiredis for redis-py or libvalkey for valkey-py.
    When False, uses the default Python parser.
    """
    return request.param


def _get_client_library_options(
    client_library: str = "redis",
    native_parser: bool = False,
) -> dict:
    """Get OPTIONS dict entries for the given client library.

    Args:
        client_library: "redis" or "valkey"
        native_parser: If True, use hiredis/libvalkey parser; else use Python parser

    Returns:
        Dict with REDIS_CLIENT_CLASS, CONNECTION_POOL_CLASS, and PARSER_CLASS

    """
    config = CLIENT_LIBRARY_CONFIGS.get(client_library, CLIENT_LIBRARY_CONFIGS["redis"])
    options = {
        "REDIS_CLIENT_CLASS": config["client_class"],
        "CONNECTION_POOL_CLASS": config["connection_pool_class"],
    }
    # Always set PARSER_CLASS explicitly to control which parser is used
    if native_parser:
        options["PARSER_CLASS"] = config["native_parser_class"]
    else:
        options["PARSER_CLASS"] = config["parser_class"]
    return options


def build_cache_config(
    redis_host: str,
    redis_port: int,
    *,
    client_class: str = "default",
    compressor: str | None = None,
    serializer: str | None = None,
    client_library: str = "redis",
    native_parser: bool = False,
    db: int = 1,
) -> dict:
    """Build a CACHES configuration dict.

    Args:
        redis_host: Redis server host
        redis_port: Redis server port
        client_class: django-redis client class ("default", "sentinel", "cluster")
        compressor: Compressor name (None, "gzip", "lz4", "zlib", "zstd")
        serializer: Serializer name (None, "json", "msgpack")
        client_library: Python client library ("redis" or "valkey")
        native_parser: If True, use native parser (hiredis/libvalkey)
        db: Redis database number

    """
    options = {"CLIENT_CLASS": CLIENT_CLASSES[client_class]}
    options.update(_get_client_library_options(client_library, native_parser))

    if compressor and compressor in COMPRESSORS:
        options["COMPRESSOR"] = COMPRESSORS[compressor]
    if serializer and serializer in SERIALIZERS:
        options["SERIALIZER"] = SERIALIZERS[serializer]

    location = f"redis://{redis_host}:{redis_port}?db={db}"

    return {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": [location, location],
            "OPTIONS": options,
        },
        "doesnotexist": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": f"redis://{redis_host}:56379?db={db}",
            "OPTIONS": options.copy(),
        },
        "sample": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": f"{location},{location}",
            "OPTIONS": options.copy(),
        },
        "with_prefix": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": location,
            "OPTIONS": options.copy(),
            "KEY_PREFIX": "test-prefix",
        },
    }


def build_sentinel_cache_config(
    sentinel_host: str,
    sentinel_port: int,
    *,
    use_connection_factory_opts: bool = False,
    client_library: str = "redis",
    native_parser: bool = False,
    db: int = 7,
) -> dict:
    """Build a CACHES configuration for Sentinel."""
    sentinels = [(sentinel_host, sentinel_port)]
    conn_factory = "django_redis.pool.SentinelConnectionFactory"

    base_options = {
        "CLIENT_CLASS": "django_redis.client.DefaultClient",
        "SENTINELS": sentinels,
    }
    base_options.update(_get_client_library_options(client_library, native_parser))

    if use_connection_factory_opts:
        base_options["CONNECTION_FACTORY"] = conn_factory

    return {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": [f"redis://mymaster?db={db}"],
            "OPTIONS": base_options.copy(),
        },
        "doesnotexist": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": f"redis://missing_service?db={db}",
            "OPTIONS": base_options.copy(),
        },
        "sample": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": f"redis://mymaster?db={db}",
            "OPTIONS": {
                **base_options,
                "CLIENT_CLASS": "django_redis.client.SentinelClient",
            },
        },
        "with_prefix": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": f"redis://mymaster?db={db}",
            "OPTIONS": base_options.copy(),
            "KEY_PREFIX": "test-prefix",
        },
    }


def build_cluster_cache_config(
    cluster_host: str,
    cluster_port: int,
    *,
    compressor: str | None = None,
    serializer: str | None = None,
    client_library: str = "redis",
    native_parser: bool = False,
) -> dict:
    """Build a CACHES configuration for Redis Cluster.

    Note: Cluster mode currently only supports redis-py. When using valkey client_library,
    this function still uses redis-py's RedisCluster for cluster connections.
    """
    options = {
        "CLIENT_CLASS": CLIENT_CLASSES["cluster"],
        "CONNECTION_FACTORY": CONNECTION_FACTORIES["cluster"],
    }
    # For cluster, we only use client library options for non-cluster connections
    # The ClusterConnectionFactory creates RedisCluster directly
    # Note: Cluster mode currently only supports redis-py's RedisCluster
    if client_library == "redis":
        lib_options = _get_client_library_options(client_library, native_parser)
        # Remove pool class - cluster manages its own connections
        lib_options.pop("CONNECTION_POOL_CLASS", None)
        options.update(lib_options)

    if compressor and compressor in COMPRESSORS:
        options["COMPRESSOR"] = COMPRESSORS[compressor]
    if serializer and serializer in SERIALIZERS:
        options["SERIALIZER"] = SERIALIZERS[serializer]

    # Cluster doesn't use db numbers - data is sharded across slots
    location = f"redis://{cluster_host}:{cluster_port}"

    return {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": location,
            "OPTIONS": options.copy(),
        },
        "doesnotexist": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": f"redis://{cluster_host}:56379",  # Non-existent port
            "OPTIONS": options.copy(),
        },
        "sample": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": location,
            "OPTIONS": options.copy(),
        },
        "with_prefix": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": location,
            "OPTIONS": options.copy(),
            "KEY_PREFIX": "test-prefix",
        },
    }


def get_db_number(
    client_class: str,
    compressor: str | None,
    serializer: str | None,
) -> int:
    """Calculate the db number based on configuration to avoid conflicts."""
    return abs(hash((client_class, compressor, serializer))) % 14 + 1


def _make_cache(
    redis_container: "RedisContainerInfo",
    request: pytest.FixtureRequest,
    client_class_val: str,
    sentinel_mode_val: str | bool,
    compressor_val: str | None,
    serializer_val: str | None,
    native_parser_val: bool = False,
) -> Iterable[BaseCache]:
    """Core cache creation logic shared by all cache fixtures."""
    redis_host = redis_container.host
    redis_port = redis_container.port
    client_library = redis_container.client_library

    # Handle sentinel mode - it overrides other settings
    if sentinel_mode_val:
        sentinel_info: SentinelContainerInfo = request.getfixturevalue("sentinel_container")
        use_opts = sentinel_mode_val == "sentinel_opts"
        db = 8 if use_opts else 7
        caches = build_sentinel_cache_config(
            sentinel_info.host,
            sentinel_info.port,
            use_connection_factory_opts=use_opts,
            client_library=sentinel_info.client_library,
            native_parser=native_parser_val,
            db=db,
        )
        if not use_opts:
            with override_settings(
                CACHES=caches,
                DJANGO_REDIS_CONNECTION_FACTORY="django_redis.pool.SentinelConnectionFactory",
            ):
                from django.core.cache import cache as default_cache

                default_cache.clear()  # Clear before test
                yield default_cache
                default_cache.clear()  # Clear after test
            return

        with override_settings(CACHES=caches):
            from django.core.cache import cache as default_cache

            default_cache.clear()  # Clear before test
            yield default_cache
            default_cache.clear()  # Clear after test
        return

    # Handle cluster client - needs cluster_container instead of redis_container
    if client_class_val == "cluster":
        cluster_host, cluster_port = request.getfixturevalue("cluster_container")
        caches = build_cluster_cache_config(
            cluster_host,
            cluster_port,
            compressor=compressor_val,
            serializer=serializer_val,
            client_library=client_library,
            native_parser=native_parser_val,
        )
        with override_settings(CACHES=caches):
            from django.core.cache import cache as default_cache

            default_cache.clear()  # Clear before test
            yield default_cache
            default_cache.clear()  # Clear after test
        return

    # Build cache config for default client
    db = get_db_number(client_class_val, compressor_val, serializer_val)
    caches = build_cache_config(
        redis_host,
        redis_port,
        client_class=client_class_val,
        compressor=compressor_val,
        serializer=serializer_val,
        client_library=client_library,
        native_parser=native_parser_val,
        db=db,
    )

    with override_settings(CACHES=caches):
        from django.core.cache import cache as default_cache

        default_cache.clear()  # Clear before test
        yield default_cache
        default_cache.clear()  # Clear after test


@pytest.fixture
def cache(
    client_class: str,
    sentinel_mode: str | bool,
    redis_container: "RedisContainerInfo",
    request: pytest.FixtureRequest,
) -> Iterable[BaseCache]:
    """Django cache fixture parametrized by client_class × sentinel_mode.

    If the test also requests `compressor`, `serializer`, or `native_parser` fixtures,
    those will be used (creating additional Cartesian product).
    Otherwise, defaults (no compression, pickle serializer, Python parser) are used.

    The client library (redis-py vs valkey-py) is automatically determined from
    the redis_container fixture, which is coupled to the server image being tested.
    """

    # Check if test opted into compressor/serializer/native_parser parametrization
    compressor_val = None
    serializer_val = None
    native_parser_val = False

    if "compressors" in request.fixturenames:
        compressor_val = request.getfixturevalue("compressors")
    if "serializers" in request.fixturenames:
        serializer_val = request.getfixturevalue("serializers")
    if "native_parser" in request.fixturenames:
        native_parser_val = request.getfixturevalue("native_parser")

    yield from _make_cache(
        redis_container,
        request,
        client_class,
        sentinel_mode,
        compressor_val,
        serializer_val,
        native_parser_val,
    )
