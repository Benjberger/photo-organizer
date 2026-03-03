"""Tests for the renamer module."""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from photo_organizer.renamer import (
    plan_renames,
    preview_renames,
    execute_renames,
    undo_renames,
    _apply_pattern,
    _clean_name,
)


def _create_photo(directory, name, content=b"photo data"):
    """Helper: create a fake photo file."""
    filepath = directory / name
    filepath.write_bytes(content)
    return filepath


# --- Test _clean_name() ---

def test_clean_name_spaces():
    """Spaces should become underscores."""
    assert _clean_name("Canon EOS R5") == "Canon_EOS_R5"


def test_clean_name_special_chars():
    """Special characters should be removed."""
    assert _clean_name("Sony/Alpha (A7)") == "Sony_Alpha_A7"


# --- Test _apply_pattern() ---

def test_apply_pattern_with_date(tmp_path):
    """Pattern with {date} should use EXIF date."""
    photo = _create_photo(tmp_path, "IMG_001.jpg")
    fake_date = datetime(2024, 6, 15, 14, 30, 0)

    with patch("photo_organizer.renamer.get_date_taken", return_value=fake_date), \
         patch("photo_organizer.renamer.read_metadata", return_value={"Make": "Canon"}):
        result = _apply_pattern(photo, "{date}_{camera}_{seq}", 1)

    assert result == "2024-06-15_Canon_001.jpg"


def test_apply_pattern_no_date(tmp_path):
    """Pattern should use 'undated' when no EXIF date exists."""
    photo = _create_photo(tmp_path, "old.jpg")

    with patch("photo_organizer.renamer.get_date_taken", return_value=None), \
         patch("photo_organizer.renamer.read_metadata", return_value={}):
        result = _apply_pattern(photo, "{date}_{seq}", 5)

    assert result == "undated_005.jpg"


def test_apply_pattern_with_location(tmp_path):
    """Pattern with {location} should use provided location name."""
    photo = _create_photo(tmp_path, "IMG_001.jpg")
    fake_date = datetime(2024, 6, 15, 14, 30, 0)

    with patch("photo_organizer.renamer.get_date_taken", return_value=fake_date), \
         patch("photo_organizer.renamer.read_metadata", return_value={}):
        result = _apply_pattern(photo, "{location}_{date}_{seq}", 1, location="Paris")

    assert result == "Paris_2024-06-15_001.jpg"


def test_apply_pattern_location_fallback(tmp_path):
    """Pattern with {location} but no location should use 'unknown'."""
    photo = _create_photo(tmp_path, "IMG_001.jpg")

    with patch("photo_organizer.renamer.get_date_taken", return_value=None), \
         patch("photo_organizer.renamer.read_metadata", return_value={}):
        result = _apply_pattern(photo, "{location}_{seq}", 1, location=None)

    assert result == "unknown_001.jpg"


def test_apply_pattern_preserves_extension(tmp_path):
    """Original file extension should be kept."""
    photo = _create_photo(tmp_path, "RAW_FILE.CR2")

    with patch("photo_organizer.renamer.get_date_taken", return_value=None), \
         patch("photo_organizer.renamer.read_metadata", return_value={}):
        result = _apply_pattern(photo, "{seq}", 1)

    assert result == "001.cr2"  # Extension lowercased


def test_apply_pattern_original_name(tmp_path):
    """Pattern with {original} should include the original filename."""
    photo = _create_photo(tmp_path, "vacation.jpg")

    with patch("photo_organizer.renamer.get_date_taken", return_value=None), \
         patch("photo_organizer.renamer.read_metadata", return_value={}):
        result = _apply_pattern(photo, "{original}_{seq}", 1)

    assert result == "vacation_001.jpg"


# --- Test plan_renames() ---

def test_plan_renames_basic(tmp_path):
    """Should create rename plans for all photos."""
    _create_photo(tmp_path, "a.jpg")
    _create_photo(tmp_path, "b.jpg")

    with patch("photo_organizer.renamer.get_date_taken", return_value=None), \
         patch("photo_organizer.renamer.read_metadata", return_value={}):
        renames = plan_renames(tmp_path, "{seq}")

    assert len(renames) == 2


# --- Test execute_renames() ---

def test_execute_renames(tmp_path):
    """Should rename files on disk."""
    photo = _create_photo(tmp_path, "old_name.jpg")
    new_path = tmp_path / "new_name.jpg"

    renames = [(photo, new_path)]
    results = execute_renames(renames)

    assert results["success"] == 1
    assert new_path.exists()
    assert not photo.exists()


def test_execute_with_undo_log(tmp_path):
    """Should save an undo log when path is provided."""
    photo = _create_photo(tmp_path, "original.jpg")
    new_path = tmp_path / "renamed.jpg"
    undo_path = tmp_path / "undo.json"

    renames = [(photo, new_path)]
    execute_renames(renames, undo_log_path=undo_path)

    assert undo_path.exists()

    with open(undo_path) as f:
        log = json.load(f)

    assert len(log["renames"]) == 1
    assert "timestamp" in log


def test_execute_collision_protection(tmp_path):
    """Should not overwrite existing files."""
    photo = _create_photo(tmp_path, "source.jpg", b"source data")
    existing = _create_photo(tmp_path, "target.jpg", b"existing data")

    renames = [(photo, existing)]
    results = execute_renames(renames)

    assert results["failed"] == 1
    assert existing.read_bytes() == b"existing data"  # Not overwritten


# --- Test undo_renames() ---

def test_undo_renames(tmp_path):
    """Should reverse renames using the undo log."""
    # Simulate a rename that already happened
    renamed = _create_photo(tmp_path, "new_name.jpg")
    original_path = tmp_path / "original_name.jpg"

    # Create an undo log
    undo_log = tmp_path / "undo.json"
    log_data = {
        "timestamp": "2024-01-01T00:00:00",
        "renames": [{"new": str(renamed), "original": str(original_path)}],
    }
    with open(undo_log, "w") as f:
        json.dump(log_data, f)

    results = undo_renames(undo_log)

    assert results["success"] == 1
    assert original_path.exists()
    assert not renamed.exists()


# --- Test preview ---

def test_preview_renames():
    """Preview should show old -> new for each file."""
    renames = [
        (Path("/photos/IMG_001.jpg"), Path("/photos/2024-06-15_001.jpg")),
    ]
    output = preview_renames(renames)
    assert "IMG_001.jpg" in output
    assert "2024-06-15_001.jpg" in output


def test_preview_empty():
    """No renames should show a clear message."""
    assert "No files" in preview_renames([])
