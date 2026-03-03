"""Tests for the grouping module.

The grouping module clusters photos by time proximity and resolves
location names from GPS data.
"""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from photo_organizer.grouping import (
    cluster_by_time,
    resolve_cluster_locations,
    build_location_map,
    format_clusters_report,
    _extract_place_name,
    reverse_geocode,
)


def _create_photo(directory, name, content=b"photo data"):
    """Helper: create a fake photo file."""
    filepath = directory / name
    filepath.write_bytes(content)
    return filepath


# --- Test cluster_by_time() ---

def test_single_cluster(tmp_path):
    """Photos taken close together should be in one cluster."""
    p1 = _create_photo(tmp_path, "a.jpg")
    p2 = _create_photo(tmp_path, "b.jpg")
    p3 = _create_photo(tmp_path, "c.jpg")

    # All within 1 hour of each other
    dates = {
        str(p1): datetime(2024, 6, 15, 10, 0),
        str(p2): datetime(2024, 6, 15, 10, 30),
        str(p3): datetime(2024, 6, 15, 11, 0),
    }

    def fake_date(fp):
        return dates.get(str(fp))

    with patch("photo_organizer.grouping.get_date_taken", side_effect=fake_date):
        clusters = cluster_by_time(tmp_path, gap_hours=3)

    assert len(clusters) == 1
    assert len(clusters[0]["photos"]) == 3


def test_two_clusters_by_gap(tmp_path):
    """Photos separated by a big gap should be in different clusters."""
    p1 = _create_photo(tmp_path, "morning.jpg")
    p2 = _create_photo(tmp_path, "evening.jpg")

    # 8 hours apart — should be two separate clusters with default 3h gap
    dates = {
        str(p1): datetime(2024, 6, 15, 8, 0),
        str(p2): datetime(2024, 6, 15, 16, 0),
    }

    def fake_date(fp):
        return dates.get(str(fp))

    with patch("photo_organizer.grouping.get_date_taken", side_effect=fake_date):
        clusters = cluster_by_time(tmp_path, gap_hours=3)

    assert len(clusters) == 2
    assert len(clusters[0]["photos"]) == 1
    assert len(clusters[1]["photos"]) == 1


def test_undated_photos_separate_cluster(tmp_path):
    """Photos without dates should go into their own cluster."""
    _create_photo(tmp_path, "dated.jpg")
    _create_photo(tmp_path, "undated.jpg")

    dates = {
        "dated": datetime(2024, 6, 15, 10, 0),
        "undated": None,
    }

    def fake_date(fp):
        name = Path(fp).stem
        return dates.get(name)

    with patch("photo_organizer.grouping.get_date_taken", side_effect=fake_date):
        clusters = cluster_by_time(tmp_path, gap_hours=3)

    assert len(clusters) == 2
    # One cluster has a date, one doesn't
    has_date = [c for c in clusters if c["start"] is not None]
    no_date = [c for c in clusters if c["start"] is None]
    assert len(has_date) == 1
    assert len(no_date) == 1


def test_cluster_date_range(tmp_path):
    """Cluster should track start and end dates."""
    p1 = _create_photo(tmp_path, "first.jpg")
    p2 = _create_photo(tmp_path, "last.jpg")

    start = datetime(2024, 6, 15, 10, 0)
    end = datetime(2024, 6, 15, 12, 0)

    dates = {str(p1): start, str(p2): end}

    def fake_date(fp):
        return dates.get(str(fp))

    with patch("photo_organizer.grouping.get_date_taken", side_effect=fake_date):
        clusters = cluster_by_time(tmp_path, gap_hours=3)

    assert clusters[0]["start"] == start
    assert clusters[0]["end"] == end


