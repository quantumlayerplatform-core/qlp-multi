# Publishing QuantumLayer CLI to PyPI

This guide covers how to publish the QuantumLayer CLI to PyPI.

## Prerequisites

1. PyPI account (https://pypi.org/account/register/)
2. Test PyPI account (https://test.pypi.org/account/register/)
3. API tokens for both PyPI and Test PyPI
4. Python build tools installed

## Setup

1. Install required tools:
```bash
pip install --upgrade build twine
```

2. Configure PyPI credentials:
   - Copy `.pypirc.template` to `~/.pypirc`
   - Update with your API tokens

## Publishing Process

### 1. Update Version

Edit the version in these files:
- `setup.py` (version field)
- `pyproject.toml` (version field)
- `qlp_cli/__init__.py` (__version__)
- `qlp_cli/main.py` (version_option)

### 2. Update CHANGELOG.md

Add release notes for the new version.

### 3. Build the Package

```bash
./build_for_pypi.sh
```

This will:
- Clean previous builds
- Create source distribution and wheel
- Validate the packages

### 4. Test on Test PyPI (Recommended)

```bash
# Upload to Test PyPI
python -m twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ quantumlayer
```

### 5. Publish to PyPI

```bash
# Upload to production PyPI
python -m twine upload dist/*
```

### 6. Verify Installation

```bash
# In a new virtual environment
pip install quantumlayer
qlp --version
```

## Post-Release

1. Tag the release in git:
```bash
git tag -a v0.1.0 -m "Release version 0.1.0"
git push origin v0.1.0
```

2. Create GitHub release with changelog

3. Update documentation

## Troubleshooting

### Common Issues

1. **Package name already taken**: The name "quantumlayer" must be unique on PyPI
2. **Invalid metadata**: Run `twine check dist/*` to validate
3. **Authentication failed**: Ensure ~/.pypirc has correct API tokens
4. **Missing files**: Check MANIFEST.in includes all necessary files

### Validation Commands

```bash
# Check package metadata
twine check dist/*

# Test local installation
pip install dist/quantumlayer-*.whl

# Check installed files
pip show -f quantumlayer
```

## Security Notes

- Never commit `.pypirc` or API tokens
- Use API tokens instead of passwords
- Test on Test PyPI first
- Sign releases with GPG (optional)