"""Rename endpoints."""

from pathlib import Path

from flask import Blueprint, jsonify, request

bp = Blueprint("rename", __name__)


@bp.route("/api/rename/plan", methods=["POST"])
def plan():
    """Preview planned renames."""
    data = request.get_json()
    directory = data.get("directory", "")
    pattern = data.get("pattern", "{date}_{seq}")

    if not directory:
        return jsonify({"error": "Missing directory"}), 400

    dir_path = Path(directory)
    if not dir_path.exists() or not dir_path.is_dir():
        return jsonify({"error": f"Invalid directory: {directory}"}), 400

    from photo_organizer.renamer import plan_renames, preview_renames

    location_map = None
    clusters_json = None
    needs_location_names = False

    if "{location}" in pattern:
        gap_hours = data.get("gap_hours", 3.0)
        location_names = data.get("location_names")

        from photo_organizer.grouping import (
            cluster_by_time, resolve_cluster_locations, build_location_map,
        )

        clusters = cluster_by_time(directory, gap_hours=gap_hours)
        clusters = resolve_cluster_locations(clusters)

        # Apply user-provided names
        if location_names:
            for idx_str, name in location_names.items():
                idx = int(idx_str)
                if 0 <= idx < len(clusters) and name:
                    clusters[idx]["location"] = name

        # Check if any still need names
        unnamed = [
            i for i, c in enumerate(clusters)
            if not c.get("location")
        ]

        if unnamed and not location_names:
            needs_location_names = True
            clusters_json = []
            for i, c in enumerate(clusters):
                start = c["start"].strftime("%Y-%m-%d %H:%M") if c.get("start") else "undated"
                end = c["end"].strftime("%Y-%m-%d %H:%M") if c.get("end") else "undated"
                clusters_json.append({
                    "index": i,
                    "photo_count": len(c["photos"]),
                    "date_range": f"{start} to {end}" if c.get("start") else "undated",
                    "location": c.get("location"),
                    "needs_name": not c.get("location"),
                    "sample_files": [p.name for p in c["photos"][:3]],
                    "thumbnail_paths": [str(p) for p in c["photos"][:1]],
                })
            return jsonify({
                "needs_location_names": True,
                "clusters": clusters_json,
                "renames": [],
                "preview": "",
                "count": 0,
            })

        location_map = build_location_map(clusters)

    renames = plan_renames(directory, pattern, location_map=location_map)
    preview = preview_renames(renames)

    renames_json = [
        {"old_path": str(old), "old_name": old.name, "new_name": new.name}
        for old, new in renames
    ]

    return jsonify({
        "renames": renames_json,
        "preview": preview,
        "count": len(renames),
        "needs_location_names": False,
        "clusters": clusters_json,
    })


@bp.route("/api/rename/execute", methods=["POST"])
def execute():
    """Execute the rename operation."""
    data = request.get_json()
    directory = data.get("directory", "")
    pattern = data.get("pattern", "{date}_{seq}")

    if not directory:
        return jsonify({"error": "Missing directory"}), 400

    from photo_organizer.renamer import plan_renames, execute_renames

    location_map = None
    if "{location}" in pattern:
        gap_hours = data.get("gap_hours", 3.0)
        location_names = data.get("location_names")

        from photo_organizer.grouping import (
            cluster_by_time, resolve_cluster_locations, build_location_map,
        )

        clusters = cluster_by_time(directory, gap_hours=gap_hours)
        clusters = resolve_cluster_locations(clusters)

        if location_names:
            for idx_str, name in location_names.items():
                idx = int(idx_str)
                if 0 <= idx < len(clusters) and name:
                    clusters[idx]["location"] = name

        location_map = build_location_map(clusters)

    renames = plan_renames(directory, pattern, location_map=location_map)

    undo_log = data.get("undo_log")
    if not undo_log:
        undo_log = str(Path(directory) / ".rename_undo_log.json")

    results = execute_renames(renames, undo_log_path=undo_log)
    results["undo_log"] = undo_log

    return jsonify(results)


@bp.route("/api/rename/undo", methods=["POST"])
def undo():
    """Undo a rename operation."""
    data = request.get_json()
    undo_log = data.get("undo_log", "")

    if not undo_log:
        return jsonify({"error": "Missing undo_log path"}), 400

    undo_path = Path(undo_log)
    if not undo_path.exists():
        return jsonify({"error": f"Undo log not found: {undo_log}"}), 404

    from photo_organizer.renamer import undo_renames

    results = undo_renames(undo_log)
    return jsonify(results)
