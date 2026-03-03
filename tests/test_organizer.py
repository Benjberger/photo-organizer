"""Tests for the organizer module.

These tests use 'tmp_path' — a pytest feature that creates a fresh temporary
directory for each test. This means our tests never touch real files and
each test starts with a clean slate.
"""

from pathlib import Path
from datetime import datetime
from unittest.mock import patch

from photo_organizer.organizer import (
    scan_photos,
    plan_organization,
    preview_organization,
    execute_organization,
    _resolve_collision,
)


def _create_fake_photo(directory, name):
    """Helper: create a fake photo file for testing."""
    filepath = directory / name
    filepath.write_bytes(b"fake photo data")
    return filepath


# --- Test scan_photos() ---

def test_scan_finds_photos(tmp_path):
    """Should find JPEG and RAW files."""
    _create_fake_photo(tmp_path, "photo1.jpg")
    _create_fake_photo(tmp_path, "photo2.cr2")
    _create_fake_photo(tmp_path, "document.txt")  # Should be ignored

    photos = list(scan_photos(tmp_path))
    names = [p.name for p in photos]

    assert "photo1.jpg" in names
    assert "photo2.cr2" in names
    assert "document.txt" not in names


def test_scan_finds_nested_photos(tmp_path):
    """Should find photos in subdirectories too."""
    subfolder = tmp_path / "subfolder"
    subfolder.mkdir()
    _create_fake_photo(tmp_path, "top.jpg")
    _create_fake_photo(subfolder, "nested.jpg")

    photos = list(scan_photos(tmp_path))
    names = [p.name for p in photos]

    assert "top.jpg" in names
    assert "nested.jpg" in names


def test_scan_empty_directory(tmp_path):
    """Should return nothing for a directory with no photos."""
    _create_fake_photo(tmp_path, "readme.txt")
    photos = list(scan_photos(tmp_path))
    assert photos == []


def test_scan_invalid_directory():
    """Should raise ValueError for a non-existent directory."""
    try:
        list(scan_photos("/nonexistent/path"))
        assert False, "Should have raised ValueError"
    except ValueError:
        pass  # Expected


# --- Test plan_organization() ---

def test_plan_with_dated_photo(tmp_path):
    """Photos with EXIF dates should go into YYYY/YYYY-MM-DD/ folders."""
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()

    _create_fake_photo(source, "photo.jpg")

    fake_date = datetime(2024, 6, 15, 14, 30, 0)
    with patch("photo_organizer.organizer.get_date_taken", return_value=fake_date):
        moves = plan_organization(source, dest)

    assert len(moves) == 1
    src, dst = moves[0]
    assert "2024" in str(dst)
    assert "2024-06-15" in str(dst)
    assert dst.name == "photo.jpg"


def test_plan_with_undated_photo(tmp_path):
    """Photos without EXIF dates should go into 'undated' folder."""
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()

    _create_fake_photo(source, "old_photo.jpg")

    with patch("photo_organizer.organizer.get_date_taken", return_value=None):
        moves = plan_organization(source, dest)

    assert len(moves) == 1
    _, dst = moves[0]
    assert "undated" in str(dst)


# --- Test execute_organization() ---

def test_execute_copy(tmp_path):
    """Should copy photos to destination, keeping originals."""
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()

    photo = _create_fake_photo(source, "test.jpg")
    dest_file = dest / "2024" / "2024-06-15" / "test.jpg"

    moves = [(photo, dest_file)]
    results = execute_organization(moves, mode="copy")

    assert results["success"] == 1
    assert results["failed"] == 0
    assert dest_file.exists()
    assert photo.exists()  # Original still there (copy, not move)


def test_execute_move(tmp_path):
    """Should move photos, removing originals."""
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()

    photo = _create_fake_photo(source, "test.jpg")
    dest_file = dest / "organized" / "test.jpg"

    moves = [(photo, dest_file)]
    results = execute_organization(moves, mode="move")

    assert results["success"] == 1
    assert dest_file.exists()
    assert not photo.exists()  # Original is gone (moved)


# --- Test _resolve_collision() ---

def test_no_collision(tmp_path):
    """If file doesn't exist, return the same path."""
    path = tmp_path / "photo.jpg"
    assert _resolve_collision(path) == path


def test_collision_adds_number(tmp_path):
    """If file exists, should add _1 suffix."""
    existing = tmp_path / "photo.jpg"
    existing.write_bytes(b"existing")

    result = _resolve_collision(existing)
    assert result.name == "photo_1.jpg"


# --- Test preview_organization() ---

def test_preview_format():
    """Preview should list files grouped by folder."""
    moves = [
        (Path("/source/a.jpg"), Path("/dest/2024/2024-01-01/a.jpg")),
        (Path("/source/b.jpg"), Path("/dest/2024/2024-01-01/b.jpg")),
    ]
    output = preview_organization(moves)
    assert "2 photo(s)" in output
    assert "a.jpg" in output
    assert "b.jpg" in output


def test_preview_empty():
    """No photos should give a clear message."""
    output = preview_organization([])
    assert "No photos found" in output
