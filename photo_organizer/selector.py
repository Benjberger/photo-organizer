"""Identify the best photos for printing.

Scores photos based on measurable quality indicators and lets you
tag favorites manually. Helps you narrow down a large collection
to the shots worth printing.

Scoring factors:
- Resolution: higher megapixel count = more detail for large prints
- File size: larger files (at the same resolution) usually mean more
  detail was captured (less compression, more tonal range)
- Sharpness: estimated using a Laplacian filter — sharp images have
  crisp edges, blurry ones don't

Concepts:
- Image analysis with Pillow (filters, statistics)
- Scoring / ranking algorithms
- JSON for persisting tags across sessions
"""

import json
from pathlib import Path

from PIL import Image, ImageFilter

from photo_organizer.metadata import JPEG_EXTENSIONS, RAW_EXTENSIONS
from photo_organizer.organizer import scan_photos


def score_photo(filepath):
    """Score a single photo on print-worthiness.

    Returns a dict with individual scores and an overall score (0-100).

    Args:
        filepath: Path to a photo file.

    Returns:
        A dict with scoring details:
        {
            "filepath": Path,
            "resolution_score": float,  # 0-100 based on megapixels
            "size_score": float,        # 0-100 based on file size
            "sharpness_score": float,   # 0-100 based on edge detection
            "overall_score": float,     # weighted average
            "megapixels": float,
            "sharpness": float,         # raw Laplacian variance
        }
    """
    filepath = Path(filepath)
    suffix = filepath.suffix.lower()

    result = {
        "filepath": filepath,
        "resolution_score": 0,
        "size_score": 0,
        "sharpness_score": 0,
        "overall_score": 0,
        "megapixels": 0,
        "sharpness": 0,
    }

    try:
        if suffix in JPEG_EXTENSIONS:
            img = Image.open(filepath)
        elif suffix in RAW_EXTENSIONS:
            # Extract embedded JPEG preview for analysis
            try:
                import rawpy
                with rawpy.imread(str(filepath)) as raw:
                    thumb = raw.extract_thumb()
                    if thumb.format == rawpy.ThumbFormat.JPEG:
                        from io import BytesIO
                        img = Image.open(BytesIO(thumb.data))
                    else:
                        img = Image.fromarray(thumb.data)
            except Exception:
                return result
        else:
            return result

        # --- Resolution score ---
        # Based on megapixels. 24MP+ gets full marks (enough for large prints).
        megapixels = (img.width * img.height) / 1_000_000
        result["megapixels"] = round(megapixels, 1)
        result["resolution_score"] = min(100, (megapixels / 24) * 100)

        # --- File size score ---
        # Larger files (relative to resolution) = more detail retained.
        # For JPEGs, 2MB+ per megapixel is excellent.
        file_size_mb = filepath.stat().st_size / 1_000_000
        bytes_per_mp = file_size_mb / max(megapixels, 0.1)
        result["size_score"] = min(100, (bytes_per_mp / 2) * 100)

        # --- Sharpness score ---
        # Laplacian filter detects edges. High variance = sharp image.
        sharpness = _estimate_sharpness(img)
        result["sharpness"] = round(sharpness, 1)
        # Normalize: variance of 500+ is very sharp for a typical photo
        result["sharpness_score"] = min(100, (sharpness / 500) * 100)

        # --- Overall score (weighted average) ---
        result["overall_score"] = round(
            result["resolution_score"] * 0.25 +
            result["size_score"] * 0.25 +
            result["sharpness_score"] * 0.50,  # Sharpness matters most for prints
            1,
        )

    except Exception:
        pass

    return result


def score_directory(directory):
    """Score all photos in a directory and return them ranked.

    Args:
        directory: Path to scan.

    Returns:
        A list of score dicts, sorted by overall_score (best first).
    """
    scores = []
    for filepath in scan_photos(directory):
        scores.append(score_photo(filepath))
    scores.sort(key=lambda s: s["overall_score"], reverse=True)
    return scores


def get_print_candidates(scores, min_score=60, top_n=None):
    """Filter scores to find the best photos for printing.

    Args:
        scores: List of score dicts from score_directory().
        min_score: Minimum overall score to be a candidate (0-100).
        top_n: If set, return at most this many candidates.

    Returns:
        A filtered list of score dicts.
    """
    candidates = [s for s in scores if s["overall_score"] >= min_score]
    if top_n is not None:
        candidates = candidates[:top_n]
    return candidates


