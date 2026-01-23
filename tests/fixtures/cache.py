"""Cache fixture and configuration builders."""

from collections.abc import Iterable

import pytest
from django.test import override_settings

from django_redis.cache import BaseCache

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


def build_cache_config(
    redis_host: str,
    redis_port: int,
    *,
    client_class: str = "default",
    compressor: str | None = None,
    serializer: str | None = None,
    db: int = 1,
) -> dict:
    """Build a CACHES configuration dict."""
    options = {"CLIENT_CLASS": CLIENT_CLASSES[client_class]}

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
    db: int = 7,
) -> dict:
    """Build a CACHES configuration for Sentinel."""
    sentinels = [(sentinel_host, sentinel_port)]
    conn_factory = "django_redis.pool.SentinelConnectionFactory"

    base_options = {
        "CLIENT_CLASS": "django_redis.client.DefaultClient",
        "SENTINELS": sentinels,
    }
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
) -> dict:
    """Build a CACHES configuration for Redis Cluster."""
    options = {
        "CLIENT_CLASS": CLIENT_CLASSES["cluster"],
        "CONNECTION_FACTORY": CONNECTION_FACTORIES["cluster"],
    }

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
    redis_container: tuple[str, int],
    request: pytest.FixtureRequest,
    client_class_val: str,
    sentinel_mode_val: str | bool,
    compressor_val: str | None,
    serializer_val: str | None,
) -> Iterable[BaseCache]:
    """Core cache creation logic shared by all cache fixtures."""
    redis_host, redis_port = redis_container

    # Handle sentinel mode - it overrides other settings
    if sentinel_mode_val:
        sentinel_host, sentinel_port = request.getfixturevalue("sentinel_container")
        use_opts = sentinel_mode_val == "sentinel_opts"
        db = 8 if use_opts else 7
        caches = build_sentinel_cache_config(
            sentinel_host,
            sentinel_port,
            use_connection_factory_opts=use_opts,
            db=db,
        )
        if not use_opts:
            with override_settings(
                CACHES=caches,
                DJANGO_REDIS_CONNECTION_FACTORY="django_redis.pool.SentinelConnectionFactory",
            ):
                from django.core.cache import cache as default_cache

                yield default_cache
                default_cache.clear()
            return

        with override_settings(CACHES=caches):
            from django.core.cache import cache as default_cache

            yield default_cache
            default_cache.clear()
        return

    # Handle cluster client - needs cluster_container instead of redis_container
    if client_class_val == "cluster":
        cluster_host, cluster_port = request.getfixturevalue("cluster_container")
        caches = build_cluster_cache_config(
            cluster_host,
            cluster_port,
            compressor=compressor_val,
            serializer=serializer_val,
        )
        with override_settings(CACHES=caches):
            from django.core.cache import cache as default_cache

            yield default_cache
            default_cache.clear()
        return

    # Build cache config for default client
    db = get_db_number(client_class_val, compressor_val, serializer_val)
    caches = build_cache_config(
        redis_host,
        redis_port,
        client_class=client_class_val,
        compressor=compressor_val,
        serializer=serializer_val,
        db=db,
    )

    with override_settings(CACHES=caches):
        from django.core.cache import cache as default_cache

        yield default_cache
        default_cache.clear()


@pytest.fixture
def cache(
    client_class: str,
    sentinel_mode: str | bool,
    redis_container: tuple[str, int],
    request: pytest.FixtureRequest,
) -> Iterable[BaseCache]:
    """
    Django cache fixture parametrized by client_class × sentinel_mode.

    If the test also requests `compressor` or `serializer` fixtures,
    those will be used (creating additional Cartesian product).
    Otherwise, defaults (no compression, pickle serializer) are used.
    """
    # Check if test opted into compressor/serializer parametrization
    compressor_val = None
    serializer_val = None

    if "compressors" in request.fixturenames:
        compressor_val = request.getfixturevalue("compressors")
    if "serializers" in request.fixturenames:
        serializer_val = request.getfixturevalue("serializers")

    yield from _make_cache(
        redis_container,
        request,
        client_class,
        sentinel_mode,
        compressor_val,
        serializer_val,
    )
