"""Read metadata (EXIF data) from photo files.

EXIF (Exchangeable Image File Format) is information embedded in photos by
cameras. It includes: date taken, camera model, dimensions, GPS coordinates,
exposure settings, and more.

This module supports:
- JPEG files: full EXIF reading via Pillow and exifread
- RAW files (CR2, NEF, ARW, etc.): basic metadata via exifread and rawpy
"""

import io
import sys
from datetime import datetime
from pathlib import Path

import exifread
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

# File extensions we support
JPEG_EXTENSIONS = {".jpg", ".jpeg"}
RAW_EXTENSIONS = {".cr2", ".nef", ".arw", ".dng", ".orf", ".rw2", ".raf"}
SUPPORTED_EXTENSIONS = JPEG_EXTENSIONS | RAW_EXTENSIONS


def is_supported(filepath):
    """Check if a file is a supported photo format.

    Args:
        filepath: Path to the file (string or Path object).

    Returns:
        True if the file extension is one we can handle.
    """
    return Path(filepath).suffix.lower() in SUPPORTED_EXTENSIONS


def read_exif_jpeg(filepath):
    """Read EXIF metadata from a JPEG file using Pillow.

    Pillow is a Python image library. It can open images AND read their
    embedded EXIF data. The EXIF data comes as numbered "tags" — we convert
    those numbers to human-readable names using the TAGS dictionary.

    Args:
        filepath: Path to a JPEG file.

    Returns:
        A dictionary of tag_name -> value pairs, or empty dict if no EXIF.
    """
    filepath = Path(filepath)
    metadata = {}

    try:
        with Image.open(filepath) as img:
            # Get basic image info (always available, not EXIF-specific)
            metadata["Width"] = img.width
            metadata["Height"] = img.height
            metadata["Format"] = img.format

            # Get EXIF data (may not exist in all JPEGs)
            exif_data = img._getexif()
            if exif_data is None:
                return metadata

            # Convert numeric tag IDs to human-readable names
            # EXIF stores tags as numbers like 271, 272, etc.
            # TAGS maps these to names like "Make", "Model", etc.
            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, str(tag_id))

                # GPSInfo is nested — handle it specially
                if tag_name == "GPSInfo":
                    gps = _parse_gps_info(value)
                    if gps:
                        metadata.update(gps)
                else:
                    metadata[tag_name] = value

    except Exception as e:
        metadata["Error"] = str(e)

    return metadata


def read_exif_raw(filepath):
    """Read EXIF metadata from a RAW file using exifread.

    RAW files are the unprocessed sensor data from cameras. They're much
    larger than JPEGs but contain more detail. The exifread library can
    read EXIF tags from many RAW formats without loading the full image.

    Args:
        filepath: Path to a RAW file.

    Returns:
        A dictionary of tag_name -> value pairs.
    """
    filepath = Path(filepath)
    metadata = {}

    try:
        # Suppress exifread's "File format not recognized" messages —
        # it prints directly to stderr instead of using logging
        with open(filepath, "rb") as f:
            old_stderr = sys.stderr
            sys.stderr = io.StringIO()
            try:
                tags = exifread.process_file(f, details=False)
            finally:
                sys.stderr = old_stderr

        for tag_name, value in tags.items():
            # exifread prefixes tags like "EXIF DateTimeOriginal"
            # We strip the prefix for cleaner output
            clean_name = tag_name.split(" ", 1)[-1] if " " in tag_name else tag_name
            metadata[clean_name] = str(value)

        # Try to get dimensions from the RAW file using rawpy
        try:
            import rawpy
            with rawpy.imread(str(filepath)) as raw:
                metadata["Width"] = raw.sizes.width
                metadata["Height"] = raw.sizes.height
        except Exception:
            pass  # rawpy may not support all formats

    except Exception as e:
        metadata["Error"] = str(e)

    return metadata


