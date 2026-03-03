"""Tests for the metadata module.

pytest discovers and runs any function whose name starts with 'test_'.
Each test function checks one specific behavior. If something goes wrong,
the test fails and tells you exactly what broke.

To run tests: python -m pytest tests/ -v
The -v flag means "verbose" — it shows each test name and its result.
"""

from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

from photo_organizer.metadata import (
    is_supported,
    read_metadata,
    get_date_taken,
    format_metadata,
    _dms_to_decimal,
    _format_value,
)


# --- Test is_supported() ---

def test_jpeg_extensions_supported():
    """JPEG files should be recognized."""
    assert is_supported("photo.jpg") is True
    assert is_supported("photo.jpeg") is True
    assert is_supported("photo.JPG") is True  # Case insensitive


def test_raw_extensions_supported():
    """RAW files should be recognized."""
    assert is_supported("photo.cr2") is True
    assert is_supported("photo.nef") is True
    assert is_supported("photo.arw") is True
    assert is_supported("photo.dng") is True


def test_unsupported_extensions():
    """Non-photo files should not be supported."""
    assert is_supported("document.pdf") is False
    assert is_supported("video.mp4") is False
    assert is_supported("readme.txt") is False


def test_path_objects_work():
    """Should accept Path objects, not just strings."""
    assert is_supported(Path("photo.jpg")) is True
    assert is_supported(Path("document.pdf")) is False


# --- Test read_metadata() ---

def test_missing_file():
    """Should return an error dict for files that don't exist."""
    result = read_metadata("nonexistent.jpg")
    assert "Error" in result
    assert "not found" in result["Error"]


def test_unsupported_format(tmp_path):
    """Should return an error for unsupported file types."""
    # Create a real file with an unsupported extension
    test_file = tmp_path / "document.txt"
    test_file.write_text("not a photo")
    result = read_metadata(test_file)
    assert "Error" in result
    assert "Unsupported" in result["Error"]


# --- Test helper functions ---

def test_dms_to_decimal():
    """GPS degrees/minutes/seconds should convert correctly."""
    # 40 degrees, 26 minutes, 46 seconds = ~40.4461
    result = _dms_to_decimal([40, 26, 46])
    assert abs(result - 40.44611) < 0.001


def test_format_value_file_size():
    """File sizes should be human-readable."""
    assert "MB" in _format_value("FileSize", 5_000_000)
    assert "KB" in _format_value("FileSize", 5_000)
    assert "bytes" in _format_value("FileSize", 500)


def test_format_metadata_output():
    """format_metadata should produce readable output."""
    metadata = {
        "Filepath": "/photos/test.jpg",
        "Filetype": ".jpg",
        "Width": 4000,
        "Height": 3000,
        "FileSize": 2_500_000,
    }
    output = format_metadata(metadata)
    assert "test.jpg" in output
    assert "4000" in output
    assert "2.5 MB" in output


# --- Test get_date_taken() with mocking ---

def test_get_date_taken_with_exif(tmp_path):
    """Should extract date from a JPEG with EXIF data.

    We use tmp_path (a pytest feature that gives us a temporary directory)
    and 'mocking' to simulate a JPEG file with EXIF data without needing
    a real photo file.
    """
    # Create a tiny valid JPEG file
    test_file = tmp_path / "test.jpg"
    test_file.write_bytes(b"fake jpeg content")

    # Mock read_metadata to return fake EXIF data
    fake_metadata = {
        "Filepath": str(test_file),
        "DateTimeOriginal": "2024:06:15 14:30:00",
    }
    with patch("photo_organizer.metadata.read_metadata", return_value=fake_metadata):
        result = get_date_taken(test_file)
        assert result == datetime(2024, 6, 15, 14, 30, 0)


def test_get_date_taken_no_exif(tmp_path):
    """Should return None when no date is found."""
    test_file = tmp_path / "test.jpg"
    test_file.write_bytes(b"fake jpeg content")

    fake_metadata = {"Filepath": str(test_file)}
    with patch("photo_organizer.metadata.read_metadata", return_value=fake_metadata):
        result = get_date_taken(test_file)
        assert result is None
