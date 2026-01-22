# django-redis-ng TODO

Features and changes we want to make.

## Planned Features

- [ ] Support Valkey client (valkey-py)
- [ ] Fake cache backend (locmem-style or fakeredis) for testing without Redis

## Compatibility

- Redis server 6.x and 7.x (redis-py 5.x)
- Python 3.12, 3.13, 3.14
- Django 5.2, 6.0

## Tooling/Infrastructure

- [x] Migrate to pyproject.toml with hatchling
- [x] Switch to UV for package management
- [x] MkDocs documentation with Material theme
- [x] Modern CI/CD with auto-tagging and publishing
- [x] Update CI matrix for Python 3.12-3.14 and Django 5.2-6.0

## Code Quality

- [ ] Full type annotations (73 mypy errors remaining)
- [ ] Stricter mypy configuration
