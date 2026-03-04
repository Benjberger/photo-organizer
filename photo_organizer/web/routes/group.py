"""Group wizard endpoints.

Multi-step workflow: cluster → name → dates → duplicates → preview → execute.
Wizard state is stored server-side in memory, keyed by wizard_id.
"""

import uuid
from pathlib import Path

from flask import Blueprint, jsonify, request

bp = Blueprint("group", __name__)

# Server-side wizard state: {wizard_id: {clusters, group_dupes, exclude, config, moves}}
_wizards = {}


def _cluster_to_json(i, c):
    """Convert a cluster dict to a JSON-safe dict."""
    start = c["start"].strftime("%Y-%m-%d %H:%M") if c.get("start") else None
    end = c["end"].strftime("%Y-%m-%d %H:%M") if c.get("end") else None
    return {
        "index": i,
        "photo_count": len(c["photos"]),
        "date_range": f"{start} to {end}" if start else "undated",
        "location": c.get("location"),
        "needs_name": not c.get("location"),
        "has_date": c.get("start") is not None,
        "has_date_override": "date_override" in c,
        "sample_files": [p.name for p in c["photos"][:4]],
        "thumbnail_paths": [str(p) for p in c["photos"][:4]],
    }


@bp.route("/api/group/start", methods=["POST"])
def start():
    """Step 1: Cluster photos and detect duplicates."""
    data = request.get_json()
    source = data.get("source", "")
    destination = data.get("destination", "")
    pattern = data.get("pattern", "{location}_{date}_{seq}")
    gap_hours = data.get("gap_hours", 3.0)

    if not source or not destination:
        return jsonify({"error": "Missing source or destination"}), 400

    source_path = Path(source)
    if not source_path.exists() or not source_path.is_dir():
        return jsonify({"error": f"Invalid source directory: {source}"}), 400

    from photo_organizer.grouping import cluster_by_time, resolve_cluster_locations
    from photo_organizer.group_organizer import find_group_duplicates

    clusters = cluster_by_time(source, gap_hours=gap_hours)
    clusters = resolve_cluster_locations(clusters)
    group_dupes = find_group_duplicates(clusters)

    wizard_id = str(uuid.uuid4())[:8]
    _wizards[wizard_id] = {
        "clusters": clusters,
        "group_dupes": group_dupes,
        "exclude": set(),
        "config": {
            "source": source,
            "destination": destination,
            "pattern": pattern,
        },
        "moves": None,
    }

    # Format duplicates for JSON
    dupes_json = {}
    for idx, dupe_groups in group_dupes.items():
        dupes_json[str(idx)] = []
        for group in dupe_groups:
            dupes_json[str(idx)].append({
                "keep": {"path": str(group[0]), "name": group[0].name},
                "dupes": [{"path": str(d), "name": d.name} for d in group[1:]],
            })

    total_photos = sum(len(c["photos"]) for c in clusters)

    return jsonify({
        "wizard_id": wizard_id,
        "clusters": [_cluster_to_json(i, c) for i, c in enumerate(clusters)],
        "duplicates": dupes_json,
        "total_photos": total_photos,
    })


@bp.route("/api/group/name", methods=["POST"])
def name_groups():
    """Step 2: Apply user-provided names to unnamed clusters."""
    data = request.get_json()
    wizard_id = data.get("wizard_id")
    names = data.get("names", {})

    wizard = _wizards.get(wizard_id)
    if not wizard:
        return jsonify({"error": "Invalid wizard_id"}), 400

    clusters = wizard["clusters"]
    for idx_str, name in names.items():
        idx = int(idx_str)
        if 0 <= idx < len(clusters) and name:
            clusters[idx]["location"] = name

    return jsonify({
        "clusters": [_cluster_to_json(i, c) for i, c in enumerate(clusters)],
    })


