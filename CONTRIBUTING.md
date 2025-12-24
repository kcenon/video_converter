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

# Skip E2E tests (run only quick tests)
pytest -m "not e2e"
```

### Running E2E Tests

End-to-end tests perform actual video conversions and require:
- FFmpeg installed
- ExifTool installed
- Sufficient disk space

```bash
# Run E2E tests
pytest tests/gui/test_e2e.py -v -m e2e

# Run all GUI tests including E2E
pytest tests/gui/ -v
```

**Note:** E2E tests are slower (may take several minutes) and are excluded from regular CI runs. They run on:
- Weekly schedule (Sunday 2 AM UTC)
- Manual workflow dispatch
- Commits containing `[e2e]` in the message

### Test Structure

- `tests/unit/` - Unit tests for individual modules
  - `tests/unit/cli/` - CLI command tests (convert, run, stats, config, service)
- `tests/gui/` - GUI tests with pytest-qt
  - `tests/gui/test_e2e.py` - End-to-end tests with actual conversions
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
- **Test**: pytest on Python 3.10, 3.11, 3.12 (excludes E2E tests)
- **E2E Tests**: Runs on schedule, manual trigger, or `[e2e]` commits
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

## Documentation

### Building Documentation

Documentation is built using MkDocs with the Material theme.

```bash
# Install documentation dependencies
pip install -e ".[docs]"

# Build documentation
mkdocs build

# Serve documentation locally
mkdocs serve
# Then open http://localhost:8000
```

### Generating Architecture Diagrams

Architecture diagrams are auto-generated from the codebase using pyreverse and pydeps:

```bash
# Generate all architecture diagrams
python scripts/generate_diagrams.py

# Output to custom directory
python scripts/generate_diagrams.py --output-dir path/to/output
```

This generates:
- `classes_video_converter.svg` - UML class diagram
- `packages_video_converter.svg` - Package structure diagram
- `dependencies.svg` - Full dependency graph
- `core_dependencies.svg` - Core module dependencies

**Prerequisites:**
- Graphviz must be installed for SVG output: `brew install graphviz`

### API Documentation

API documentation is automatically generated from docstrings using mkdocstrings.
Use Google-style docstrings in your code:

```python
def convert(self, request: ConversionRequest) -> ConversionResult:
    """Convert a video from H.264 to H.265.

    Args:
        request: The conversion request containing input/output paths and options.

    Returns:
        ConversionResult with status and output path.

    Raises:
        ConversionError: If FFmpeg fails to convert the video.
    """
```

## Reporting Issues

When reporting issues, please include:
- macOS version
- Python version
- FFmpeg version
- Steps to reproduce
- Expected vs actual behavior

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
