# Test Fixtures

This directory contains test data and fixture files used by the test suite.

## Directory Structure

```
fixtures/
├── README.md           # This file
├── gps/                # GPS-related test data
│   └── (sample GPS tracks and coordinates)
└── (future fixture directories)
```

## Usage Guidelines

### Adding New Fixtures

1. **Keep files small**: Use minimal sample data that still exercises the code paths
2. **Use descriptive names**: `valid_h264_metadata.json` is better than `test1.json`
3. **Document the purpose**: Add comments or a README explaining each fixture
4. **Avoid binary files when possible**: Use JSON/text representations where feasible

### Sample Config Files

For configuration testing, use the fixtures provided in `tests/conftest.py`:

```python
def test_with_mock_config(mock_config):
    # mock_config is pre-configured with test values
    assert mock_config.encoding.mode == "hardware"
```

### Video File Testing

**DO NOT** commit actual video files to this repository. Instead:

1. Use mock metadata in tests (see `sample_h264_metadata` fixture)
2. Create empty placeholder files with `path.touch()`
3. Mock FFmpeg/FFprobe responses

Example:
```python
def test_video_processing(sample_video_path, mock_ffprobe):
    # sample_video_path is an empty file
    # mock_ffprobe returns predefined probe results
    result = analyze_video(sample_video_path)
    assert result.codec == "h264"
```

### GPS Test Data

The `gps/` directory contains sample GPS data for testing location-related features:

- Sample GPX tracks
- Coordinate test cases
- Timezone test data

### Creating Test Fixtures Programmatically

For complex test data, create it in fixtures:

```python
@pytest.fixture
def complex_conversion_job(temp_dir, mock_config):
    """Create a complete conversion job for integration testing."""
    input_file = temp_dir / "input.mp4"
    input_file.touch()

    return ConversionJob(
        input_path=input_file,
        output_dir=temp_dir / "output",
        config=mock_config,
    )
```

## File Size Limits

- Individual fixture files: < 1 MB
- Total fixtures directory: < 10 MB
- If larger files are needed, generate them in tests or download during CI

## Updating Fixtures

When updating fixtures:

1. Ensure backward compatibility with existing tests
2. Update this README if structure changes
3. Run the full test suite to verify changes
