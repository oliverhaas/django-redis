import sys
from collections.abc import Iterable
from os import environ
from pathlib import Path

import pytest
from testcontainers.redis import RedisContainer
from xdist.scheduler import LoadScopeScheduling

from django_redis.cache import BaseCache
from tests.settings_wrapper import SettingsWrapper

# Redis versions to test against
# redis:8 - Latest stable (8.2.x)
# redis:7.2 - Last 7.x version (7.2.x)
REDIS_VERSIONS = ["redis:8", "redis:7.2"]


class FixtureScheduling(LoadScopeScheduling):
    """Split by [] value. This is very hackish and might blow up any time!"""

    def _split_scope(self, nodeid):
        if "[sqlite" in nodeid:
            return nodeid.rsplit("[")[-1].replace("]", "")
        return None


def pytest_xdist_make_scheduler(log, config):
    return FixtureScheduling(config, log)


def pytest_addoption(parser):
    """Add custom command-line options."""
    parser.addoption(
        "--redis-versions",
        action="store_true",
        default=False,
        help="Test against all configured Redis versions instead of just the latest",
    )


def pytest_configure(config):
    sys.path.insert(0, str(Path(__file__).absolute().parent))


def pytest_sessionfinish():
    """Clean up all Redis containers at the end of the test session."""
    from contextlib import suppress

    for container in _CONTAINER_CACHE.values():
        with suppress(Exception):
            container.stop()
    _CONTAINER_CACHE.clear()


@pytest.fixture(scope="session")
def redis_version(request):
    """
    Parametrized fixture to select Redis version.

    Can be parametrized to test different Redis versions.
    Defaults to latest if not parametrized.
    """
    return getattr(request, "param", REDIS_VERSIONS[0])


# Cache of running containers per Redis version to avoid restarting
_CONTAINER_CACHE = {}


@pytest.fixture(scope="session")
def cache_container(redis_version):
    """
    Session-scoped container that starts Redis for a specific version.

    Uses container caching to avoid restarting containers when testing
    multiple Redis versions in the same session.
    """
    # Reuse container if already started for this version
    if redis_version in _CONTAINER_CACHE:
        container = _CONTAINER_CACHE[redis_version]
    else:
        # Start new container for this Redis version
        container = RedisContainer(redis_version)
        container.start()
        _CONTAINER_CACHE[redis_version] = container

    # Store connection info in environment variables
    host = container.get_container_host_ip()
    port = container.get_exposed_port(6379)
    environ["REDIS_HOST"] = host
    environ["REDIS_PORT"] = str(port)
    environ["REDIS_VERSION"] = redis_version

    yield container

    # Don't stop here - let pytest_sessionfinish handle cleanup


@pytest.fixture()
def settings():
    """A Django settings object which restores changes after the testrun"""
    wrapper = SettingsWrapper()
    yield wrapper
    wrapper.finalize()


@pytest.fixture()
def cache(
    cache_settings: str,
    cache_container,
) -> Iterable[BaseCache]:
    """
    Django cache fixture that uses the container-based Redis setup.

    Depends on cache_container to ensure Redis is running before Django setup.
    """
    from django import setup

    environ["DJANGO_SETTINGS_MODULE"] = f"settings.{cache_settings}"
    setup()

    from django.core.cache import cache as default_cache

    yield default_cache
    default_cache.clear()


def pytest_generate_tests(metafunc):
    # Parametrize Redis version if requested via --redis-versions flag
    # Check for cache_container or cache fixtures which depend on redis_version
    needs_redis_version = (
        "redis_version" in metafunc.fixturenames
        or "cache_container" in metafunc.fixturenames
        or "cache" in metafunc.fixturenames
    )
    if needs_redis_version and metafunc.config.getoption(
        "--redis-versions",
        default=False,
    ):
        metafunc.parametrize("redis_version", REDIS_VERSIONS, scope="session")

    if "cache" in metafunc.fixturenames or "session" in metafunc.fixturenames:
        # Container-based settings that use dynamic Redis connection from env vars
        # Each uses a different database number for isolation
        settings = [
            "base_container",  # db=1, no compression
            "container_gzip",  # db=2, gzip compression
            # Future additions:
            # "container_lz4",     # db=3, lz4 compression
            # "container_msgpack", # db=4, msgpack serializer
            # "container_json",    # db=5, json serializer
        ]
        metafunc.parametrize("cache_settings", settings)
