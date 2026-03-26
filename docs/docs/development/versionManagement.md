# Version Management in Caracal Core

## Overview

Caracal Core uses a centralized version management system where the `VERSION` file at the root of the project serves as the single source of truth for all version references.

## Architecture

### Single Source of Truth

The `VERSION` file contains only the version number (e.g., `1.0.0`) and is used by:

1. **Python Package** (`pyproject.toml`, `setup.py`)
2. **Runtime Code** (`caracal/_version.py`, `caracal/__init__.py`)
3. **CLI/TUI Runtime Metadata** (version surfaced by commands and UI)

### How It Works

#### Python Package

**pyproject.toml:**
```toml
[project]
name = "caracal-core"
dynamic = ["version"]

[tool.setuptools.dynamic]
version = {file = ["VERSION"]}
```

**setup.py:**
```python
from pathlib import Path
from setuptools import setup

version_file = Path(__file__).parent / "VERSION"
version = version_file.read_text().strip()

setup(version=version)
```

**caracal/_version.py:**
```python
from pathlib import Path

def get_version() -> str:
    version_file = Path(__file__).parent.parent / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return "unknown"

__version__ = get_version()
```

**caracal/__init__.py:**
```python
from caracal._version import __version__

__all__ = ["__version__"]
```

Gateway deployment artifacts (Docker gateway image, Helm, Kubernetes manifests)
are enterprise-only and are versioned in the enterprise repository.

## Usage

### Updating the Version

1. **Edit VERSION file:**
   ```bash
   echo "1.0.0" > VERSION
   ```

2. **Update all references:**
   ```bash
   ./scripts/update-version.sh
   ```

3. **Verify changes:**
   ```bash
   git diff
   ```

4. **Commit changes:**
   ```bash
   git add VERSION pyproject.toml
   git commit -m "Bump version to 1.0.0"
   ```

### Automated Release

Use the release script for a complete release process:

```bash
./scripts/release.sh
```

This will:
1. Update all version references
2. Create git tag (optional)
3. Publish to PyPI (optional)

### Manual Release Steps

If you prefer manual control:

```bash
# 1. Update version
echo "1.0.0" > VERSION

# 2. Update references
./scripts/update-version.sh

# 3. Commit changes
git add VERSION pyproject.toml
git commit -m "Bump version to 1.0.0"

# 4. Create tag
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin main
git push origin v1.0.0

# 5. Publish to PyPI
python -m build
twine upload dist/*
```

## Version Format

Caracal Core follows [Semantic Versioning](https://semver.org/):

- **MAJOR.MINOR.PATCH** (e.g., `1.0.0`)
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Version Prefixes

- **Git tags**: Use `v` prefix (e.g., `v1.0.0`)
- **Python package**: No `v` prefix (e.g., `version = "1.0.0"`)

## Files Updated by Scripts

`release.sh` orchestrates the open-source release process by updating versioned
metadata, tagging, and publishing package artifacts.

## Accessing Version at Runtime

### Python Code

```python
import caracal
print(caracal.__version__)  # e.g., "1.0.0"
```

### CLI

```bash
caracal --version
```

## Best Practices

1. **Always update VERSION file first** before running scripts
2. **Run update-version.sh** after changing VERSION file
3. **Commit VERSION file changes** with all updated references
4. **Use semantic versioning** for version numbers
5. **Tag releases** with `v` prefix (e.g., `v1.0.0`)
6. **Test locally** before pushing tags
7. **Document changes** in RELEASE_NOTES.md

## Troubleshooting

### Version Mismatch

If you see version mismatches:

```bash
# Re-run update script
./scripts/update-version.sh

# Verify all files are updated
git diff
```

### Python Package Version

If Python package shows wrong version:

```bash
# Rebuild package
python -m build

# Check version
python -c "import caracal; print(caracal.__version__)"
```

### Docker Image Version

If Docker images have wrong tags:

```bash
# Rebuild images
./scripts/build-images.sh

# Verify tags
docker images | grep caracal
```

## Migration from Hardcoded Versions

If you're migrating from hardcoded versions:

1. Create VERSION file with current version
2. Update pyproject.toml to use dynamic versioning
3. Update setup.py to read from VERSION file
4. Create _version.py module
5. Update __init__.py to import from _version.py
6. Run update-version.sh to update all references
7. Test that version is correctly read everywhere

## References

- [Semantic Versioning](https://semver.org/)
- [PEP 440 - Version Identification](https://www.python.org/dev/peps/pep-0440/)
- [setuptools Dynamic Metadata](https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#dynamic-metadata)
