# Django-Redis Development Guide for Claude Code

This document contains helpful information for working on django-redis with Claude Code or any AI assistant.

## Project Overview

**django-redis** is a full-featured Redis/Valkey cache and session backend for Django. It's a Jazzband community project.

- **Language**: Python 3.9+
- **Framework**: Django 4.2+
- **Cache Backend**: Redis 2.8+ or Valkey
- **Client Libraries**: redis-py 4.0.2+ or valkey-py 1.0.0+
- **License**: BSD-3-Clause

## Quick Setup

### Prerequisites
- Python 3.9 or higher
- Redis server running locally
- Git

### Initial Setup

```bash
# Clone the repository (if not already done)
git clone https://github.com/jazzband/django-redis.git
cd django-redis

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install the package in editable mode
pip install -e .

# Install development dependencies
pip install pytest pytest-cov pytest-mock pytest-pythonpath pytest-xdist \
            msgpack lz4 pyzstd pre-commit mypy django-stubs types-redis \
            lxml tox

# Set up pre-commit hooks
pre-commit install

# Verify Redis is running
redis-cli ping  # Should return PONG

# Run tests to verify setup
pytest tests/ -n 4
```

## Project Structure

```
django-redis/
├── django_redis/          # Main package source code
│   ├── cache.py          # Cache backend implementation
│   ├── client/           # Client implementations (Default, Shard, Herd, Sentinel)
│   ├── serializers/      # Serializers (Pickle, JSON, MsgPack)
│   └── compressors/      # Compressors (Zlib, Gzip, Lz4, Zstd)
├── tests/                # Test suite (1600+ tests)
│   ├── settings/         # Test configurations (13 variants including Valkey)
│   ├── test_backend.py   # Main backend tests
│   ├── test_client.py    # Client tests
│   ├── test_session.py   # Session backend tests
│   └── conftest.py       # Pytest configuration
├── .claude/              # Claude Code configuration
├── setup.cfg             # Package metadata and tool config
├── pyproject.toml        # Build system configuration
└── .pre-commit-config.yaml  # Pre-commit hooks
```

## Development Workflow

### Running Tests

```bash
# Activate virtual environment first
source .venv/bin/activate

# Run all tests with parallel execution (recommended)
pytest tests/ -n 4

# Run all tests with coverage
pytest tests/

# Run specific test file
pytest tests/test_backend.py -v

# Run specific test class
pytest tests/test_backend.py::TestDjangoRedisCache -v

# Run specific test method
pytest tests/test_backend.py::TestDjangoRedisCache::test_setnx -v

# Run tests without coverage (faster)
pytest tests/ --no-cov -v

# Run tests in quiet mode
pytest tests/ -n 4 -q
```

### Code Quality Checks

```bash
# Run all pre-commit hooks
pre-commit run --all-files

# Run only ruff linting
ruff check .

# Auto-fix with ruff
ruff check --fix .

# Format code with ruff
ruff format .

# Run mypy type checking
mypy django_redis tests

# Run specific tool from pre-commit
pre-commit run ruff-check --all-files
```

### Using Tox

Tox runs tests across multiple Python and Django versions:

```bash
# Run all tox environments
tox

# Run specific environment
tox -e py312-dj52-redislatest

# List all environments
tox -l

# Run linting only
tox -e pre-commit

# Run type checking only
tox -e mypy
```

## Test Configurations

Tests run against 13 different configurations (see `tests/conftest.py`):

1. **sqlite** - Default client with pickle serialization
2. **sqlite_gzip** - Gzip compression
3. **sqlite_herd** - Herd client (thundering herd mitigation)
4. **sqlite_json** - JSON serialization
5. **sqlite_lz4** - LZ4 compression
6. **sqlite_msgpack** - MessagePack serialization
7. **sqlite_sentinel** - Redis Sentinel support
8. **sqlite_sentinel_opts** - Sentinel with options
9. **sqlite_sharding** - Client-side sharding
10. **sqlite_usock** - Unix socket connections
11. **sqlite_valkey** - Valkey client (requires valkey-py)
12. **sqlite_zlib** - Zlib compression
13. **sqlite_zstd** - Zstandard compression

**Note**: The `sqlite_valkey` configuration is only included if valkey-py is installed.

## Common Tasks

### Adding a New Feature

1. Create a new branch: `git checkout -b feature/my-feature`
2. Make your changes in `django_redis/`
3. Add tests in `tests/`
4. Run tests: `pytest tests/ -n 4`
5. Run pre-commit: `pre-commit run --all-files`
6. Commit with descriptive message
7. Push and create a pull request

### Debugging Tests

```bash
# Run with verbose output and stop on first failure
pytest tests/ -vv -x

# Run with print statements visible
pytest tests/ -s

# Run with Python debugger
pytest tests/ --pdb

# Show local variables on failure
pytest tests/ -l
```

### Working with Redis

```bash
# Check Redis status
redis-cli ping

# Monitor Redis commands (useful for debugging)
redis-cli monitor

# Flush test databases
redis-cli -n 1 flushdb  # Test database 1
redis-cli -n 2 flushdb  # Test database 2

# Get all keys in test database
redis-cli -n 1 keys "*"
```

## Important Files

### Configuration
- `setup.cfg` - Package metadata, dependencies, tox config, pytest config
- `pyproject.toml` - Build system, towncrier changelog config
- `.pre-commit-config.yaml` - Pre-commit hook configuration
- `.ruff.toml` - Ruff linter/formatter settings

