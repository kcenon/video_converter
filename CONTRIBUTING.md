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

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/video_converter

# Run specific test file
pytest tests/unit/test_codec_detector.py
```

## Code Style

This project uses:
- **Ruff** for linting and formatting
- **MyPy** for type checking

Before submitting a PR, ensure your code passes:
```bash
ruff check src/
ruff format src/
mypy src/
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Run tests and linting
5. Commit your changes with a descriptive message
6. Push to your fork
7. Create a Pull Request

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
