# Contributing to Video Converter

Thank you for your interest in contributing to Video Converter! This document provides guidelines for contributing to the project.

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/kcenon/video_converter.git
   cd video_converter
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Install external tools**
   ```bash
   brew install ffmpeg exiftool
   ```

5. **Set up pre-commit hooks**
   ```bash
   pre-commit install
   ```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/video_converter

# Run only unit tests
pytest tests/unit

# Run specific test file
pytest tests/unit/test_codec_detector.py

# Skip slow tests
pytest -m "not slow"

# Skip integration tests
pytest -m "not integration"
```

### Test Structure

- `tests/unit/` - Unit tests for individual modules
  - `tests/unit/cli/` - CLI command tests (convert, run, stats, config, service)
- `tests/integration/` - Integration tests for component interactions
- `tests/fixtures/` - Test data and fixture files
- `tests/conftest.py` - Shared fixtures for all tests

### Running CLI Tests

```bash
# Run all CLI tests
pytest tests/unit/cli/

# Run specific command tests
pytest tests/unit/cli/test_convert_cmd.py
pytest tests/unit/cli/test_service_cmd.py
```

## Code Style

This project uses:
- **Ruff** for linting and formatting
- **MyPy** for type checking
- **pre-commit** for automated checks

Pre-commit hooks will automatically run on each commit. To run manually:
```bash
# Run all hooks on all files
pre-commit run --all-files

# Run specific hook
pre-commit run ruff --all-files
```

You can also run checks manually:
```bash
ruff check src/
ruff format src/
mypy src/
```

## Continuous Integration

All pull requests are automatically checked by GitHub Actions:

- **Lint**: Ruff linter and formatter checks
- **Type Check**: MyPy static type analysis
- **Test**: pytest on Python 3.10, 3.11, 3.12
- **Dependency Review**: Security scanning for dependencies

CI must pass before merging. Check the [Actions tab](https://github.com/kcenon/video_converter/actions) for build status.

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Run tests and linting locally
5. Commit your changes with a descriptive message
6. Push to your fork
7. Create a Pull Request
8. Ensure CI checks pass

## Commit Message Format

Use conventional commit format:
```
type(scope): description

[optional body]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

## Reporting Issues

When reporting issues, please include:
- macOS version
- Python version
- FFmpeg version
- Steps to reproduce
- Expected vs actual behavior

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