def read_metadata(filepath):
    """Read metadata from any supported photo file.

    This is the main function you should call. It detects the file type
    and uses the right method to read metadata.

    Args:
        filepath: Path to a photo file.

    Returns:
        A dictionary with metadata. Always includes "Filepath" and "Filetype".
    """
    filepath = Path(filepath)

    if not filepath.exists():
        return {"Filepath": str(filepath), "Error": "File not found"}

    if not is_supported(filepath):
        return {"Filepath": str(filepath), "Error": f"Unsupported format: {filepath.suffix}"}

    result = {"Filepath": str(filepath), "Filetype": filepath.suffix.lower()}

    # Add file size (useful for quick comparisons)
    result["FileSize"] = filepath.stat().st_size

    # Read EXIF based on file type
    suffix = filepath.suffix.lower()
    if suffix in JPEG_EXTENSIONS:
        exif = read_exif_jpeg(filepath)
    elif suffix in RAW_EXTENSIONS:
        exif = read_exif_raw(filepath)
    else:
        exif = {}

    result.update(exif)
    return result


def get_date_taken(filepath):
    """Extract the date a photo was taken.

    Cameras store the date in EXIF tags like "DateTimeOriginal". This
    function finds that date and returns it as a Python datetime object.

    Args:
        filepath: Path to a photo file.

    Returns:
        A datetime object, or None if no date was found.
    """
    metadata = read_metadata(filepath)

    # Try different EXIF tag names for the date (cameras use different ones)
    date_tags = ["DateTimeOriginal", "DateTimeDigitized", "DateTime"]

    for tag in date_tags:
        if tag in metadata:
            value = metadata[tag]
            # EXIF dates look like "2024:01:15 14:30:00"
            date_str = str(value).strip()
            for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue

    return None


def format_metadata(metadata):
    """Format metadata as a readable string for display.

    Args:
        metadata: Dictionary from read_metadata().

    Returns:
        A formatted multi-line string.
    """
    lines = []

    # Display order: most useful info first
    priority_keys = [
        "Filepath", "Filetype", "Width", "Height", "FileSize",
        "DateTimeOriginal", "Make", "Model", "LensModel",
        "ExposureTime", "FNumber", "ISOSpeedRatings",
        "Latitude", "Longitude",
    ]

    # Show priority keys first (if they exist)
    shown = set()
    for key in priority_keys:
        if key in metadata:
            value = _format_value(key, metadata[key])
            lines.append(f"  {key:.<30} {value}")
            shown.add(key)

    # Show remaining keys
    for key, value in sorted(metadata.items()):
        if key not in shown and key != "Error":
            value = _format_value(key, value)
            lines.append(f"  {key:.<30} {value}")

    # Show errors last
    if "Error" in metadata:
        lines.append(f"  {'Error':.<30} {metadata['Error']}")

    return "\n".join(lines)


def _format_value(key, value):
    """Format a single metadata value for display."""
    if key == "FileSize":
        # Convert bytes to human-readable
        size = int(value)
        if size >= 1_000_000:
            return f"{size / 1_000_000:.1f} MB"
        elif size >= 1_000:
            return f"{size / 1_000:.1f} KB"
        return f"{size} bytes"
    return str(value)


def _parse_gps_info(gps_data):
    """Parse GPS EXIF data into latitude/longitude.

    GPS coordinates in EXIF are stored as degrees/minutes/seconds,
    which we convert to decimal degrees (like Google Maps uses).
    """
    result = {}

    try:
        # GPS data uses numeric tag IDs too
        gps_tags = {}
        for tag_id, value in gps_data.items():
            tag_name = GPSTAGS.get(tag_id, str(tag_id))
            gps_tags[tag_name] = value

        if "GPSLatitude" in gps_tags and "GPSLatitudeRef" in gps_tags:
            lat = _dms_to_decimal(gps_tags["GPSLatitude"])
            if gps_tags["GPSLatitudeRef"] == "S":
                lat = -lat
            result["Latitude"] = round(lat, 6)

        if "GPSLongitude" in gps_tags and "GPSLongitudeRef" in gps_tags:
            lon = _dms_to_decimal(gps_tags["GPSLongitude"])
            if gps_tags["GPSLongitudeRef"] == "W":
                lon = -lon
            result["Longitude"] = round(lon, 6)

    except Exception:
        pass

    return result


def _dms_to_decimal(dms):
    """Convert degrees/minutes/seconds to decimal degrees.

    Cameras store GPS as (degrees, minutes, seconds) — three separate
    numbers. Decimal degrees is a single number like 37.7749.
    """
    degrees = float(dms[0])
    minutes = float(dms[1])
    seconds = float(dms[2])
    return degrees + minutes / 60 + seconds / 3600
