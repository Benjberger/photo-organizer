"""Metadata endpoint."""

from pathlib import Path

from flask import Blueprint, jsonify, request

bp = Blueprint("metadata", __name__)


@bp.route("/api/metadata", methods=["POST"])
def get_metadata():
    """Read EXIF metadata for a single photo."""
    data = request.get_json()
    file_path = data.get("file", "")

    if not file_path:
        return jsonify({"error": "Missing file path"}), 400

    filepath = Path(file_path)
    if not filepath.exists() or not filepath.is_file():
        return jsonify({"error": f"File not found: {file_path}"}), 404

    from photo_organizer.metadata import read_metadata, format_metadata

    metadata = read_metadata(filepath)

    # Convert metadata values to JSON-serializable types
    clean = {}
    for key, value in metadata.items():
        clean[str(key)] = str(value)

    formatted = format_metadata(metadata)

    return jsonify({
        "metadata": clean,
        "formatted": formatted,
        "filepath": str(filepath),
    })
