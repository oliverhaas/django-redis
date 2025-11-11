# Testing with Testcontainers

This test suite uses [testcontainers-python](https://github.com/testcontainers/testcontainers-python) to automatically start Redis/Valkey containers for testing. This eliminates the need for manual setup and ensures consistent test environments.

## Prerequisites

- **Docker**: Must be installed and running
- **Python 3.9+**: With testcontainers package

## How It Works

### Automatic Container Management

The test suite automatically:
1. **Starts a Redis/Valkey container** at the beginning of the test session
2. **Exposes a random port** to avoid conflicts
3. **Sets environment variables** (`REDIS_HOST`, `REDIS_PORT`) with connection details
4. **Tears down the container** when tests complete

### Container Fixture

Located in `tests/conftest.py`:

```python
@pytest.fixture(scope="session", autouse=True)
def redis_container(redis_backend):
    """Session-scoped container that starts Redis or Valkey."""
    if redis_backend == "valkey":
        container = DockerContainer("valkey/valkey:latest")
        container.with_exposed_ports(6379)
        container.with_command("valkey-server --protected-mode no")
    else:
        container = RedisContainer("redis:latest")

    container.start()
    # ... sets environment variables ...
    yield container
    container.stop()
```

### Test Settings

Test settings files use environment variables for dynamic connection:

```python
# tests/settings/base_container.py
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}?db=1",
        ...
    }
}
```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Specific Test File
```bash
pytest tests/test_backend_lists.py
```

### Run With Coverage
```bash
pytest --cov=django_redis --cov-report=html
```

### Parallel Execution
```bash
pytest -n 4  # Run with 4 workers
```

## Test Configurations

Current configurations test different features:

| Configuration | Database | Features |
|--------------|----------|----------|
| `base_container` | db=1 | No compression, standard setup |
| `container_gzip` | db=2 | Gzip compression |

### Future Configurations (Easy to Add)

The framework supports adding more configurations:

```python
# tests/settings/container_lz4.py
# LZ4 compression variant

# tests/settings/container_msgpack.py
# MessagePack serializer

# tests/settings/container_json.py
# JSON serializer

# tests/settings/container_sentinel.py
# Redis Sentinel for HA testing

# tests/settings/container_cluster.py
# Redis Cluster testing
```

## Switching Between Redis and Valkey

The fixture currently defaults to Redis. To test with Valkey:

```python
@pytest.fixture(scope="session")
def redis_backend():
    return "valkey"  # Change to "valkey" to test Valkey
```

Future enhancement: Could be parametrized to test both in one run.

## Benefits Over Previous Setup

### Before (docker-compose)
- ❌ Requires manual `docker-compose up`
- ❌ Uses fixed port (6379) - conflicts possible
- ❌ External dependency management
- ❌ Manual cleanup needed

### Now (testcontainers)
- ✅ Fully automatic - no manual steps
- ✅ Random ports - no conflicts
- ✅ Self-contained - no external dependencies
- ✅ Automatic cleanup after tests
- ✅ Works in CI without configuration
- ✅ Easy to add new backends (Valkey, etc.)

## Troubleshooting

### Docker Not Running
```
Error: Cannot connect to Docker daemon
```
**Solution**: Start Docker Desktop or Docker daemon

### Port Already in Use
Testcontainers automatically uses random ports, so this shouldn't happen.

### Container Won't Start
```
Error: Failed to pull image
```
**Solution**: Check internet connection and Docker Hub access

### Slow First Run
First run downloads Docker images (redis:latest, valkey:latest).
Subsequent runs are much faster as images are cached.

## Performance

- **Container startup**: ~2-5 seconds (one-time per session)
- **Test execution**: Similar to local Redis
- **Session scope**: Container shared across all tests
- **Cleanup**: Automatic on test completion

## CI/CD Integration

No special configuration needed! Testcontainers works automatically in:
- GitHub Actions
- GitLab CI
- Jenkins
- Any CI with Docker support

Just ensure Docker is available in the CI environment.
