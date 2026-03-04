"""Tests for the group_organizer module."""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from photo_organizer.group_organizer import (
    find_group_duplicates,
    format_group_duplicates,
    prompt_for_cluster_dates,
    plan_group_moves,
    preview_group_moves,
    execute_group_moves,
    undo_group_moves,
    _resolve_group_names,
    _resolve_collision,
)


def _create_photo(directory, name, content=b"photo data"):
    """Helper: create a fake photo file."""
    filepath = directory / name
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_bytes(content)
    return filepath


def _make_cluster(photos, location=None, start=None, end=None, date_override=None):
    """Helper: build a cluster dict."""
    cluster = {
        "photos": photos,
        "start": start,
        "end": end,
        "location": location,
    }
    if date_override is not None:
        cluster["date_override"] = date_override
    return cluster


# --- Test find_group_duplicates() ---

def test_find_group_duplicates_detects_dupes(tmp_path):
    """Should find duplicate files within the same cluster."""
    p1 = _create_photo(tmp_path, "a.jpg", b"identical content")
    p2 = _create_photo(tmp_path, "b.jpg", b"identical content")
    p3 = _create_photo(tmp_path, "c.jpg", b"different content")

    clusters = [_make_cluster([p1, p2, p3])]
    dupes = find_group_duplicates(clusters)

    assert 0 in dupes
    assert len(dupes[0]) == 1  # One duplicate group
    assert len(dupes[0][0]) == 2  # Two files in the group


def test_find_group_duplicates_no_dupes(tmp_path):
    """Should return empty dict when no duplicates exist."""
    p1 = _create_photo(tmp_path, "a.jpg", b"content 1")
    p2 = _create_photo(tmp_path, "b.jpg", b"content 2")

    clusters = [_make_cluster([p1, p2])]
    dupes = find_group_duplicates(clusters)

    assert dupes == {}


def test_find_group_duplicates_across_clusters(tmp_path):
    """Should NOT flag duplicates across different clusters."""
    p1 = _create_photo(tmp_path, "a.jpg", b"same content")
    p2 = _create_photo(tmp_path, "b.jpg", b"same content")

    # Same content but in different clusters
    clusters = [_make_cluster([p1]), _make_cluster([p2])]
    dupes = find_group_duplicates(clusters)

    assert dupes == {}


def test_find_group_duplicates_multiple_clusters(tmp_path):
    """Should detect dupes independently in each cluster."""
    p1 = _create_photo(tmp_path, "a.jpg", b"dup content")
    p2 = _create_photo(tmp_path, "b.jpg", b"dup content")
    p3 = _create_photo(tmp_path, "c.jpg", b"unique")

    p4 = _create_photo(tmp_path, "d.jpg", b"other dup")
    p5 = _create_photo(tmp_path, "e.jpg", b"other dup")

    clusters = [_make_cluster([p1, p2, p3]), _make_cluster([p4, p5])]
    dupes = find_group_duplicates(clusters)

    assert 0 in dupes
    assert 1 in dupes


# --- Test format_group_duplicates() ---

def test_format_group_duplicates_shows_info(tmp_path):
    """Should show group number, keep/dupe labels, and file names."""
    p1 = _create_photo(tmp_path, "a.jpg", b"identical")
    p2 = _create_photo(tmp_path, "b.jpg", b"identical")

    clusters = [_make_cluster([p1, p2])]
    group_dupes = {0: [[p1, p2]]}

    output = format_group_duplicates(clusters, group_dupes)
    assert "Group 1" in output
    assert "[keep]" in output
    assert "[dupe]" in output


def test_format_group_duplicates_empty():
    """Should show a clear message when no duplicates."""
    output = format_group_duplicates([], {})
    assert "No duplicates" in output


# --- Test _resolve_group_names() ---

def test_resolve_group_names_unique():
    """Unique names should pass through unchanged."""
    clusters = [
        _make_cluster([], location="Beach"),
        _make_cluster([], location="Mountain"),
    ]
    names = _resolve_group_names(clusters)
    assert names == ["Beach", "Mountain"]


def test_resolve_group_names_duplicates():
    """Duplicate names should stay the same (merged into one folder)."""
    clusters = [
        _make_cluster([], location="unnamed"),
        _make_cluster([], location="unnamed"),
        _make_cluster([], location="Beach"),
    ]
    names = _resolve_group_names(clusters)
    assert names == ["unnamed", "unnamed", "Beach"]


def test_resolve_group_names_none_location():
    """Clusters with no location should default to 'unnamed'."""
    clusters = [_make_cluster([], location=None)]
    names = _resolve_group_names(clusters)
    assert names == ["unnamed"]


