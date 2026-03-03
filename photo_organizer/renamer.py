"""Batch rename photos using customizable patterns.

Rename photos based on their EXIF metadata using patterns like:
    {date}_{camera}_{seq}.jpg  ->  2024-06-15_Canon_001.jpg

Features:
- Pattern-based renaming with metadata placeholders
- Preview changes before applying (dry-run)
- Undo log: saves a JSON file mapping new names -> old names
  so you can reverse any rename operation

Concepts:
- String formatting with str.format() / f-strings
- JSON: a standard text format for storing structured data
- Regular expressions (regex): pattern matching for text
"""

import json
import re
from datetime import datetime
from pathlib import Path

from photo_organizer.metadata import read_metadata, get_date_taken
from photo_organizer.organizer import scan_photos


# Available placeholders and what they mean
PLACEHOLDERS = {
    "{date}": "Date taken (YYYY-MM-DD)",
    "{datetime}": "Date and time (YYYY-MM-DD_HHMMSS)",
    "{year}": "Year (YYYY)",
    "{month}": "Month (MM)",
    "{day}": "Day (DD)",
    "{camera}": "Camera make (e.g., Canon)",
    "{model}": "Camera model (e.g., EOS R5)",
    "{seq}": "Sequence number (001, 002, ...)",
    "{original}": "Original filename (without extension)",
    "{location}": "Location name from GPS or user-provided group name",
}


def plan_renames(directory, pattern, start_seq=1, location_map=None):
    """Plan how files would be renamed without changing anything.

    Args:
        directory: Directory containing photos.
        pattern: Naming pattern with placeholders like {date}_{camera}_{seq}
        start_seq: Starting number for {seq} placeholder.
        location_map: Optional dict mapping Path → location name string.
                      Built by grouping.build_location_map(). If the pattern
                      uses {location} and no map is provided, "unknown" is used.

    Returns:
        A list of (old_path, new_path) tuples.
    """
    directory = Path(directory)
    renames = []
    seq = start_seq

    for filepath in scan_photos(directory):
        location = None
        if location_map:
            location = location_map.get(filepath)
        new_name = _apply_pattern(filepath, pattern, seq, location=location)
        new_path = filepath.parent / new_name

        # Avoid renaming to the same name
        if new_path != filepath:
            renames.append((filepath, new_path))

        seq += 1

    return renames


def preview_renames(renames):
    """Format planned renames as a readable preview.

    Args:
        renames: List of (old_path, new_path) tuples.

    Returns:
        A formatted string showing before -> after for each file.
    """
    if not renames:
        return "No files to rename."

    lines = [f"Planned renames ({len(renames)} file(s)):\n"]

    for old, new in renames:
        lines.append(f"  {old.name}")
        lines.append(f"    -> {new.name}")
        lines.append("")

    return "\n".join(lines)


def execute_renames(renames, undo_log_path=None):
    """Perform the renames and optionally save an undo log.

    The undo log is a JSON file that maps each new filename back to its
    original name. If something goes wrong, you can use undo_renames()
    to reverse everything.

    Args:
        renames: List of (old_path, new_path) tuples.
        undo_log_path: Where to save the undo log (optional but recommended).

    Returns:
        A dict with results: {"success": N, "failed": N, "errors": [...]}.
    """
    results = {"success": 0, "failed": 0, "errors": []}
    undo_entries = []

    for old_path, new_path in renames:
        try:
            # Check for collision
            if new_path.exists():
                raise FileExistsError(f"Target already exists: {new_path}")

            old_path.rename(new_path)
            results["success"] += 1

            # Record for undo log
            undo_entries.append({
                "new": str(new_path),
                "original": str(old_path),
            })

        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"{old_path.name}: {e}")

    # Save undo log if requested
    if undo_log_path and undo_entries:
        undo_log_path = Path(undo_log_path)
        undo_log_path.parent.mkdir(parents=True, exist_ok=True)

        with open(undo_log_path, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "renames": undo_entries,
            }, f, indent=2)

    return results


def undo_renames(undo_log_path):
    """Reverse a batch rename using a saved undo log.

    Args:
        undo_log_path: Path to the undo log JSON file.

    Returns:
        A dict with results: {"success": N, "failed": N, "errors": [...]}.
    """
    undo_log_path = Path(undo_log_path)

    with open(undo_log_path) as f:
        log = json.load(f)

    results = {"success": 0, "failed": 0, "errors": []}

    for entry in log["renames"]:
        new_path = Path(entry["new"])
        original_path = Path(entry["original"])

        try:
            if not new_path.exists():
                raise FileNotFoundError(f"File not found: {new_path}")

            new_path.rename(original_path)
            results["success"] += 1

        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"{new_path.name}: {e}")

    return results


def _apply_pattern(filepath, pattern, seq, location=None):
    """Fill in a naming pattern with actual metadata values.

    Args:
        filepath: Path to the photo file.
        pattern: Pattern string with {placeholders}.
        seq: Current sequence number.
        location: Optional location/group name for {location} placeholder.

    Returns:
        The new filename (with original extension preserved).
    """
    filepath = Path(filepath)
    metadata = read_metadata(filepath)
    date = get_date_taken(filepath)

    # Build the replacement values
    values = {
        "original": filepath.stem,
        "seq": f"{seq:03d}",  # Zero-padded to 3 digits: 001, 002, etc.
        "location": _clean_name(location) if location else "unknown",
    }

    # Date-related values
    if date:
        values["date"] = date.strftime("%Y-%m-%d")
        values["datetime"] = date.strftime("%Y-%m-%d_%H%M%S")
        values["year"] = date.strftime("%Y")
        values["month"] = date.strftime("%m")
        values["day"] = date.strftime("%d")
    else:
        values["date"] = "undated"
        values["datetime"] = "undated"
        values["year"] = "unknown"
        values["month"] = "unknown"
        values["day"] = "unknown"

    # Camera info
    make = metadata.get("Make", "")
    if hasattr(make, "strip"):
        make = make.strip()
    values["camera"] = _clean_name(str(make)) if make else "unknown"

    model = metadata.get("Model", "")
    if hasattr(model, "strip"):
        model = model.strip()
    values["model"] = _clean_name(str(model)) if model else "unknown"

    # Apply the pattern
    try:
        new_stem = pattern.format(**values)
    except KeyError as e:
        # Unknown placeholder — use the pattern literally
        new_stem = pattern

    # Keep the original file extension
    return new_stem + filepath.suffix.lower()


def _clean_name(name):
    """Clean a string for use in a filename.

    Removes characters that aren't safe in filenames and replaces
    spaces with underscores.
    """
    # Replace spaces and slashes with underscores
    name = name.replace(" ", "_").replace("/", "_").replace("\\", "_")
    # Remove any remaining unsafe characters
    name = re.sub(r'[^\w\-.]', '', name)
    return name
