"""Group, deduplicate, and organize photos into named folders.

Combines clustering, duplicate detection, and renaming into a single
workflow: scan photos, group by time, detect duplicates within groups,
prompt the user to name groups and confirm duplicate removal, then
move files into destination/GroupName/ folders with descriptive filenames.

Reuses existing modules:
- grouping: time clustering and location resolution
- duplicates: SHA-256 hashing for duplicate detection
- renamer: pattern-based filename generation
"""

import json
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from photo_organizer.duplicates import compute_hash
from photo_organizer.renamer import _apply_pattern, _clean_name


def find_group_duplicates(clusters):
    """Find duplicate photos within each cluster.

    Only checks for duplicates within the same cluster, not across
    clusters. Uses the same size-first-then-hash strategy as
    duplicates.find_duplicates() but scoped per cluster.

    Args:
        clusters: List of cluster dicts from cluster_by_time().

    Returns:
        A dict mapping cluster index → list of duplicate groups.
        Each duplicate group is a list of Paths (first = keep, rest = dupes).
        Clusters with no duplicates are omitted from the dict.
    """
    group_dupes = {}

    for idx, cluster in enumerate(clusters):
        # Phase 1: group by file size
        by_size = defaultdict(list)
        for photo in cluster["photos"]:
            try:
                size = photo.stat().st_size
                by_size[size].append(photo)
            except OSError:
                continue

        # Phase 2: hash files with matching sizes
        dupe_groups = []
        for size, files in by_size.items():
            if len(files) < 2:
                continue
            by_hash = defaultdict(list)
            for filepath in files:
                file_hash = compute_hash(filepath)
                by_hash[file_hash].append(filepath)
            for file_hash, group in by_hash.items():
                if len(group) >= 2:
                    dupe_groups.append(sorted(group))

        if dupe_groups:
            group_dupes[idx] = dupe_groups

    return group_dupes


def format_group_duplicates(clusters, group_dupes):
    """Format duplicate information for display.

    Args:
        clusters: List of cluster dicts.
        group_dupes: Dict from find_group_duplicates().

    Returns:
        Formatted string describing duplicates found.
    """
    if not group_dupes:
        return "No duplicates found within groups."

    lines = []
    for idx, dupe_groups in sorted(group_dupes.items()):
        total_dupes = sum(len(g) - 1 for g in dupe_groups)
        # Show file size for context
        try:
            size = dupe_groups[0][0].stat().st_size
            size_str = _human_size(size)
        except OSError:
            size_str = "unknown size"

        lines.append(
            f"  Group {idx + 1}: {total_dupes} duplicate(s) found "
            f"({size_str} each)"
        )
        for group in dupe_groups:
            lines.append(f"    [keep] {group[0].name}")
            for dupe in group[1:]:
                lines.append(f"    [dupe] {dupe.name}")

    return "\n".join(lines)


def prompt_duplicate_removal(clusters, group_dupes):
    """Interactively ask user to confirm removal of each duplicate.

    Args:
        clusters: List of cluster dicts.
        group_dupes: Dict from find_group_duplicates().

    Returns:
        A set of Paths to exclude from the move (confirmed duplicates).
    """
    exclude = set()

    for idx, dupe_groups in sorted(group_dupes.items()):
        for group in dupe_groups:
            for dupe in group[1:]:
                answer = input(
                    f"    Duplicates: {dupe.name} (remove? Y/n): "
                ).strip().lower()
                if answer in ("", "y", "yes"):
                    exclude.add(dupe)

    return exclude


def prompt_for_cluster_dates(clusters):
    """Prompt the user to provide dates for undated clusters.

    For each cluster where 'start' is None, asks the user to enter a date.
    Accepts YYYY-MM-DD (stored as datetime) or freeform text (stored as str).
    Shows the date range of dated clusters for context.

    Args:
        clusters: List of cluster dicts.

    Returns:
        The clusters list (modified in place with date_override keys).
    """
    undated = [(i, c) for i, c in enumerate(clusters) if c.get("start") is None]

    if not undated:
        return clusters

    # Show date context from dated clusters
    dated_starts = [
        c["start"] for c in clusters
        if c.get("start") is not None
    ]
    if dated_starts:
        earliest = min(dated_starts).strftime("%Y-%m-%d")
        latest = max(dated_starts).strftime("%Y-%m-%d")
        print(f"\n  Other groups span: {earliest} to {latest}")

    print(f"\n{len(undated)} undated group(s) found.")
    for i, cluster in undated:
        name = cluster.get("location") or "unnamed"
        count = len(cluster["photos"])
        answer = input(
            f"  Group {i + 1} ({name}, {count} photos) — "
            f"enter date (YYYY-MM-DD or freeform) or press Enter to keep 'undated': "
        ).strip()

        if answer:
            try:
                cluster["date_override"] = datetime.strptime(answer, "%Y-%m-%d")
            except ValueError:
                # Accept freeform text as-is
                cluster["date_override"] = answer

    return clusters