def test_resolve_group_names_cleans_names():
    """Names with spaces and special chars should be cleaned."""
    clusters = [_make_cluster([], location="My Trip!")]
    names = _resolve_group_names(clusters)
    assert names == ["My_Trip"]


# --- Test plan_group_moves() ---

def test_plan_group_moves_basic(tmp_path):
    """Should create move plans with correct folder structure."""
    src = tmp_path / "src"
    src.mkdir()
    p1 = _create_photo(src, "a.jpg")
    dest = tmp_path / "dest"

    clusters = [_make_cluster([p1], location="Beach")]

    with patch("photo_organizer.group_organizer._apply_pattern",
               return_value="Beach_2024-01-01_001.jpg"):
        moves = plan_group_moves(clusters, dest)

    assert len(moves) == 1
    assert moves[0][0] == p1
    assert "Beach" in str(moves[0][1].parent)


def test_plan_group_moves_excludes_dupes(tmp_path):
    """Should skip files in the exclude set."""
    src = tmp_path / "src"
    src.mkdir()
    p1 = _create_photo(src, "a.jpg")
    p2 = _create_photo(src, "b.jpg")
    dest = tmp_path / "dest"

    clusters = [_make_cluster([p1, p2], location="Trip")]

    with patch("photo_organizer.group_organizer._apply_pattern",
               return_value="Trip_001.jpg"):
        moves = plan_group_moves(clusters, dest, exclude={p2})

    assert len(moves) == 1
    assert moves[0][0] == p1


def test_plan_group_moves_per_group_sequence(tmp_path):
    """Each group should have its own sequence counter."""
    src = tmp_path / "src"
    src.mkdir()
    p1 = _create_photo(src, "a.jpg")
    p2 = _create_photo(src, "b.jpg")
    p3 = _create_photo(src, "c.jpg")
    dest = tmp_path / "dest"

    clusters = [
        _make_cluster([p1, p2], location="Beach"),
        _make_cluster([p3], location="Mountain"),
    ]

    # Track what seq numbers _apply_pattern receives
    call_seqs = []
    original_apply = _resolve_collision  # just need something to reference

    def mock_apply(filepath, pattern, seq, location=None, date_override=None):
        call_seqs.append((location, seq))
        return f"{location}_{seq:03d}.jpg"

    with patch("photo_organizer.group_organizer._apply_pattern", side_effect=mock_apply):
        moves = plan_group_moves(clusters, dest)

    assert len(moves) == 3
    # Beach group: seq 1, 2
    assert ("Beach", 1) in call_seqs
    assert ("Beach", 2) in call_seqs
    # Mountain group: seq starts at 1 (different name)
    assert ("Mountain", 1) in call_seqs


def test_plan_group_moves_multiple_unnamed_merge(tmp_path):
    """Multiple unnamed clusters should merge into one folder with continuous sequence."""
    src = tmp_path / "src"
    src.mkdir()
    p1 = _create_photo(src, "a.jpg")
    p2 = _create_photo(src, "b.jpg")
    dest = tmp_path / "dest"

    clusters = [
        _make_cluster([p1], location=None),
        _make_cluster([p2], location=None),
    ]

    call_seqs = []

    def mock_apply(filepath, pattern, seq, location=None, date_override=None):
        call_seqs.append((location, seq))
        return f"{location}_{seq:03d}.jpg"

    with patch("photo_organizer.group_organizer._apply_pattern", side_effect=mock_apply):
        moves = plan_group_moves(clusters, dest)

    # Should merge into one folder
    folders = {m[1].parent.name for m in moves}
    assert folders == {"unnamed"}
    # Continuous sequencing: 1, 2
    assert ("unnamed", 1) in call_seqs
    assert ("unnamed", 2) in call_seqs


# --- Test preview_group_moves() ---

def test_preview_group_moves_format():
    """Should show folder/file structure."""
    moves = [
        (Path("/src/a.jpg"), Path("/dest/Beach/Beach_001.jpg")),
        (Path("/src/b.jpg"), Path("/dest/Beach/Beach_002.jpg")),
        (Path("/src/c.jpg"), Path("/dest/Mountain/Mountain_001.jpg")),
    ]
    output = preview_group_moves(moves)

    assert "3 file(s)" in output
    assert "Beach" in output
    assert "Mountain" in output
    assert "a.jpg -> Beach_001.jpg" in output


def test_preview_group_moves_empty():
    """Empty moves should show a clear message."""
    assert "No files" in preview_group_moves([])


# --- Test execute_group_moves() ---

