"""Group photos into events and resolve location names.

This module answers: "Which photos belong together?" It uses two signals:

1. **Time clustering**: Photos taken close together in time are likely from
   the same event (trip, party, walk, etc.). A big gap in timestamps
   (default: 3 hours) marks the boundary between events.

2. **Location**: If any photo in a cluster has GPS coordinates, we
   reverse-geocode those to get a human-readable place name (city, etc.)
   using OpenStreetMap's free Nominatim service.

When a group has no GPS data, the user can be prompted to name it.

Concepts:
- Clustering: grouping similar items together based on a distance metric
- Reverse geocoding: converting GPS coordinates → place names
- Caching: storing results to avoid redundant work (API calls are slow)
"""

from datetime import timedelta
from pathlib import Path

from photo_organizer.metadata import read_metadata, get_date_taken
from photo_organizer.organizer import scan_photos


# How big a time gap (in hours) before we consider it a new event
DEFAULT_GAP_HOURS = 3

# Cache for reverse geocoding results (coordinates → place name)
# Rounded to ~1km precision so nearby photos share the same lookup
_geocode_cache = {}


def cluster_by_time(directory, gap_hours=DEFAULT_GAP_HOURS):
    """Group photos by time proximity.

    Algorithm:
    1. Collect all photos with their dates
    2. Sort by date taken
    3. Walk through in order — if the gap between consecutive photos
       exceeds the threshold, start a new cluster
    4. Photos without dates go into a separate "undated" cluster

    Args:
        directory: Path to scan for photos.
        gap_hours: Hours of silence before starting a new cluster.

    Returns:
        A list of clusters. Each cluster is a dict:
        {
            "photos": [Path, ...],       # photo files in this cluster
            "start": datetime or None,   # earliest photo date
            "end": datetime or None,     # latest photo date
            "location": str or None,     # resolved location name
        }
    """
    directory = Path(directory)
    gap = timedelta(hours=gap_hours)

    # Collect photos with dates
    dated = []
    undated = []

    for filepath in scan_photos(directory):
        date = get_date_taken(filepath)
        if date:
            dated.append((date, filepath))
        else:
            undated.append(filepath)

    # Sort by date
    dated.sort(key=lambda x: x[0])

    # Cluster by time gaps
    clusters = []
    current_cluster = None

    for date, filepath in dated:
        if current_cluster is None:
            # First photo — start a new cluster
            current_cluster = {
                "photos": [filepath],
                "start": date,
                "end": date,
                "location": None,
            }
        elif date - current_cluster["end"] > gap:
            # Big gap — save current cluster, start new one
            clusters.append(current_cluster)
            current_cluster = {
                "photos": [filepath],
                "start": date,
                "end": date,
                "location": None,
            }
        else:
            # Same cluster — add photo and update end time
            current_cluster["photos"].append(filepath)
            current_cluster["end"] = date

    # Don't forget the last cluster
    if current_cluster:
        clusters.append(current_cluster)

    # Undated photos get their own cluster
    if undated:
        clusters.append({
            "photos": undated,
            "start": None,
            "end": None,
            "location": None,
        })

    return clusters


def resolve_cluster_locations(clusters):
    """Try to find a location name for each cluster from GPS data.

    For each cluster, we check if any photo has GPS coordinates.
    If so, we reverse-geocode the first one found and use that as
    the cluster's location.

    Args:
        clusters: List of cluster dicts from cluster_by_time().

    Returns:
        The same list with "location" fields filled in where possible.
    """
    for cluster in clusters:
        if cluster["location"]:
            continue  # Already has a location

        # Check each photo for GPS data
        for filepath in cluster["photos"]:
            metadata = read_metadata(filepath)
            lat = metadata.get("Latitude")
            lon = metadata.get("Longitude")

            if lat is not None and lon is not None:
                location = reverse_geocode(lat, lon)
                if location:
                    cluster["location"] = location
                    break  # One location is enough for the whole cluster

    return clusters


