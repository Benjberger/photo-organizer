"""Duplicates detection endpoints."""

from pathlib import Path

from flask import Blueprint, jsonify, request

bp = Blueprint("duplicates", __name__)


@bp.route("/api/duplicates/scan", methods=["POST"])
def scan():
    """Scan a directory for duplicate photos."""
    data = request.get_json()
    directory = data.get("directory", "")

    if not directory:
        return jsonify({"error": "Missing directory"}), 400

    dir_path = Path(directory)
    if not dir_path.exists() or not dir_path.is_dir():
        return jsonify({"error": f"Invalid directory: {directory}"}), 400

    from photo_organizer.duplicates import find_duplicates, format_duplicates_report

    groups = find_duplicates(directory)
    report = format_duplicates_report(groups)

    groups_json = []
    for group in groups:
        files = []
        for filepath in group:
            try:
                size = filepath.stat().st_size
            except OSError:
                size = 0
            files.append({
                "path": str(filepath),
                "name": filepath.name,
                "size": size,
            })
        groups_json.append({"files": files})

    total_dupes = sum(len(g["files"]) - 1 for g in groups_json)

    return jsonify({
        "groups": groups_json,
        "report": report,
        "total_groups": len(groups_json),
        "total_duplicates": total_dupes,
    })


@bp.route("/api/duplicates/handle", methods=["POST"])
def handle():
    """Handle duplicates (report, move, or delete)."""
    data = request.get_json()
    directory = data.get("directory", "")
    action = data.get("action", "report")

    if not directory:
        return jsonify({"error": "Missing directory"}), 400

    from photo_organizer.duplicates import find_duplicates, handle_duplicates

    groups = find_duplicates(directory)

    if not groups:
        return jsonify({"processed": 0, "errors": []})

    duplicates_dir = data.get("duplicates_dir")
    results = handle_duplicates(groups, action, duplicates_dir)

    return jsonify(results)