def test_execute_group_moves_creates_dirs(tmp_path):
    """Should create destination directories and move files."""
    src = _create_photo(tmp_path, "photo.jpg")
    dest = tmp_path / "dest" / "Beach" / "Beach_001.jpg"

    moves = [(src, dest)]
    results = execute_group_moves(moves)

    assert results["success"] == 1
    assert results["failed"] == 0
    assert dest.exists()
    assert not src.exists()


def test_execute_group_moves_collision_protection(tmp_path):
    """Should not overwrite existing files."""
    src = _create_photo(tmp_path, "source.jpg", b"source")
    dest_dir = tmp_path / "dest" / "Beach"
    dest_dir.mkdir(parents=True)
    existing = _create_photo(dest_dir, "target.jpg", b"existing")

    moves = [(src, existing)]
    results = execute_group_moves(moves)

    assert results["failed"] == 1
    assert existing.read_bytes() == b"existing"


def test_execute_group_moves_undo_log(tmp_path):
    """Should save an undo log when path is provided."""
    src = _create_photo(tmp_path, "photo.jpg")
    dest = tmp_path / "dest" / "Beach" / "photo.jpg"
    undo_path = tmp_path / "dest" / ".group_undo_log.json"

    moves = [(src, dest)]
    execute_group_moves(moves, undo_log_path=undo_path)

    assert undo_path.exists()
    with open(undo_path) as f:
        log = json.load(f)
    assert len(log["moves"]) == 1
    assert "timestamp" in log


def test_execute_group_moves_multiple_files(tmp_path):
    """Should handle multiple files across multiple groups."""
    src1 = _create_photo(tmp_path, "a.jpg", b"content a")
    src2 = _create_photo(tmp_path, "b.jpg", b"content b")
    dest1 = tmp_path / "dest" / "Beach" / "Beach_001.jpg"
    dest2 = tmp_path / "dest" / "Mountain" / "Mountain_001.jpg"

    moves = [(src1, dest1), (src2, dest2)]
    results = execute_group_moves(moves)

    assert results["success"] == 2
    assert dest1.exists()
    assert dest2.exists()


# --- Test undo_group_moves() ---

def test_undo_group_moves(tmp_path):
    """Should restore files to original locations."""
    # Set up: file is already at the "moved" location
    dest_dir = tmp_path / "dest" / "Beach"
    dest_dir.mkdir(parents=True)
    moved = _create_photo(dest_dir, "Beach_001.jpg")

    original_dir = tmp_path / "src"
    original_path = original_dir / "photo.jpg"

    # Create undo log
    undo_path = tmp_path / "undo.json"
    log = {
        "timestamp": "2024-01-01T00:00:00",
        "moves": [{"new": str(moved), "original": str(original_path)}],
    }
    with open(undo_path, "w") as f:
        json.dump(log, f)

    results = undo_group_moves(undo_path)

    assert results["success"] == 1
    assert original_path.exists()
    assert not moved.exists()
    assert original_dir.exists()


def test_undo_group_moves_missing_file(tmp_path):
    """Should report error for missing files."""
    undo_path = tmp_path / "undo.json"
    log = {
        "timestamp": "2024-01-01T00:00:00",
        "moves": [{"new": str(tmp_path / "gone.jpg"),
                    "original": str(tmp_path / "original.jpg")}],
    }
    with open(undo_path, "w") as f:
        json.dump(log, f)

    results = undo_group_moves(undo_path)
    assert results["failed"] == 1


# --- Test _resolve_collision() ---

def test_resolve_collision_no_conflict(tmp_path):
    """Non-existing path should pass through."""
    path = tmp_path / "new_file.jpg"
    assert _resolve_collision(path) == path


def test_resolve_collision_with_conflict(tmp_path):
    """Existing path should get a numeric suffix."""
    existing = _create_photo(tmp_path, "photo.jpg")
    result = _resolve_collision(existing)

    assert result == tmp_path / "photo_1.jpg"


def test_resolve_collision_multiple_conflicts(tmp_path):
    """Should increment suffix until a free name is found."""
    _create_photo(tmp_path, "photo.jpg")
    _create_photo(tmp_path, "photo_1.jpg")
    _create_photo(tmp_path, "photo_2.jpg")

    result = _resolve_collision(tmp_path / "photo.jpg")
    assert result == tmp_path / "photo_3.jpg"


# --- Test prompt_for_cluster_dates() ---

