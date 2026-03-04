"""Thumbnail serving endpoint."""

import base64
from pathlib import Path

from flask import Blueprint, Response, request, jsonify

bp = Blueprint("thumbnails", __name__)

# 1x1 transparent PNG placeholder
_PLACEHOLDER = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4"
    "nGNgYPgPAAEDAQAIicLsAAAABJRU5ErkJggg=="
)


@bp.route("/api/thumbnail")
def thumbnail():
    """Serve a photo thumbnail as JPEG."""
    path_str = request.args.get("path", "")
    if not path_str:
        return jsonify({"error": "Missing path parameter"}), 400

    filepath = Path(path_str)
    if not filepath.exists() or not filepath.is_file():
        return Response(_PLACEHOLDER, mimetype="image/png")

    try:
        from photo_organizer.contact_sheet import _make_thumbnail
        b64 = _make_thumbnail(filepath)
        if b64:
            data = base64.b64decode(b64)
            return Response(data, mimetype="image/jpeg",
                            headers={"Cache-Control": "max-age=3600"})
    except Exception:
        pass

    return Response(_PLACEHOLDER, mimetype="image/png")