def plan_group_moves(clusters, destination, pattern="{location}_{date}_{seq}",
                     exclude=None):
    """Plan file moves into group-named destination folders.

    Each cluster's photos are moved into destination/GroupName/ and renamed
    using the pattern. Same-named groups are merged into one folder with
    continuous sequencing.

    Args:
        clusters: List of cluster dicts (with locations resolved/named).
        destination: Root destination directory.
        pattern: Naming pattern for files (default: {location}_{date}_{seq}).
        exclude: Set of Paths to skip (confirmed duplicates).

    Returns:
        A list of (source_path, dest_path) tuples.
    """
    destination = Path(destination)
    exclude = exclude or set()
    moves = []

    # Build per-cluster group names (no disambiguation — duplicates merge)
    group_names = _resolve_group_names(clusters)

    # Per-name sequence counter for continuous numbering across merged groups
    name_seq = {}

    for idx, cluster in enumerate(clusters):
        group_name = group_names[idx]
        group_dir = destination / group_name
        date_override = cluster.get("date_override")

        for photo in cluster["photos"]:
            if photo in exclude:
                continue

            name_seq[group_name] = name_seq.get(group_name, 0) + 1
            seq = name_seq[group_name]

            new_name = _apply_pattern(
                photo, pattern, seq, location=group_name,
                date_override=date_override,
            )
            dest_path = group_dir / new_name

            # Handle collisions
            dest_path = _resolve_collision(dest_path)

            moves.append((photo, dest_path))

    return moves


def preview_group_moves(moves):
    """Format planned moves grouped by destination folder.

    Args:
        moves: List of (source_path, dest_path) tuples.

    Returns:
        Formatted string showing the move plan.
    """
    if not moves:
        return "No files to move."

    lines = [f"Planned group organization ({len(moves)} file(s)):"]

    # Group by destination folder
    by_folder = {}
    for src, dst in moves:
        folder = str(dst.parent)
        if folder not in by_folder:
            by_folder[folder] = []
        by_folder[folder].append((src, dst))

    for folder in sorted(by_folder):
        folder_name = Path(folder).name
        lines.append(f"  {folder_name}/")
        for src, dst in by_folder[folder]:
            lines.append(f"    {src.name} -> {dst.name}")
    lines.append("")

    return "\n".join(lines)


def execute_group_moves(moves, undo_log_path=None):
    """Move files into group folders and optionally save an undo log.

    Args:
        moves: List of (source_path, dest_path) tuples.
        undo_log_path: Where to save the undo log JSON (optional).

    Returns:
        A dict with results: {"success": N, "failed": N, "errors": []}.
    """
    results = {"success": 0, "failed": 0, "errors": []}
    undo_entries = []

    for src, dst in moves:
        try:
            if dst.exists():
                raise FileExistsError(f"Target already exists: {dst}")

            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            results["success"] += 1

            undo_entries.append({
                "new": str(dst),
                "original": str(src),
            })

        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"{src.name}: {e}")

    if undo_log_path and undo_entries:
        undo_log_path = Path(undo_log_path)
        undo_log_path.parent.mkdir(parents=True, exist_ok=True)

        with open(undo_log_path, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "moves": undo_entries,
            }, f, indent=2)

    return results


def undo_group_moves(undo_log_path):
    """Reverse a group move operation using the undo log.

    Moves files back to their original locations and recreates
    source directories if needed.

    Args:
        undo_log_path: Path to the undo log JSON file.

    Returns:
        A dict with results: {"success": N, "failed": N, "errors": []}.
    """
    undo_log_path = Path(undo_log_path)

    with open(undo_log_path) as f:
        log = json.load(f)

    results = {"success": 0, "failed": 0, "errors": []}

    for entry in log["moves"]:
        new_path = Path(entry["new"])
        original_path = Path(entry["original"])

        try:
            if not new_path.exists():
                raise FileNotFoundError(f"File not found: {new_path}")

            # Recreate the original directory if it was removed
            original_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(new_path), str(original_path))
            results["success"] += 1

        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"{new_path.name}: {e}")

    return results


def _resolve_group_names(clusters):
    """Build group names for each cluster.

    Same-named clusters keep the same name so they merge into one folder.

    Args:
        clusters: List of cluster dicts.

    Returns:
        A list of group name strings, one per cluster.
    """
    result = []
    for cluster in clusters:
        name = cluster.get("location") or "unnamed"
        result.append(_clean_name(name))

    return result


def _resolve_collision(dest_path):
    """Add a numeric suffix if dest_path already exists."""
    if not dest_path.exists():
        return dest_path

    stem = dest_path.stem
    suffix = dest_path.suffix
    parent = dest_path.parent

    counter = 1
    while True:
        new_path = parent / f"{stem}_{counter}{suffix}"
        if not new_path.exists():
            return new_path
        counter += 1


def _human_size(size_bytes):
    """Convert bytes to human-readable size string."""
    if size_bytes >= 1_000_000_000:
        return f"{size_bytes / 1_000_000_000:.1f} GB"
    elif size_bytes >= 1_000_000:
        return f"{size_bytes / 1_000_000:.1f} MB"
    elif size_bytes >= 1_000:
        return f"{size_bytes / 1_000:.1f} KB"
    return f"{size_bytes} bytes"