def test_prompt_for_cluster_dates_sets_override():
    """Should set date_override on undated clusters when user provides a date."""
    clusters = [
        _make_cluster([], location="Trip", start=None),
        _make_cluster([], location="Beach", start=datetime(2024, 1, 1)),
    ]

    with patch("builtins.input", return_value="2023-02-15"):
        result = prompt_for_cluster_dates(clusters)

    assert result[0]["date_override"] == datetime(2023, 2, 15)
    assert "date_override" not in result[1]  # Dated cluster untouched


def test_prompt_for_cluster_dates_empty_keeps_undated():
    """Pressing Enter should leave no date_override."""
    clusters = [_make_cluster([], location="Old", start=None)]

    with patch("builtins.input", return_value=""):
        result = prompt_for_cluster_dates(clusters)

    assert "date_override" not in result[0]


def test_prompt_for_cluster_dates_freeform_text():
    """Non-YYYY-MM-DD input should be stored as a string override."""
    clusters = [_make_cluster([], location="Old", start=None)]

    with patch("builtins.input", return_value="03-2023"):
        result = prompt_for_cluster_dates(clusters)

    assert result[0]["date_override"] == "03-2023"
    assert isinstance(result[0]["date_override"], str)


def test_prompt_for_cluster_dates_freeform_text_descriptive():
    """Descriptive freeform text like 'March_2023' should be accepted."""
    clusters = [_make_cluster([], location="Old", start=None)]

    with patch("builtins.input", return_value="March_2023"):
        result = prompt_for_cluster_dates(clusters)

    assert result[0]["date_override"] == "March_2023"


def test_prompt_for_cluster_dates_shows_date_context(capsys):
    """Should print date range of dated clusters as context."""
    clusters = [
        _make_cluster([], location="Trip", start=None),
        _make_cluster([], location="Beach", start=datetime(2023, 1, 15)),
        _make_cluster([], location="Mountain", start=datetime(2023, 3, 20)),
    ]

    with patch("builtins.input", return_value=""):
        prompt_for_cluster_dates(clusters)

    output = capsys.readouterr().out
    assert "2023-01-15" in output
    assert "2023-03-20" in output
    assert "Other groups span:" in output


def test_prompt_for_cluster_dates_no_context_when_all_undated(capsys):
    """Should not show date context when there are no dated clusters."""
    clusters = [_make_cluster([], location="Old", start=None)]

    with patch("builtins.input", return_value=""):
        prompt_for_cluster_dates(clusters)

    output = capsys.readouterr().out
    assert "Other groups span:" not in output


def test_prompt_for_cluster_dates_no_undated():
    """Should return immediately if all clusters have dates."""
    clusters = [
        _make_cluster([], location="A", start=datetime(2024, 1, 1)),
    ]
    # No input() call should happen
    result = prompt_for_cluster_dates(clusters)
    assert result is clusters


# --- Test same-name group merging ---

def test_plan_group_moves_same_name_continuous_sequence(tmp_path):
    """Same-named groups should merge into one folder with continuous sequence."""
    src = tmp_path / "src"
    src.mkdir()
    p1 = _create_photo(src, "a.jpg")
    p2 = _create_photo(src, "b.jpg")
    p3 = _create_photo(src, "c.jpg")
    dest = tmp_path / "dest"

    clusters = [
        _make_cluster([p1, p2], location="Family"),
        _make_cluster([p3], location="Family"),
    ]

    call_seqs = []

    def mock_apply(filepath, pattern, seq, location=None, date_override=None):
        call_seqs.append((location, seq))
        return f"{location}_{seq:03d}.jpg"

    with patch("photo_organizer.group_organizer._apply_pattern", side_effect=mock_apply):
        moves = plan_group_moves(clusters, dest)

    assert len(moves) == 3
    # All in one folder
    folders = {m[1].parent.name for m in moves}
    assert folders == {"Family"}
    # Continuous: 1, 2, 3
    assert ("Family", 1) in call_seqs
    assert ("Family", 2) in call_seqs
    assert ("Family", 3) in call_seqs


def test_plan_group_moves_passes_date_override(tmp_path):
    """Should pass date_override from cluster to _apply_pattern."""
    src = tmp_path / "src"
    src.mkdir()
    p1 = _create_photo(src, "a.jpg")
    dest = tmp_path / "dest"

    override_dt = datetime(2023, 5, 10)
    clusters = [
        _make_cluster([p1], location="Old", start=None, date_override=override_dt),
    ]

    call_args = []

    def mock_apply(filepath, pattern, seq, location=None, date_override=None):
        call_args.append(date_override)
        return f"{location}_{seq:03d}.jpg"

    with patch("photo_organizer.group_organizer._apply_pattern", side_effect=mock_apply):
        plan_group_moves(clusters, dest)

    assert call_args == [override_dt]
