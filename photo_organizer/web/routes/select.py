"""Select (print scoring) endpoints."""

from pathlib import Path

from flask import Blueprint, jsonify, request

bp = Blueprint("select", __name__)


@bp.route("/api/select/score", methods=["POST"])
def score():
    """Score photos in a directory for print quality."""
    data = request.get_json()
    directory = data.get("directory", "")
    min_score = data.get("min_score", 0)
    top = data.get("top")

    if not directory:
        return jsonify({"error": "Missing directory"}), 400

    dir_path = Path(directory)
    if not dir_path.exists() or not dir_path.is_dir():
        return jsonify({"error": f"Invalid directory: {directory}"}), 400

    from photo_organizer.selector import (
        score_directory, get_print_candidates, format_scores_report,
    )

    scores = score_directory(directory)
    candidates = get_print_candidates(scores, min_score=min_score, top_n=top)
    report = format_scores_report(candidates)

    scores_json = []
    for s in candidates:
        scores_json.append({
            "filepath": str(s["filepath"]),
            "name": s["filepath"].name,
            "overall_score": round(s["overall_score"], 1),
            "resolution_score": round(s["resolution_score"], 1),
            "size_score": round(s["size_score"], 1),
            "sharpness_score": round(s["sharpness_score"], 1),
            "megapixels": round(s.get("megapixels", 0), 1),
        })

    return jsonify({
        "scores": scores_json,
        "total_scored": len(scores),
        "candidates_count": len(candidates),
        "report": report,
    })


@bp.route("/api/select/tag", methods=["POST"])
def tag():
    """Tag photos with a label."""
    data = request.get_json()
    files = data.get("files", [])
    tag_name = data.get("tag", "print")
    tags_file = data.get("tags_file", "photo_tags.json")

    if not files:
        return jsonify({"error": "No files provided"}), 400

    from photo_organizer.selector import load_tags, tag_photo, save_tags

    tags = load_tags(tags_file)
    for filepath in files:
        tags = tag_photo(tags, filepath, tag_name)
    save_tags(tags, tags_file)

    return jsonify({"tagged": len(files)})


@bp.route("/api/select/export", methods=["POST"])
def export():
    """Export a selection to a text file."""
    data = request.get_json()
    files = data.get("files", [])
    output_file = data.get("output_file", "selection.txt")

    if not files:
        return jsonify({"error": "No files provided"}), 400

    from photo_organizer.selector import export_selection

    export_selection(files, output_file)

    return jsonify({"exported": len(files), "output_file": output_file})
