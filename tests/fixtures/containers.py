"""Container fixtures for Redis and Sentinel using testcontainers."""

from collections.abc import Callable, Generator
from contextlib import suppress
from os import environ
from typing import NamedTuple

import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

import docker

# Available Redis-compatible images
REDIS_IMAGES = ["redis:latest", "redis/redis-stack-server:latest", "valkey/valkey:latest"]
DEFAULT_REDIS_IMAGE = "redis:latest"


class ContainerInfo(NamedTuple):
    """Container connection info plus the container object for internal operations."""

    host: str
    port: int
    container: DockerContainer


def _get_container_internal_ip(container: DockerContainer) -> str:
    """Get the internal Docker network IP of a container."""
    client = docker.from_env()
    container_info = client.containers.get(container.get_wrapped_container().id)
    return container_info.attrs["NetworkSettings"]["IPAddress"]


def _start_redis_container(image: str) -> ContainerInfo:
    """Start a Redis container with the given image."""
    container = DockerContainer(image)
    container.with_exposed_ports(6379)
    container.with_command("redis-server --enable-debug-command yes --protected-mode no")
    container.start()
    wait_for_logs(container, "Ready to accept connections")
    return ContainerInfo(
        host=container.get_container_host_ip(),
        port=int(container.get_exposed_port(6379)),
        container=container,
    )


def _start_sentinel_container(image: str, redis_internal_ip: str) -> ContainerInfo:
    """Start a Redis Sentinel container with the given image."""
    sentinel_conf = f"""
sentinel monitor mymaster {redis_internal_ip} 6379 1
sentinel down-after-milliseconds mymaster 5000
sentinel failover-timeout mymaster 60000
sentinel parallel-syncs mymaster 1
"""
    container = DockerContainer(image)
    container.with_exposed_ports(26379)
    container.with_command(
        f"sh -c 'echo \"{sentinel_conf}\" > /tmp/sentinel.conf && redis-sentinel /tmp/sentinel.conf --port 26379'",
    )
    container.start()
    wait_for_logs(container, r"\+monitor master")
    return ContainerInfo(
        host=container.get_container_host_ip(),
        port=int(container.get_exposed_port(26379)),
        container=container,
    )


# Type alias for container factory functions
ContainerFactory = Callable[[str], tuple[str, int]]


@pytest.fixture(params=REDIS_IMAGES)
def redis_images(request) -> str:
    """Parametrized Redis image fixture. Request this to test all Redis-compatible images."""
    return request.param


@pytest.fixture(scope="session")
def redis_container_factory() -> Generator[tuple[ContainerFactory, dict[str, ContainerInfo]]]:
    """Session-scoped factory that creates and caches Redis containers by image.

    Returns both the factory function and the cache dict (for sentinel to access containers).
    """
    cache: dict[str, ContainerInfo] = {}

    def get_container(image: str) -> tuple[str, int]:
        if image not in cache:
            cache[image] = _start_redis_container(image)
        info = cache[image]
        return info.host, info.port

    yield get_container, cache

    # Cleanup all containers at session end
    for info in cache.values():
        with suppress(Exception):
            info.container.stop()


@pytest.fixture(scope="session")
def sentinel_container_factory(
    redis_container_factory: tuple[ContainerFactory, dict[str, ContainerInfo]],
) -> Generator[ContainerFactory]:
    """Session-scoped factory that creates and caches Sentinel containers by image."""
    redis_factory, redis_cache = redis_container_factory
    sentinel_cache: dict[str, ContainerInfo] = {}

    def get_container(image: str) -> tuple[str, int]:
        # Ensure redis container exists first
        redis_factory(image)

        if image not in sentinel_cache:
            redis_internal_ip = _get_container_internal_ip(redis_cache[image].container)
            sentinel_cache[image] = _start_sentinel_container(image, redis_internal_ip)

        info = sentinel_cache[image]
        return info.host, info.port

    yield get_container

    # Cleanup sentinel containers at session end
    for info in sentinel_cache.values():
        with suppress(Exception):
            info.container.stop()


@pytest.fixture
def redis_container(
    redis_container_factory: tuple[ContainerFactory, dict[str, ContainerInfo]],
    request: pytest.FixtureRequest,
) -> tuple[str, int]:
    """Get a Redis container, using redis_images if opted in."""
    factory, _ = redis_container_factory
    image = request.getfixturevalue("redis_images") if "redis_images" in request.fixturenames else DEFAULT_REDIS_IMAGE

    host, port = factory(image)
    environ["REDIS_HOST"] = host
    environ["REDIS_PORT"] = str(port)
    return host, port


@pytest.fixture
def sentinel_container(
    sentinel_container_factory: ContainerFactory,
    request: pytest.FixtureRequest,
) -> tuple[str, int]:
    """Get a Sentinel container, using redis_images if opted in."""
    image = request.getfixturevalue("redis_images") if "redis_images" in request.fixturenames else DEFAULT_REDIS_IMAGE

    host, port = sentinel_container_factory(image)
    environ["SENTINEL_HOST"] = host
    environ["SENTINEL_PORT"] = str(port)
    return host, port