def reverse_geocode(latitude, longitude):
    """Convert GPS coordinates to a place name.

    Uses OpenStreetMap's Nominatim service (free, no API key needed).
    Results are cached so the same area isn't looked up twice.

    Args:
        latitude: GPS latitude (e.g., 37.7749)
        longitude: GPS longitude (e.g., -122.4194)

    Returns:
        A short place name like "San_Francisco" or None if lookup fails.
    """
    # Round to ~1km precision for caching
    # 0.01 degrees ≈ 1.1 km
    cache_key = (round(latitude, 2), round(longitude, 2))

    if cache_key in _geocode_cache:
        return _geocode_cache[cache_key]

    try:
        from geopy.geocoders import Nominatim

        geolocator = Nominatim(user_agent="photo_organizer")
        location = geolocator.reverse(
            f"{latitude}, {longitude}",
            language="en",
            exactly_one=True,
        )

        if location and location.raw.get("address"):
            name = _extract_place_name(location.raw["address"])
        else:
            name = None

    except Exception:
        name = None

    _geocode_cache[cache_key] = name
    return name


def _extract_place_name(address):
    """Pick the most useful place name from a geocoding result.

    Nominatim returns many levels of detail (house number, street,
    city, state, country). We want something like "San_Francisco"
    or "Central_Park" — specific but not too long.

    Args:
        address: The 'address' dict from Nominatim's response.

    Returns:
        A cleaned place name string.
    """
    import re

    # Try these fields in order of specificity
    name_fields = [
        "neighbourhood",
        "suburb",
        "city",
        "town",
        "village",
        "county",
        "state",
    ]

    for field in name_fields:
        if field in address:
            name = address[field]
            # Clean for use in filenames
            name = name.replace(" ", "_").replace("/", "_")
            name = re.sub(r'[^\w\-.]', '', name)
            return name

    return None


def prompt_for_cluster_names(clusters):
    """Interactively ask the user to name clusters without locations.

    For each unnamed cluster, shows the date range and number of photos,
    then asks the user to type a name.

    Args:
        clusters: List of cluster dicts.

    Returns:
        The same list with user-provided names filled in.
    """
    unnamed = [c for c in clusters if not c["location"]]

    if not unnamed:
        return clusters

    print(f"\n{len(unnamed)} group(s) have no location data.")
    print("Please name them (or press Enter to use 'unnamed'):\n")

    for i, cluster in enumerate(unnamed, 1):
        n = len(cluster["photos"])

        if cluster["start"]:
            date_range = cluster["start"].strftime("%Y-%m-%d %H:%M")
            if cluster["end"] and cluster["end"].date() != cluster["start"].date():
                date_range += f" to {cluster['end'].strftime('%Y-%m-%d %H:%M')}"
            elif cluster["end"]:
                date_range += f" to {cluster['end'].strftime('%H:%M')}"
        else:
            date_range = "undated"

        # Show a few example filenames
        examples = [p.name for p in cluster["photos"][:3]]
        example_str = ", ".join(examples)
        if n > 3:
            example_str += f", ... (+{n - 3} more)"

        print(f"  Group {i}: {n} photo(s), {date_range}")
        print(f"    Files: {example_str}")

        name = input(f"    Name for this group: ").strip()
        if not name:
            name = "unnamed"

        # Clean for filename use
        import re
        name = name.replace(" ", "_").replace("/", "_")
        name = re.sub(r'[^\w\-.]', '', name)
        cluster["location"] = name

    return clusters


def build_location_map(clusters):
    """Build a mapping from photo path → location/group name.

    This is the output that the renamer uses. Given a photo path,
    it returns the location name for that photo's cluster.

    Args:
        clusters: List of cluster dicts (with locations resolved).

    Returns:
        A dict mapping Path → location name string.
    """
    location_map = {}
    for cluster in clusters:
        name = cluster["location"] or "unnamed"
        for photo in cluster["photos"]:
            location_map[photo] = name
    return location_map


def format_clusters_report(clusters):
    """Format clusters as a readable report.

    Args:
        clusters: List of cluster dicts.

    Returns:
        Formatted multi-line string.
    """
    if not clusters:
        return "No photos found."

    total = sum(len(c["photos"]) for c in clusters)
    lines = [f"Found {total} photo(s) in {len(clusters)} group(s):\n"]

    for i, cluster in enumerate(clusters, 1):
        n = len(cluster["photos"])
        location = cluster["location"] or "(no location)"

        if cluster["start"]:
            date_str = cluster["start"].strftime("%Y-%m-%d")
            if cluster["end"] and cluster["end"].date() != cluster["start"].date():
                date_str += f" to {cluster['end'].strftime('%Y-%m-%d')}"
        else:
            date_str = "undated"

        lines.append(f"  Group {i}: {location} — {n} photo(s), {date_str}")

    return "\n".join(lines)
