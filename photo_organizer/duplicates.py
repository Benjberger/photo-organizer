"""Detect and handle duplicate photos.

Duplicates are identified by file content (not name). Two photos with
different names but identical content are duplicates.

Strategy (optimized for speed):
1. Group files by size (instant — just reads file metadata)
2. Only files with matching sizes COULD be duplicates
3. Hash those files with SHA-256 to confirm (reads full file content)

This avoids hashing every single file, which would be very slow for
large photo collections.

Concepts:
- hashlib: Python's built-in library for computing hashes (SHA-256, MD5, etc.)
- defaultdict: a dictionary that auto-creates empty values for new keys
- sets: unordered collections of unique items (great for tracking "seen" values)
"""

import hashlib
import shutil
from collections import defaultdict
from pathlib import Path

from photo_organizer.organizer import scan_photos


def compute_hash(filepath, chunk_size=8192):
    """Compute the SHA-256 hash of a file.

    Instead of reading the entire file into memory at once (a 50MB RAW
    file would use 50MB of RAM!), we read it in small chunks. The hash
    is computed incrementally — same result, much less memory.

    Args:
        filepath: Path to the file.
        chunk_size: How many bytes to read at a time (default 8KB).

    Returns:
        The hex string of the SHA-256 hash.
    """
    sha256 = hashlib.sha256()

    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            sha256.update(chunk)

    return sha256.hexdigest()


def find_duplicates(directory):
    """Find duplicate photos in a directory.

    Uses the two-phase approach:
    1. Group by file size (fast filter)
    2. Hash files with matching sizes (confirm duplicates)

    Args:
        directory: Path to scan for duplicates.

    Returns:
        A list of duplicate groups. Each group is a list of Path objects
        that are all identical. The first item in each group is considered
        the "original" (the one we'd keep).

    Example return value:
        [
            [Path("a/photo1.jpg"), Path("b/photo1_copy.jpg")],
            [Path("c/sunset.cr2"), Path("d/sunset_backup.cr2")],
        ]
    """
    directory = Path(directory)

    # Phase 1: Group files by size
    # defaultdict(list) means: if a key doesn't exist, create an empty list
    by_size = defaultdict(list)
    file_count = 0

    for filepath in scan_photos(directory):
        size = filepath.stat().st_size
        by_size[size].append(filepath)
        file_count += 1

    # Phase 2: For groups with matching sizes, compute hashes
    duplicate_groups = []
    files_hashed = 0

    for size, files in by_size.items():
        if len(files) < 2:
            continue  # Only one file with this size — can't be a duplicate

        # Hash each file in this size group
        by_hash = defaultdict(list)
        for filepath in files:
            file_hash = compute_hash(filepath)
            by_hash[file_hash].append(filepath)
            files_hashed += 1

        # Groups with more than one file sharing a hash are duplicates
        for file_hash, group in by_hash.items():
            if len(group) >= 2:
                # Sort so the result is deterministic (same order every time)
                duplicate_groups.append(sorted(group))

    return duplicate_groups


def format_duplicates_report(duplicate_groups):
    """Format duplicate groups as a readable report.

    Args:
        duplicate_groups: Output from find_duplicates().

    Returns:
        A formatted string showing duplicate groups.
    """
    if not duplicate_groups:
        return "No duplicates found."

    total_dupes = sum(len(group) - 1 for group in duplicate_groups)
    total_wasted = 0

    lines = [f"Found {len(duplicate_groups)} group(s) of duplicates "
             f"({total_dupes} duplicate file(s)):\n"]

    for i, group in enumerate(duplicate_groups, 1):
        file_size = group[0].stat().st_size
        wasted = file_size * (len(group) - 1)
        total_wasted += wasted

        lines.append(f"  Group {i} ({_human_size(file_size)} each, "
                     f"{len(group)} copies):")
        lines.append(f"    [keep]   {group[0]}")
        for dupe in group[1:]:
            lines.append(f"    [dupe]   {dupe}")
        lines.append("")

    lines.append(f"Total wasted space: {_human_size(total_wasted)}")
    return "\n".join(lines)


def handle_duplicates(duplicate_groups, action="report", duplicates_dir=None):
    """Take action on found duplicates.

    Args:
        duplicate_groups: Output from find_duplicates().
        action: What to do with duplicates:
            - "report": Just return the report (no changes)
            - "move": Move duplicates to a separate folder
            - "delete": Delete duplicate files (keeps the first in each group)
        duplicates_dir: Where to move duplicates (required if action="move").

    Returns:
        A dict with results: {"processed": N, "errors": [...]}.
    """
    results = {"processed": 0, "errors": []}

    if action == "report":
        return results

    for group in duplicate_groups:
        # Keep the first file, act on the rest
        for dupe in group[1:]:
            try:
                if action == "move":
                    if duplicates_dir is None:
                        raise ValueError("duplicates_dir required for 'move' action")
                    dest = Path(duplicates_dir)
                    dest.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(dupe), str(dest / dupe.name))
                elif action == "delete":
                    dupe.unlink()
                else:
                    raise ValueError(f"Unknown action: {action}")

                results["processed"] += 1

            except Exception as e:
                results["errors"].append(f"{dupe}: {e}")

    return results


def _human_size(size_bytes):
    """Convert bytes to human-readable size string."""
    if size_bytes >= 1_000_000_000:
        return f"{size_bytes / 1_000_000_000:.1f} GB"
    elif size_bytes >= 1_000_000:
        return f"{size_bytes / 1_000_000:.1f} MB"
    elif size_bytes >= 1_000:
        return f"{size_bytes / 1_000:.1f} KB"
    return f"{size_bytes} bytes"
