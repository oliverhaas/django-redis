# django-redis-ng TODO

Features and changes we want to make.

## Compatibility

- Redis server 6.x and 7.x (redis-py 5.x)
- Python 3.12, 3.13, 3.14
- Django 5.2, 6.0

## Planned Features

- [ ] Support Valkey client (valkey-py)
  - Branches: `research/valkey-py`, `research/valkey-glide`
- [ ] Add async Django cache interface (official Django async cache API)
  - Branch: `feat/async-support`
- [ ] Add async API for all other methods
- [ ] Add more Redis method support (everything commonly used)
  - Branches: `feat/list-methods-mixin`, `feat/list-operations-mixin`
  - Branches: `refactor/hash-operations-mixin`, `refactor/set-methods-mixin`, `refactor/set-operations-mixin`
  - Branch: `refactor/fix-hash-method-parameters`, `refactor/rename-name-to-key`
- [ ] Use Python 3.14 builtin zstd when available (with backport fallback)

## Testing

- [ ] Use testcontainers with Redis and Valkey images instead of Docker Compose
  - Parametrized session fixture for Redis/Valkey
  - Branch: `test/containers`
- [ ] Fake cache backend (locmem-style or fakeredis) for testing without Redis

## Code Quality

- [ ] Full type annotations up to Django layer (user-facing typing support)
  - 73 mypy errors remaining
- [ ] Enable more ruff rules (disable/exclude instead of explicit enable, like django-nested-values)
- [ ] Stricter mypy configuration
- [ ] Clean up config as changes are made

## Tooling/Infrastructure

- [x] Migrate to pyproject.toml with hatchling
- [x] Switch to UV for package management
- [x] MkDocs documentation with Material theme
- [x] Modern CI/CD with auto-tagging and publishing
- [x] Update CI matrix for Python 3.12-3.14 and Django 5.2-6.0
