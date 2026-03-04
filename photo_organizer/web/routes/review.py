"""Review (contact sheet) endpoint."""

from pathlib import Path

from flask import Blueprint, jsonify, request

bp = Blueprint("review", __name__)


@bp.route("/api/review/generate", methods=["POST"])
def generate():
    """Cluster photos and return data for an in-browser contact sheet."""
    data = request.get_json()
    directory = data.get("directory", "")
    gap_hours = data.get("gap_hours", 3.0)

    if not directory:
        return jsonify({"error": "Missing directory"}), 400

    dir_path = Path(directory)
    if not dir_path.exists() or not dir_path.is_dir():
        return jsonify({"error": f"Invalid directory: {directory}"}), 400

    from photo_organizer.grouping import (
        cluster_by_time, resolve_cluster_locations, format_clusters_report,
    )

    clusters = cluster_by_time(directory, gap_hours=gap_hours)
    clusters = resolve_cluster_locations(clusters)
    report = format_clusters_report(clusters)

    clusters_json = []
    total_photos = 0
    for i, c in enumerate(clusters):
        start = c["start"].strftime("%Y-%m-%d %H:%M") if c.get("start") else None
        end = c["end"].strftime("%Y-%m-%d %H:%M") if c.get("end") else None
        photos = [
            {"path": str(p), "name": p.name}
            for p in c["photos"]
        ]
        total_photos += len(photos)
        clusters_json.append({
            "index": i,
            "location": c.get("location"),
            "photo_count": len(photos),
            "date_range": f"{start} to {end}" if start else "undated",
            "photos": photos,
        })

    return jsonify({
        "clusters": clusters_json,
        "total_photos": total_photos,
        "total_groups": len(clusters_json),
        "report": report,
    })
