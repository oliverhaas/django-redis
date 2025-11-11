import sys
from collections.abc import Iterable
from os import environ
from pathlib import Path

import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.redis import RedisContainer
from xdist.scheduler import LoadScopeScheduling

from django_redis.cache import BaseCache
from tests.settings_wrapper import SettingsWrapper

# Container backend types
CONTAINER_BACKENDS = ["redis", "valkey"]


class FixtureScheduling(LoadScopeScheduling):
    """Split by [] value. This is very hackish and might blow up any time!"""

    def _split_scope(self, nodeid):
        if "[sqlite" in nodeid:
            return nodeid.rsplit("[")[-1].replace("]", "")
        return None


def pytest_xdist_make_scheduler(log, config):
    return FixtureScheduling(config, log)


def pytest_configure(config):
    sys.path.insert(0, str(Path(__file__).absolute().parent))


@pytest.fixture(scope="session")
def container_backend(request):
    """Parametrized fixture to select Redis or Valkey backend."""
    return getattr(request, "param", "redis")


@pytest.fixture(scope="session", autouse=True)
def cache_container(container_backend):
    """
    Session-scoped container that starts Redis or Valkey.

    This fixture is autouse=True so it starts automatically once per test session,
    regardless of which backend is being tested.
    """
    if container_backend == "valkey":
        # Valkey uses the valkey/valkey image
        container = DockerContainer("valkey/valkey:latest")
        container.with_exposed_ports(6379)
        container.with_command("valkey-server --protected-mode no")
    else:
        # Use the built-in RedisContainer for Redis
        container = RedisContainer("redis:latest")

    container.start()

    # Store connection info in environment variables
    host = container.get_container_host_ip()
    port = container.get_exposed_port(6379)
    environ["REDIS_HOST"] = host
    environ["REDIS_PORT"] = str(port)
    environ["REDIS_BACKEND"] = container_backend

    yield container

    container.stop()


@pytest.fixture()
def settings():
    """A Django settings object which restores changes after the testrun"""
    wrapper = SettingsWrapper()
    yield wrapper
    wrapper.finalize()


@pytest.fixture()
def cache(cache_settings: str) -> Iterable[BaseCache]:
    from django import setup

    environ["DJANGO_SETTINGS_MODULE"] = f"settings.{cache_settings}"
    setup()

    from django.core.cache import cache as default_cache

    yield default_cache
    default_cache.clear()


def pytest_generate_tests(metafunc):
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
