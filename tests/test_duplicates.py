"""Tests for the duplicates module."""

from pathlib import Path

from photo_organizer.duplicates import (
    compute_hash,
    find_duplicates,
    format_duplicates_report,
    handle_duplicates,
    _human_size,
)


def _create_photo(directory, name, content=b"photo data"):
    """Helper: create a fake photo file with specific content."""
    filepath = directory / name
    filepath.write_bytes(content)
    return filepath


# --- Test compute_hash() ---

def test_same_content_same_hash(tmp_path):
    """Identical files should produce the same hash."""
    file1 = _create_photo(tmp_path, "a.jpg", b"identical content")
    file2 = _create_photo(tmp_path, "b.jpg", b"identical content")

    assert compute_hash(file1) == compute_hash(file2)


def test_different_content_different_hash(tmp_path):
    """Different files should produce different hashes."""
    file1 = _create_photo(tmp_path, "a.jpg", b"content A")
    file2 = _create_photo(tmp_path, "b.jpg", b"content B")

    assert compute_hash(file1) != compute_hash(file2)


# --- Test find_duplicates() ---

def test_find_exact_duplicates(tmp_path):
    """Should find files with identical content."""
    _create_photo(tmp_path, "original.jpg", b"photo bytes here")
    _create_photo(tmp_path, "copy.jpg", b"photo bytes here")
    _create_photo(tmp_path, "unique.jpg", b"different photo")

    groups = find_duplicates(tmp_path)

    assert len(groups) == 1  # One group of duplicates
    assert len(groups[0]) == 2  # Two files in that group


def test_no_duplicates(tmp_path):
    """Should return empty list when no duplicates exist."""
    _create_photo(tmp_path, "a.jpg", b"unique content A")
    _create_photo(tmp_path, "b.jpg", b"unique content B")

    groups = find_duplicates(tmp_path)
    assert groups == []


def test_multiple_duplicate_groups(tmp_path):
    """Should handle multiple independent groups of duplicates."""
    # Group 1: two identical files
    _create_photo(tmp_path, "a1.jpg", b"group A content!!")
    _create_photo(tmp_path, "a2.jpg", b"group A content!!")

    # Group 2: three identical files (different content from group 1)
    _create_photo(tmp_path, "b1.jpg", b"group B different!")
    _create_photo(tmp_path, "b2.jpg", b"group B different!")
    _create_photo(tmp_path, "b3.jpg", b"group B different!")

    groups = find_duplicates(tmp_path)

    assert len(groups) == 2
    sizes = sorted(len(g) for g in groups)
    assert sizes == [2, 3]


def test_size_optimization(tmp_path):
    """Files with different sizes should not be hashed/compared."""
    # These have different sizes, so they can't be duplicates
    _create_photo(tmp_path, "small.jpg", b"short")
    _create_photo(tmp_path, "large.jpg", b"much longer content here")

    groups = find_duplicates(tmp_path)
    assert groups == []


# --- Test handle_duplicates() ---

def test_handle_delete(tmp_path):
    """Delete action should remove duplicate files, keeping originals."""
    orig = _create_photo(tmp_path, "original.jpg", b"same data")
    dupe = _create_photo(tmp_path, "duplicate.jpg", b"same data")

    groups = [[orig, dupe]]  # First item is "original" (kept)
    results = handle_duplicates(groups, action="delete")

    assert results["processed"] == 1
    assert orig.exists()      # Original kept
    assert not dupe.exists()  # Duplicate removed


def test_handle_move(tmp_path):
    """Move action should move duplicates to a separate folder."""
    orig = _create_photo(tmp_path, "original.jpg", b"same data")
    dupe = _create_photo(tmp_path, "duplicate.jpg", b"same data")
    dupes_dir = tmp_path / "duplicates_folder"

    groups = [[orig, dupe]]
    results = handle_duplicates(groups, action="move", duplicates_dir=dupes_dir)

    assert results["processed"] == 1
    assert orig.exists()
    assert not dupe.exists()  # Moved from original location
    assert (dupes_dir / "duplicate.jpg").exists()  # Now in duplicates folder


def test_handle_report_changes_nothing(tmp_path):
    """Report action should not modify any files."""
    orig = _create_photo(tmp_path, "original.jpg", b"same data")
    dupe = _create_photo(tmp_path, "duplicate.jpg", b"same data")

    groups = [[orig, dupe]]
    handle_duplicates(groups, action="report")

    assert orig.exists()
    assert dupe.exists()  # Still there — report doesn't delete


# --- Test format and helpers ---

def test_format_report_no_dupes():
    """Should show a clean message when no duplicates."""
    assert "No duplicates" in format_duplicates_report([])


def test_format_report_with_dupes(tmp_path):
    """Should show group details and wasted space."""
    f1 = _create_photo(tmp_path, "a.jpg", b"x" * 1000)
    f2 = _create_photo(tmp_path, "b.jpg", b"x" * 1000)

    output = format_duplicates_report([[f1, f2]])
    assert "1 group" in output
    assert "keep" in output
    assert "dupe" in output


def test_human_size():
    """Size formatting should be human-readable."""
    assert "bytes" in _human_size(500)
    assert "KB" in _human_size(5_000)
    assert "MB" in _human_size(5_000_000)
    assert "GB" in _human_size(5_000_000_000)