@bp.route("/api/group/dates", methods=["POST"])
def set_dates():
    """Step 3: Set date overrides for undated clusters."""
    data = request.get_json()
    wizard_id = data.get("wizard_id")
    dates = data.get("dates", {})

    wizard = _wizards.get(wizard_id)
    if not wizard:
        return jsonify({"error": "Invalid wizard_id"}), 400

    from datetime import datetime

    clusters = wizard["clusters"]
    for idx_str, date_str in dates.items():
        idx = int(idx_str)
        if 0 <= idx < len(clusters) and date_str:
            try:
                clusters[idx]["date_override"] = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                # Freeform text
                clusters[idx]["date_override"] = date_str

    return jsonify({
        "clusters": [_cluster_to_json(i, c) for i, c in enumerate(clusters)],
    })


@bp.route("/api/group/duplicates", methods=["POST"])
def confirm_duplicates():
    """Step 4: Confirm which duplicates to exclude."""
    data = request.get_json()
    wizard_id = data.get("wizard_id")
    exclude_paths = data.get("exclude", [])

    wizard = _wizards.get(wizard_id)
    if not wizard:
        return jsonify({"error": "Invalid wizard_id"}), 400

    wizard["exclude"] = {Path(p) for p in exclude_paths}

    return jsonify({"excluded_count": len(wizard["exclude"])})


@bp.route("/api/group/preview", methods=["POST"])
def preview():
    """Step 5: Generate and show the move plan."""
    data = request.get_json()
    wizard_id = data.get("wizard_id")

    wizard = _wizards.get(wizard_id)
    if not wizard:
        return jsonify({"error": "Invalid wizard_id"}), 400

    from photo_organizer.group_organizer import plan_group_moves, preview_group_moves

    config = wizard["config"]
    moves = plan_group_moves(
        wizard["clusters"],
        config["destination"],
        pattern=config["pattern"],
        exclude=wizard["exclude"],
    )
    wizard["moves"] = moves

    preview_text = preview_group_moves(moves)

    moves_json = [
        {
            "source": str(s),
            "source_name": s.name,
            "destination": str(d),
            "dest_name": d.name,
            "group": d.parent.name,
        }
        for s, d in moves
    ]

    return jsonify({
        "moves": moves_json,
        "preview": preview_text,
        "count": len(moves),
        "excluded_count": len(wizard["exclude"]),
    })


@bp.route("/api/group/execute", methods=["POST"])
def execute():
    """Step 6: Execute the moves."""
    data = request.get_json()
    wizard_id = data.get("wizard_id")

    wizard = _wizards.get(wizard_id)
    if not wizard:
        return jsonify({"error": "Invalid wizard_id"}), 400

    if not wizard.get("moves"):
        return jsonify({"error": "No moves planned. Run preview first."}), 400

    from photo_organizer.group_organizer import execute_group_moves

    config = wizard["config"]
    undo_log = str(Path(config["destination"]) / ".group_undo_log.json")

    results = execute_group_moves(wizard["moves"], undo_log_path=undo_log)
    results["undo_log"] = undo_log
    results["excluded_count"] = len(wizard["exclude"])

    # Clean up wizard state
    del _wizards[wizard_id]

    return jsonify(results)


@bp.route("/api/group/undo", methods=["POST"])
def undo():
    """Undo a group move operation."""
    data = request.get_json()
    undo_log = data.get("undo_log", "")

    if not undo_log:
        return jsonify({"error": "Missing undo_log path"}), 400

    undo_path = Path(undo_log)
    if not undo_path.exists():
        return jsonify({"error": f"Undo log not found: {undo_log}"}), 404

    from photo_organizer.group_organizer import undo_group_moves

    results = undo_group_moves(undo_log)
    return jsonify(results)


@bp.route("/api/group/cancel", methods=["POST"])
def cancel():
    """Cancel a wizard session and clean up state."""
    data = request.get_json()
    wizard_id = data.get("wizard_id")

    if wizard_id and wizard_id in _wizards:
        del _wizards[wizard_id]

    return jsonify({"cancelled": True})
