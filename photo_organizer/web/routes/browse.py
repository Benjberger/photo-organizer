"""Directory/file browser endpoint."""

from pathlib import Path

from flask import Blueprint, jsonify, request

bp = Blueprint("browse", __name__)


@bp.route("/api/browse")
def browse():
    """List directory contents for the file/folder picker."""
    path_str = request.args.get("path", "")
    mode = request.args.get("mode", "both")  # "dir", "file", "both"

    if not path_str:
        path = Path.home()
    else:
        path = Path(path_str)

    if not path.exists() or not path.is_dir():
        return jsonify({"error": f"Not a valid directory: {path_str}"}), 400

    entries = []
    try:
        for entry in sorted(path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            # Skip hidden files/folders
            if entry.name.startswith("."):
                continue
            try:
                if entry.is_dir():
                    if mode in ("dir", "both"):
                        entries.append({
                            "name": entry.name,
                            "type": "dir",
                            "path": str(entry),
                        })
                else:
                    if mode in ("file", "both"):
                        entries.append({
                            "name": entry.name,
                            "type": "file",
                            "size": entry.stat().st_size,
                            "path": str(entry),
                        })
            except (PermissionError, OSError):
                continue
    except PermissionError:
        return jsonify({"error": f"Permission denied: {path}"}), 403

    parent = str(path.parent) if path.parent != path else None

    return jsonify({
        "current": str(path),
        "parent": parent,
        "entries": entries,
    })