def test_custom_gap_hours(tmp_path):
    """Should respect custom gap threshold."""
    p1 = _create_photo(tmp_path, "a.jpg")
    p2 = _create_photo(tmp_path, "b.jpg")

    # 2 hours apart
    dates = {
        str(p1): datetime(2024, 6, 15, 10, 0),
        str(p2): datetime(2024, 6, 15, 12, 0),
    }

    def fake_date(fp):
        return dates.get(str(fp))

    # With 3h gap: one cluster
    with patch("photo_organizer.grouping.get_date_taken", side_effect=fake_date):
        clusters = cluster_by_time(tmp_path, gap_hours=3)
    assert len(clusters) == 1

    # With 1h gap: two clusters
    with patch("photo_organizer.grouping.get_date_taken", side_effect=fake_date):
        clusters = cluster_by_time(tmp_path, gap_hours=1)
    assert len(clusters) == 2


# --- Test resolve_cluster_locations() ---

def test_resolve_location_from_gps(tmp_path):
    """Should fill in location from GPS data in photos."""
    photo = _create_photo(tmp_path, "gps_photo.jpg")

    clusters = [{
        "photos": [photo],
        "start": datetime(2024, 6, 15, 10, 0),
        "end": datetime(2024, 6, 15, 10, 0),
        "location": None,
    }]

    fake_metadata = {"Latitude": 37.7749, "Longitude": -122.4194}

    with patch("photo_organizer.grouping.read_metadata", return_value=fake_metadata), \
         patch("photo_organizer.grouping.reverse_geocode", return_value="San_Francisco"):
        result = resolve_cluster_locations(clusters)

    assert result[0]["location"] == "San_Francisco"


def test_skip_already_named_clusters(tmp_path):
    """Should not overwrite existing location names."""
    photo = _create_photo(tmp_path, "photo.jpg")

    clusters = [{
        "photos": [photo],
        "start": datetime(2024, 6, 15, 10, 0),
        "end": datetime(2024, 6, 15, 10, 0),
        "location": "Already_Named",
    }]

    # Should not even call read_metadata
    with patch("photo_organizer.grouping.read_metadata") as mock:
        resolve_cluster_locations(clusters)
        mock.assert_not_called()

    assert clusters[0]["location"] == "Already_Named"


# --- Test _extract_place_name() ---

def test_extract_city():
    """Should prefer city over broader regions."""
    address = {
        "city": "San Francisco",
        "county": "San Francisco County",
        "state": "California",
        "country": "United States",
    }
    assert _extract_place_name(address) == "San_Francisco"


def test_extract_town_fallback():
    """Should fall back to town if no city."""
    address = {"town": "Half Moon Bay", "state": "California"}
    assert _extract_place_name(address) == "Half_Moon_Bay"


def test_extract_neighbourhood():
    """Should prefer neighbourhood (most specific)."""
    address = {
        "neighbourhood": "Nob Hill",
        "city": "San Francisco",
        "state": "California",
    }
    assert _extract_place_name(address) == "Nob_Hill"


# --- Test build_location_map() ---

def test_build_location_map(tmp_path):
    """Should map each photo path to its cluster's location."""
    p1 = _create_photo(tmp_path, "a.jpg")
    p2 = _create_photo(tmp_path, "b.jpg")

    clusters = [
        {"photos": [p1], "location": "Paris", "start": None, "end": None},
        {"photos": [p2], "location": "London", "start": None, "end": None},
    ]

    loc_map = build_location_map(clusters)
    assert loc_map[p1] == "Paris"
    assert loc_map[p2] == "London"


def test_build_location_map_unnamed(tmp_path):
    """Photos without location should map to 'unnamed'."""
    photo = _create_photo(tmp_path, "mystery.jpg")
    clusters = [{"photos": [photo], "location": None, "start": None, "end": None}]

    loc_map = build_location_map(clusters)
    assert loc_map[photo] == "unnamed"


# --- Test format ---

def test_format_clusters_report(tmp_path):
    """Report should show group count and locations."""
    p1 = _create_photo(tmp_path, "a.jpg")
    clusters = [{
        "photos": [p1],
        "start": datetime(2024, 6, 15, 10, 0),
        "end": datetime(2024, 6, 15, 10, 0),
        "location": "Paris",
    }]

    output = format_clusters_report(clusters)
    assert "1 photo" in output
    assert "1 group" in output
    assert "Paris" in output


def test_format_clusters_empty():
    """Should show clean message for no photos."""
    assert "No photos" in format_clusters_report([])
