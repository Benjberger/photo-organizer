"""Generate an HTML contact sheet for reviewing photo groups.

Creates a simple HTML page with thumbnail previews of photos, organized
by cluster/group. Open it in your browser to visually review each group
before deciding what to name them.

Concepts:
- HTML generation: building a web page from Python
- Thumbnails: small preview versions of images (fast to load)
- Base64 encoding: embedding image data directly in HTML (no separate files)
- Pillow's thumbnail(): resizes images while keeping proportions
"""

import base64
import webbrowser
from io import BytesIO
from pathlib import Path

from PIL import Image

from photo_organizer.metadata import JPEG_EXTENSIONS, RAW_EXTENSIONS


# Max thumbnail size (pixels). Keeps the HTML page lightweight.
THUMB_SIZE = (300, 300)


def generate_contact_sheet(clusters, output_path=None, open_browser=True):
    """Generate an HTML contact sheet showing photos grouped by cluster.

    Args:
        clusters: List of cluster dicts from grouping.cluster_by_time().
        output_path: Where to save the HTML file. Defaults to
                     'contact_sheet.html' in the current directory.
        open_browser: If True, automatically open the page in your browser.

    Returns:
        Path to the generated HTML file.
    """
    if output_path is None:
        output_path = Path("contact_sheet.html")
    else:
        output_path = Path(output_path)

    html = _build_html(clusters)

    output_path.write_text(html, encoding="utf-8")

    if open_browser:
        webbrowser.open(output_path.resolve().as_uri())

    return output_path


def _build_html(clusters):
    """Build the HTML string for the contact sheet."""
    groups_html = []

    for i, cluster in enumerate(clusters, 1):
        n = len(cluster["photos"])
        location = cluster["location"] or "(unnamed)"

        if cluster["start"]:
            date_str = cluster["start"].strftime("%Y-%m-%d %H:%M")
            if cluster["end"] and cluster["end"].date() != cluster["start"].date():
                date_str += f" to {cluster['end'].strftime('%Y-%m-%d %H:%M')}"
            elif cluster["end"]:
                date_str += f" to {cluster['end'].strftime('%H:%M')}"
        else:
            date_str = "undated"

        # Generate thumbnails for each photo in this group
        thumbs_html = []
        for photo in cluster["photos"]:
            thumb = _make_thumbnail(photo)
            if thumb:
                thumbs_html.append(
                    f'<div class="thumb">'
                    f'<img src="data:image/jpeg;base64,{thumb}" alt="{photo.name}">'
                    f'<span class="name">{photo.name}</span>'
                    f'</div>'
                )
            else:
                # RAW files or files we can't thumbnail
                thumbs_html.append(
                    f'<div class="thumb no-preview">'
                    f'<div class="placeholder">RAW</div>'
                    f'<span class="name">{photo.name}</span>'
                    f'</div>'
                )

        groups_html.append(f"""
        <div class="group">
            <h2>Group {i}: {location}</h2>
            <p class="meta">{n} photo(s) &mdash; {date_str}</p>
            <div class="grid">
                {''.join(thumbs_html)}
            </div>
        </div>
        """)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Photo Organizer - Contact Sheet</title>
<style>
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background: #1a1a1a;
        color: #e0e0e0;
        margin: 0;
        padding: 20px;
    }}
    h1 {{
        text-align: center;
        color: #fff;
        margin-bottom: 30px;
    }}
    .group {{
        background: #2a2a2a;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 30px;
    }}
    .group h2 {{
        margin: 0 0 5px 0;
        color: #7eb8ff;
    }}
    .meta {{
        color: #999;
        margin: 0 0 15px 0;
    }}
    .grid {{
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
    }}
    .thumb {{
        text-align: center;
    }}
    .thumb img {{
        max-width: 250px;
        max-height: 200px;
        border-radius: 4px;
        display: block;
        margin-bottom: 4px;
    }}
    .thumb .name {{
        font-size: 11px;
        color: #888;
    }}
    .no-preview .placeholder {{
        width: 150px;
        height: 120px;
        background: #3a3a3a;
        border-radius: 4px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #666;
        font-size: 18px;
        margin-bottom: 4px;
    }}
</style>
</head>
<body>
    <h1>Photo Organizer - Contact Sheet</h1>
    <p style="text-align:center;color:#999;">
        Review each group below, then run the rename command to name them.
    </p>
    {''.join(groups_html)}
</body>
</html>"""


def _make_thumbnail(filepath):
    """Create a base64-encoded JPEG thumbnail of a photo.

    Args:
        filepath: Path to the image file.

    Returns:
        Base64 string of the thumbnail JPEG, or None if we can't
        create a thumbnail (e.g., RAW files without Pillow support).
    """
    filepath = Path(filepath)
    suffix = filepath.suffix.lower()

    try:
        if suffix in JPEG_EXTENSIONS:
            img = Image.open(filepath)
        elif suffix in RAW_EXTENSIONS:
            # Try to extract the embedded JPEG preview from RAW files
            try:
                import rawpy
                with rawpy.imread(str(filepath)) as raw:
                    thumb = raw.extract_thumb()
                    if thumb.format == rawpy.ThumbFormat.JPEG:
                        img = Image.open(BytesIO(thumb.data))
                    else:
                        # Bitmap thumbnail — convert from array
                        img = Image.fromarray(thumb.data)
            except Exception:
                return None
        else:
            return None

        # Handle EXIF orientation so thumbnails aren't rotated
        from PIL import ImageOps
        img = ImageOps.exif_transpose(img)

        # Create thumbnail (modifies in place, preserves aspect ratio)
        img.thumbnail(THUMB_SIZE)

        # Convert to JPEG bytes, then base64
        buffer = BytesIO()
        img.convert("RGB").save(buffer, format="JPEG", quality=75)
        return base64.b64encode(buffer.getvalue()).decode("ascii")

    except Exception:
        return None
