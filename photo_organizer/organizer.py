"""Organize photos into date-based folder structures.

Scans a source directory for photo files, reads the date each was taken
from EXIF metadata, and copies or moves them into organized folders like:

    destination/
    ├── 2024/
    │   ├── 2024-01-15/
    │   │   ├── IMG_001.jpg
    │   │   └── IMG_002.cr2
    │   └── 2024-03-22/
    │       └── IMG_003.jpg
    └── undated/
        └── IMG_004.jpg    (no EXIF date found)

Concepts in this module:
- pathlib.Path: Python's modern way to work with file paths
- shutil: standard library for copying/moving files
- Generator functions (scan_photos uses 'yield')
"""

import shutil
from pathlib import Path

from photo_organizer.metadata import is_supported, get_date_taken


def scan_photos(directory):
    """Find all supported photo files in a directory (and subdirectories).

    This is a 'generator' function — notice the 'yield' keyword instead of
    'return'. Instead of building a huge list of all files in memory, it
    produces one file at a time. This matters when scanning directories
    with thousands of photos.

    Args:
        directory: Path to the directory to scan.

    Yields:
        Path objects for each supported photo file found.
    """
    directory = Path(directory)

    if not directory.is_dir():
        raise ValueError(f"Not a directory: {directory}")

    # rglob = "recursive glob" — searches this folder AND all subfolders
    # The '*' pattern matches every file
    for filepath in sorted(directory.rglob("*")):
        if filepath.is_file() and is_supported(filepath):
            yield filepath


def plan_organization(source, destination):
    """Plan where each photo should go, without moving anything.

    This is the 'dry-run' core. It produces a list of planned moves
    that can be reviewed before executing.

    Args:
        source: Directory containing photos to organize.
        destination: Root directory for the organized output.

    Returns:
        A list of (source_path, destination_path) tuples.
    """
    source = Path(source)
    destination = Path(destination)
    moves = []

    for filepath in scan_photos(source):
        date = get_date_taken(filepath)

        if date:
            # Organize by YYYY/YYYY-MM-DD/
            year_folder = str(date.year)
            date_folder = date.strftime("%Y-%m-%d")
            dest_dir = destination / year_folder / date_folder
        else:
            # No date found — put in 'undated' folder
            dest_dir = destination / "undated"

        dest_path = dest_dir / filepath.name

        # Handle filename collisions (two photos with the same name)
        dest_path = _resolve_collision(dest_path)

        moves.append((filepath, dest_path))

    return moves


def preview_organization(moves):
    """Format planned moves as a readable preview string.

    Args:
        moves: List of (source, destination) tuples from plan_organization().

    Returns:
        A formatted string showing what would happen.
    """
    if not moves:
        return "No photos found to organize."

    lines = [f"Found {len(moves)} photo(s) to organize:\n"]

    # Group by destination folder for cleaner output
    by_folder = {}
    for src, dst in moves:
        folder = str(dst.parent)
        if folder not in by_folder:
            by_folder[folder] = []
        by_folder[folder].append((src, dst))

    for folder in sorted(by_folder):
        lines.append(f"  {folder}/")
        for src, dst in by_folder[folder]:
            lines.append(f"    {src.name} <- {src}")
        lines.append("")

    return "\n".join(lines)


def execute_organization(moves, mode="copy"):
    """Actually copy or move the photos.

    Args:
        moves: List of (source, destination) tuples.
        mode: "copy" (default, safe — keeps originals) or "move".

    Returns:
        A dict with counts: {"success": N, "failed": N, "errors": [...]}.
    """
    results = {"success": 0, "failed": 0, "errors": []}

    for src, dst in moves:
        try:
            # Create destination folders if they don't exist
            # parents=True means create intermediate folders too
            # exist_ok=True means don't error if folder already exists
            dst.parent.mkdir(parents=True, exist_ok=True)

            if mode == "copy":
                shutil.copy2(src, dst)  # copy2 preserves metadata (dates, etc.)
            elif mode == "move":
                shutil.move(str(src), str(dst))
            else:
                raise ValueError(f"Unknown mode: {mode}. Use 'copy' or 'move'.")

            results["success"] += 1

        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"{src}: {e}")

    return results


def _resolve_collision(dest_path):
    """If a file already exists at dest_path, add a number suffix.

    Example: if 'IMG_001.jpg' exists, try 'IMG_001_1.jpg', then
    'IMG_001_2.jpg', etc.

    Args:
        dest_path: The intended destination path.

    Returns:
        A path that doesn't conflict with existing files.
    """
    if not dest_path.exists():
        return dest_path

    stem = dest_path.stem      # filename without extension (e.g., "IMG_001")
    suffix = dest_path.suffix  # extension (e.g., ".jpg")
    parent = dest_path.parent

    counter = 1
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        new_path = parent / new_name
        if not new_path.exists():
            return new_path
        counter += 1
