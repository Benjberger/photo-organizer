"""Tests for the selector module."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from photo_organizer.selector import (
    score_photo,
    get_print_candidates,
    format_scores_report,
    load_tags,
    save_tags,
    tag_photo,
    untag_photo,
    get_tagged,
    export_selection,
    _estimate_sharpness,
)


def _create_test_jpeg(directory, name, width=4000, height=3000):
    """Helper: create a real small JPEG for testing."""
    from PIL import Image
    filepath = directory / name
    img = Image.new("RGB", (width, height), color="red")
    img.save(filepath, "JPEG")
    return filepath


# --- Test score_photo() ---

def test_score_jpeg(tmp_path):
    """Should produce scores for a JPEG file."""
    photo = _create_test_jpeg(tmp_path, "test.jpg")
    result = score_photo(photo)

    assert result["filepath"] == photo
    assert result["megapixels"] > 0
    assert 0 <= result["overall_score"] <= 100
    assert 0 <= result["resolution_score"] <= 100
    assert 0 <= result["size_score"] <= 100
    assert 0 <= result["sharpness_score"] <= 100


def test_score_high_res_better(tmp_path):
    """Higher resolution photos should score higher on resolution."""
    small = _create_test_jpeg(tmp_path, "small.jpg", 800, 600)
    large = _create_test_jpeg(tmp_path, "large.jpg", 6000, 4000)

    small_score = score_photo(small)
    large_score = score_photo(large)

    assert large_score["resolution_score"] > small_score["resolution_score"]


def test_score_missing_file(tmp_path):
    """Should return zero scores for non-existent files."""
    result = score_photo(tmp_path / "missing.jpg")
    assert result["overall_score"] == 0


# --- Test get_print_candidates() ---

def test_candidates_filter_by_score():
    """Should filter out low-scoring photos."""
    scores = [
        {"filepath": Path("good.jpg"), "overall_score": 80},
        {"filepath": Path("ok.jpg"), "overall_score": 55},
        {"filepath": Path("bad.jpg"), "overall_score": 30},
    ]

    candidates = get_print_candidates(scores, min_score=60)
    assert len(candidates) == 1
    assert candidates[0]["filepath"].name == "good.jpg"


def test_candidates_top_n():
    """Should limit results to top N."""
    scores = [
        {"filepath": Path("a.jpg"), "overall_score": 90},
        {"filepath": Path("b.jpg"), "overall_score": 80},
        {"filepath": Path("c.jpg"), "overall_score": 70},
    ]

    candidates = get_print_candidates(scores, min_score=0, top_n=2)
    assert len(candidates) == 2


# --- Test format_scores_report() ---

def test_format_report():
    """Should produce readable output."""
    scores = [{
        "filepath": Path("photo.jpg"),
        "overall_score": 75.5,
        "megapixels": 24.0,
        "sharpness": 350.0,
        "resolution_score": 100,
        "size_score": 50,
        "sharpness_score": 70,
    }]
    output = format_scores_report(scores)
    assert "photo.jpg" in output
    assert "75.5" in output


def test_format_empty():
    """Should show a clear message for no photos."""
    assert "No photos" in format_scores_report([])


# --- Test tagging ---

def test_tag_and_untag():
    """Should add and remove tags."""
    tags = {}
    tags = tag_photo(tags, "photo.jpg", "favorite")
    assert "favorite" in tags["photo.jpg"]

    tags = untag_photo(tags, "photo.jpg", "favorite")
    assert "photo.jpg" not in tags


def test_tag_no_duplicates():
    """Adding the same tag twice should not create duplicates."""
    tags = {}
    tags = tag_photo(tags, "photo.jpg", "print")
    tags = tag_photo(tags, "photo.jpg", "print")
    assert tags["photo.jpg"].count("print") == 1


def test_get_tagged():
    """Should find all photos with a specific tag."""
    tags = {
        "a.jpg": ["print", "favorite"],
        "b.jpg": ["print"],
        "c.jpg": ["reject"],
    }
    result = get_tagged(tags, "print")
    assert set(result) == {"a.jpg", "b.jpg"}


def test_save_and_load_tags(tmp_path):
    """Tags should survive save/load cycle."""
    tags_file = tmp_path / "tags.json"
    tags = {"photo.jpg": ["favorite", "print"]}

    save_tags(tags, tags_file)
    loaded = load_tags(tags_file)

    assert loaded == tags


def test_load_missing_file(tmp_path):
    """Loading from non-existent file should return empty dict."""
    tags = load_tags(tmp_path / "nonexistent.json")
    assert tags == {}


# --- Test export ---

def test_export_selection(tmp_path):
    """Should write file paths to a text file."""
    output = tmp_path / "selected.txt"
    export_selection(["a.jpg", "b.jpg", "c.jpg"], output)

    content = output.read_text()
    assert "a.jpg" in content
    assert "b.jpg" in content
    assert content.count("\n") == 3


# --- Test sharpness estimation ---

def test_sharpness_detects_edges():
    """An image with edges should score higher than a blank one."""
    from PIL import Image, ImageDraw

    # Blank image (no edges)
    blank = Image.new("RGB", (200, 200), "gray")

    # Image with strong edges (grid pattern)
    edgy = Image.new("RGB", (200, 200), "white")
    draw = ImageDraw.Draw(edgy)
    for i in range(0, 200, 10):
        draw.line([(i, 0), (i, 200)], fill="black", width=2)
        draw.line([(0, i), (200, i)], fill="black", width=2)

    blank_sharpness = _estimate_sharpness(blank)
    edgy_sharpness = _estimate_sharpness(edgy)

    assert edgy_sharpness > blank_sharpness
