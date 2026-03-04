"""Organize (date-sort) endpoints."""

from pathlib import Path

from flask import Blueprint, jsonify, request

bp = Blueprint("organize", __name__)


@bp.route("/api/organize/plan", methods=["POST"])
def plan():
    """Preview how files would be organized into date folders."""
    data = request.get_json()
    source = data.get("source", "")
    destination = data.get("destination", "")

    if not source or not destination:
        return jsonify({"error": "Missing source or destination"}), 400

    source_path = Path(source)
    if not source_path.exists() or not source_path.is_dir():
        return jsonify({"error": f"Invalid source directory: {source}"}), 400

    from photo_organizer.organizer import plan_organization, preview_organization

    moves = plan_organization(source, destination)
    preview = preview_organization(moves)

    moves_json = [
        {"source": str(s), "source_name": s.name,
         "destination": str(d), "dest_name": d.name}
        for s, d in moves
    ]

    return jsonify({
        "moves": moves_json,
        "preview": preview,
        "count": len(moves),
    })


@bp.route("/api/organize/execute", methods=["POST"])
def execute():
    """Execute the organization (copy or move files)."""
    data = request.get_json()
    source = data.get("source", "")
    destination = data.get("destination", "")
    mode = data.get("mode", "copy")

    if not source or not destination:
        return jsonify({"error": "Missing source or destination"}), 400

    from photo_organizer.organizer import plan_organization, execute_organization

    moves = plan_organization(source, destination)
    results = execute_organization(moves, mode=mode)

    return jsonify(results)