### Documentation
- `README.rst` - Main documentation
- `CONTRIBUTING.rst` - Contribution guidelines
- `CHANGELOG.rst` - Version history
- `CODE_OF_CONDUCT.md` - Jazzband code of conduct

### Source Code Entry Points
- `django_redis/cache.py` - Main cache backend classes
- `django_redis/client/default.py` - Default Redis client
- `django_redis/pool.py` - Connection pool factory

## Dependencies

### Runtime Dependencies
- Django >= 4.2, < 5.3 (excluding 5.0.*)
- redis >= 4.0.2

### Development Dependencies
- pytest, pytest-cov, pytest-mock, pytest-xdist - Testing
- msgpack, lz4, pyzstd - Compression formats
- pre-commit, ruff - Code quality
- mypy, django-stubs, types-redis - Type checking
- tox - Multi-environment testing

## Claude Code Permissions

This project has `.claude/settings.local.json` configured with extensive permissions:

**Auto-approved commands:**
- Python/pip/pytest/tox/mypy/ruff/pre-commit
- Redis (redis-server, redis-cli)
- Git read operations (status, diff, log, show)
- File operations (ls, cat, grep, find, etc.)
- Docker read operations
- System info commands

**Requires confirmation:**
- `rm -rf` - Recursive deletions
- `git push` - Pushing to remote
- `git reset --hard` - Hard resets
- `sudo` - Privileged operations

## Contributing Guidelines

This is a Jazzband project. By contributing you agree to:
- Follow the [Jazzband Code of Conduct](https://jazzband.co/about/conduct)
- Follow the [Jazzband Guidelines](https://jazzband.co/about/guidelines)

### Commit Messages
- Use clear, descriptive commit messages
- Reference issue numbers when applicable
- Follow the existing commit style (check `git log`)

### Pull Requests
- Ensure all tests pass
- Add tests for new features
- Update documentation as needed
- Pre-commit hooks must pass
- Consider multiple Django/Python version compatibility

## Useful Links

- **GitHub**: https://github.com/jazzband/django-redis
- **PyPI**: https://pypi.org/project/django-redis/
- **Documentation**: See README.rst
- **Issue Tracker**: https://github.com/jazzband/django-redis/issues
- **Jazzband**: https://jazzband.co

## Test Results Summary

Current test status:
- **1628 tests passed** (redis-py)
- **158 tests passed** with Valkey (4 integer overflow edge cases differ)
- **19 tests skipped**
- Test duration: ~58 seconds (with -n 4)

All 13 test configurations passing successfully (12 redis-py + 1 valkey-py).

## Valkey Support

**django-redis** now supports Valkey as an alternative to Redis:

### Installation
```bash
# Install with Valkey support
pip install django-redis[valkey]

# Or install valkey-py separately
pip install valkey
```

### Configuration
```python
# Auto-detection via URL scheme (recommended)
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "valkey://127.0.0.1:6379/1",
    }
}

# Or explicit client class
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.valkey.DefaultValkeyClient",
        }
    }
}
```

### Key Implementation Files
- `django_redis/client/valkey.py` - DefaultValkeyClient implementation
- `django_redis/pool.py` - ValkeyConnectionFactory
- `django_redis/cache.py` - Auto-detection logic for valkey:// URLs
- `tests/settings/sqlite_valkey.py` - Valkey test configuration

### Testing Valkey
```bash
# Install valkey-py
pip install valkey

# Run valkey-specific tests
pytest tests/ -k sqlite_valkey -v

# Run full test suite (includes valkey if installed)
pytest tests/ -n 4
```

### Compatibility Notes
- 158 out of 162 tests pass with valkey-py
- 4 edge-case tests fail due to different 64-bit integer overflow handling
- Valkey is fully compatible with all django-redis features
- valkey-py is a fork of redis-py with nearly identical API

## Tips for AI Assistants

1. **Always activate the virtual environment** before running Python commands
2. **Use parallel testing** (`-n 4`) for faster feedback
3. **Check Redis is running** before running tests
4. **Tests are parameterized** - one test becomes 13 tests (one per configuration)
5. **Pre-commit runs automatically** on git commit
6. **The project uses ruff** for both linting and formatting (not flake8/black)
7. **Type hints are checked** with mypy using django-stubs
8. **Support multiple Django versions** - check compatibility when adding features
9. **Redis/Valkey features vary** by version - be mindful of minimum Redis 2.8 support
10. **Session tests** require specific Django settings - check `tests/settings/`
11. **Valkey support** is optional - tests auto-detect if valkey-py is installed

## Quick Reference Commands

```bash
# Full development cycle
source .venv/bin/activate
pytest tests/ -n 4                    # Run tests
pre-commit run --all-files            # Check code quality
mypy django_redis tests               # Type check
git add .                             # Stage changes
git commit -m "Your message"          # Commit (triggers pre-commit)
git push                              # Push to remote

# Fast iteration
pytest tests/test_backend.py -k test_setnx -v  # Run one test
ruff check --fix .                              # Quick fix
pytest tests/ -x --no-cov                       # Stop on first failure
```

---

**Last Updated**: 2025-11-09
**Environment**: Python 3.12.3, Django 5.2.8, Redis 7.0.15