def format_scores_report(scores, show_all=False):
    """Format scores as a readable report.

    Args:
        scores: List of score dicts.
        show_all: If True, show detailed breakdowns. Otherwise just summary.

    Returns:
        Formatted multi-line string.
    """
    if not scores:
        return "No photos found to score."

    lines = [f"{'Photo':<30} {'Score':>6} {'MP':>6} {'Sharp':>7} {'Res':>5} {'Size':>5} {'Shrp':>5}"]
    lines.append("-" * 80)

    for s in scores:
        name = s["filepath"].name
        if len(name) > 28:
            name = name[:25] + "..."

        lines.append(
            f"{name:<30} {s['overall_score']:>5.1f}  "
            f"{s['megapixels']:>5.1f} {s['sharpness']:>6.0f}  "
            f"{s['resolution_score']:>4.0f}  {s['size_score']:>4.0f}  "
            f"{s['sharpness_score']:>4.0f}"
        )

    return "\n".join(lines)


# --- Manual tagging ---

def load_tags(tags_file):
    """Load photo tags from a JSON file.

    Tags are stored as a simple JSON object: {"filepath": ["tag1", "tag2"]}.
    This lets you manually mark favorites, picks, rejects, etc.

    Args:
        tags_file: Path to the tags JSON file.

    Returns:
        A dict mapping filepath strings to lists of tag strings.
    """
    tags_file = Path(tags_file)
    if tags_file.exists():
        with open(tags_file) as f:
            return json.load(f)
    return {}


def save_tags(tags, tags_file):
    """Save photo tags to a JSON file.

    Args:
        tags: Dict mapping filepath strings to lists of tags.
        tags_file: Path to save to.
    """
    tags_file = Path(tags_file)
    tags_file.parent.mkdir(parents=True, exist_ok=True)
    with open(tags_file, "w") as f:
        json.dump(tags, f, indent=2)


def tag_photo(tags, filepath, tag):
    """Add a tag to a photo.

    Args:
        tags: The tags dict.
        filepath: Path to the photo.
        tag: Tag string to add (e.g., "favorite", "print", "reject").

    Returns:
        The updated tags dict.
    """
    key = str(filepath)
    if key not in tags:
        tags[key] = []
    if tag not in tags[key]:
        tags[key].append(tag)
    return tags


def untag_photo(tags, filepath, tag):
    """Remove a tag from a photo.

    Args:
        tags: The tags dict.
        filepath: Path to the photo.
        tag: Tag string to remove.

    Returns:
        The updated tags dict.
    """
    key = str(filepath)
    if key in tags and tag in tags[key]:
        tags[key].remove(tag)
        if not tags[key]:
            del tags[key]
    return tags


def get_tagged(tags, tag):
    """Get all photos with a specific tag.

    Args:
        tags: The tags dict.
        tag: Tag to filter by.

    Returns:
        A list of filepath strings that have this tag.
    """
    return [fp for fp, tag_list in tags.items() if tag in tag_list]


def export_selection(filepaths, output_file):
    """Export a list of selected photos to a text file.

    Args:
        filepaths: List of file path strings.
        output_file: Path to the output text file.
    """
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        for fp in filepaths:
            f.write(f"{fp}\n")


def _estimate_sharpness(img):
    """Estimate image sharpness using Laplacian variance.

    The Laplacian filter highlights edges in an image. A sharp photo
    has lots of well-defined edges (high variance), while a blurry
    photo has few (low variance).

    We resize to a standard size first so scores are comparable
    across different resolutions.

    Args:
        img: A PIL Image object.

    Returns:
        A float representing sharpness (higher = sharper).
    """
    # Resize to standard size for comparable scores
    img = img.copy()
    img.thumbnail((1024, 1024))

    # Convert to grayscale (edges are about brightness changes, not color)
    gray = img.convert("L")

    # Apply Laplacian-like edge detection filter
    # FIND_EDGES is Pillow's built-in edge detection kernel
    edges = gray.filter(ImageFilter.FIND_EDGES)

    # Calculate variance of the edge image
    # High variance = lots of strong edges = sharp image
    import numpy as np
    edge_array = np.array(edges, dtype=np.float64)
    return float(np.var(edge_array))
