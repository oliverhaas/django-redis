"""Tests for ClusterClient and ClusterConnectionFactory."""

from unittest.mock import MagicMock, patch

import pytest

from django_redis.client.cluster import ClusterClient
from django_redis.pool import ClusterConnectionFactory


class TestClusterConnectionFactory:
    """Tests for ClusterConnectionFactory."""

    def setup_method(self):
        """Clear the cluster cache before each test."""
        ClusterConnectionFactory._clusters.clear()

    def test_init(self):
        """Test factory initialization."""
        options = {"PASSWORD": "secret", "SOCKET_TIMEOUT": 10}
        factory = ClusterConnectionFactory(options)

        assert factory.options == options
        assert factory.redis_client_cls_kwargs == {}

    def test_init_with_client_kwargs(self):
        """Test factory initialization with client kwargs."""
        options = {"REDIS_CLIENT_KWARGS": {"decode_responses": True}}
        factory = ClusterConnectionFactory(options)

        assert factory.redis_client_cls_kwargs == {"decode_responses": True}

    def test_make_connection_params_basic(self):
        """Test basic connection params from URL."""
        factory = ClusterConnectionFactory({})
        params = factory.make_connection_params("redis://localhost:7000")

        assert params["host"] == "localhost"
        assert params["port"] == 7000

    def test_make_connection_params_with_password(self):
        """Test connection params include password from options."""
        factory = ClusterConnectionFactory({"PASSWORD": "secret123"})
        params = factory.make_connection_params("redis://localhost:7000")

        assert params["password"] == "secret123"  # noqa: S105

    def test_make_connection_params_with_timeouts(self):
        """Test connection params include timeout settings."""
        factory = ClusterConnectionFactory(
            {
                "SOCKET_TIMEOUT": 5.0,
                "SOCKET_CONNECT_TIMEOUT": 3.0,
            },
        )
        params = factory.make_connection_params("redis://localhost:7000")

        assert params["socket_timeout"] == 5.0
        assert params["socket_connect_timeout"] == 3.0

    def test_make_connection_params_invalid_timeout(self):
        """Test that invalid timeout raises error."""
        from django.core.exceptions import ImproperlyConfigured

        factory = ClusterConnectionFactory({"SOCKET_TIMEOUT": "invalid"})

        with pytest.raises(ImproperlyConfigured):
            factory.make_connection_params("redis://localhost:7000")

    @patch("django_redis.pool.RedisCluster")
    def test_connect_creates_cluster(self, mock_cluster_cls):
        """Test connect creates a RedisCluster instance."""
        mock_cluster = MagicMock()
        mock_cluster_cls.return_value = mock_cluster

        factory = ClusterConnectionFactory({})
        result = factory.connect("redis://localhost:7000")

        assert result == mock_cluster
        mock_cluster_cls.assert_called_once()

    @patch("django_redis.pool.RedisCluster")
    def test_connect_caches_cluster(self, mock_cluster_cls):
        """Test connect caches cluster instances."""
        mock_cluster = MagicMock()
        mock_cluster_cls.return_value = mock_cluster

        factory = ClusterConnectionFactory({})
        result1 = factory.connect("redis://localhost:7000")
        result2 = factory.connect("redis://localhost:7000")

        assert result1 is result2
        assert mock_cluster_cls.call_count == 1

    def test_disconnect(self):
        """Test disconnect calls close on cluster."""
        mock_cluster = MagicMock()
        factory = ClusterConnectionFactory({})

        factory.disconnect(mock_cluster)

        mock_cluster.close.assert_called_once()


class TestClusterClient:
    """Tests for ClusterClient."""

    @patch("django_redis.pool.get_connection_factory")
    def test_init(self, mock_get_factory):
        """Test ClusterClient initialization."""
        mock_factory = MagicMock()
        mock_get_factory.return_value = mock_factory

        mock_backend = MagicMock()
        mock_backend.key_prefix = ""
        mock_backend.version = 1
        mock_backend.key_func = lambda k, p, v: f"{p}:{v}:{k}"

        client = ClusterClient(
            server=["redis://localhost:7000"],
            params={"OPTIONS": {}},
            backend=mock_backend,
        )

        # Cluster client always has single client slot
        assert len(client._clients) == 1

    @patch("django_redis.pool.get_connection_factory")
    def test_get_next_client_index_always_zero(self, mock_get_factory):
        """Test that get_next_client_index always returns 0 for cluster."""
        mock_factory = MagicMock()
        mock_get_factory.return_value = mock_factory

        mock_backend = MagicMock()
        mock_backend.key_prefix = ""
        mock_backend.version = 1
        mock_backend.key_func = lambda k, p, v: f"{p}:{v}:{k}"

        client = ClusterClient(
            server=["redis://localhost:7000", "redis://localhost:7001"],
            params={"OPTIONS": {}},
            backend=mock_backend,
        )

        # Should always return 0 regardless of write flag or tried list
        assert client.get_next_client_index(write=True) == 0
        assert client.get_next_client_index(write=False) == 0
        assert client.get_next_client_index(write=True, tried=[0]) == 0

    @patch("django_redis.pool.get_connection_factory")
    def test_get_client(self, mock_get_factory):
        """Test get_client returns cluster connection."""
        mock_cluster = MagicMock()
        mock_factory = MagicMock()
        mock_factory.connect.return_value = mock_cluster
        mock_get_factory.return_value = mock_factory

        mock_backend = MagicMock()
        mock_backend.key_prefix = ""
        mock_backend.version = 1
        mock_backend.key_func = lambda k, p, v: f"{p}:{v}:{k}"

        client = ClusterClient(
            server=["redis://localhost:7000"],
            params={"OPTIONS": {}},
            backend=mock_backend,
        )

        result = client.get_client()

        assert result == mock_cluster
        mock_factory.connect.assert_called_once_with("redis://localhost:7000")

    @patch("django_redis.pool.get_connection_factory")
    def test_get_client_caches_connection(self, mock_get_factory):
        """Test get_client caches the connection."""
        mock_cluster = MagicMock()
        mock_factory = MagicMock()
        mock_factory.connect.return_value = mock_cluster
        mock_get_factory.return_value = mock_factory

        mock_backend = MagicMock()
        mock_backend.key_prefix = ""
        mock_backend.version = 1
        mock_backend.key_func = lambda k, p, v: f"{p}:{v}:{k}"

        client = ClusterClient(
            server=["redis://localhost:7000"],
            params={"OPTIONS": {}},
            backend=mock_backend,
        )

        result1 = client.get_client()
        result2 = client.get_client()

        assert result1 is result2
        assert mock_factory.connect.call_count == 1

    @patch("django_redis.pool.get_connection_factory")
    def test_do_close_clients(self, mock_get_factory):
        """Test do_close_clients closes the cluster connection."""
        mock_cluster = MagicMock()
        mock_factory = MagicMock()
        mock_factory.connect.return_value = mock_cluster
        mock_get_factory.return_value = mock_factory

        mock_backend = MagicMock()
        mock_backend.key_prefix = ""
        mock_backend.version = 1
        mock_backend.key_func = lambda k, p, v: f"{p}:{v}:{k}"

        client = ClusterClient(
            server=["redis://localhost:7000"],
            params={"OPTIONS": {}},
            backend=mock_backend,
        )

        # Connect first
        client.get_client()

        # Close
        client.do_close_clients()

        mock_cluster.close.assert_called_once()
        assert client._clients == [None]
