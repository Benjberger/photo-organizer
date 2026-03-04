# Photo Organizer

A tool for organizing, deduplicating, and managing photo collections. Built for the Fujifilm X100V workflow (JPEG + RAF RAW) but works with any camera. Includes both a CLI and a local web UI.

## Setup

```bash
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Web UI

The easiest way to use Photo Organizer — no terminal needed.

**Double-click `Photo Organizer.bat`** to launch the web interface in your browser.

Or from the command line:
```bash
python -m photo_organizer web              # opens browser to http://127.0.0.1:5000
python -m photo_organizer web --port 8080  # custom port
python -m photo_organizer web --no-open    # don't auto-open browser
```

The web UI supports all commands with a dark-themed interface, photo thumbnails, directory browsing, and a step-by-step group wizard.

## CLI Commands

### `metadata` — View EXIF data

```bash
python -m photo_organizer metadata photo.jpg
```

Shows camera make/model, date taken, dimensions, GPS coordinates, exposure settings, and more. Supports JPEG and RAW files (CR2, NEF, ARW, DNG, ORF, RW2, RAF).

### `organize` — Sort by date

```bash
python -m photo_organizer organize ./photos ./organized --dry-run
python -m photo_organizer organize ./photos ./organized --move
```

Reads EXIF dates and sorts photos into `YYYY/YYYY-MM-DD/` folders. Use `--dry-run` to preview, `--move` to move instead of copy.

### `duplicates` — Find duplicates

```bash
python -m photo_organizer duplicates ./photos
python -m photo_organizer duplicates ./photos --action move --duplicates-dir ./dupes
python -m photo_organizer duplicates ./photos --action delete
```

Detects duplicates by file content (SHA-256 hash), not filename. Uses a size-first filter to avoid hashing every file. Actions: `report` (default), `move`, or `delete`.

### `rename` — Batch rename

```bash
python -m photo_organizer rename ./photos --pattern "{date}_{seq}" --dry-run
python -m photo_organizer rename ./photos --pattern "{location}_{date}_{seq}"
python -m photo_organizer rename ./photos --undo undo_log.json
```

Rename photos using EXIF metadata placeholders: `{date}`, `{datetime}`, `{year}`, `{month}`, `{day}`, `{camera}`, `{model}`, `{seq}`, `{original}`, `{location}`. When `{location}` is used, photos are clustered by time and you're prompted to name each group. Saves an undo log for reversing renames.

### `review` — Visual contact sheet

```bash
python -m photo_organizer review ./photos --no-open
```

Groups photos by time and generates an HTML contact sheet with thumbnails. Opens in your browser for visual review. Use `--no-open` if the browser doesn't launch correctly.

### `select` — Score for printing

```bash
python -m photo_organizer select ./photos --min-score 70 --top 10
python -m photo_organizer select ./photos --tag print --export picks.txt
```

Scores photos based on technical quality (resolution, sharpness indicators) and identifies the best candidates for printing. Can tag and export selections.

### `group` — Group, deduplicate, and organize

```bash
python -m photo_organizer group ./scattered-photos ./organized --dry-run --no-open
python -m photo_organizer group ./scattered-photos ./organized --no-open
python -m photo_organizer group ./scattered-photos ./organized --undo .group_undo_log.json
```

The full workflow command. Consolidates photos from scattered directories into one organized library:

1. **Cluster** photos by time (configurable gap with `--gap-hours`)
2. **Detect duplicates** within each group
3. **Generate contact sheet** for visual review
4. **Prompt you to name** each group interactively
5. **Confirm duplicate removal** per file
6. **Move and rename** files into `destination/GroupName/` folders

Result:
```
organized/
├── Beach_Trip/
│   ├── Beach_Trip_2023-02-17_001.jpg
│   ├── Beach_Trip_2023-02-17_002.jpg
│   └── ...
├── Mountain_Hike/
│   ├── Mountain_Hike_2023-02-18_001.jpg
│   └── ...
└── .group_undo_log.json
```

Options:
- `--pattern` — file naming pattern (default: `{location}_{date}_{seq}`)
- `--gap-hours` — hours between groups (default: 3)
- `--dry-run` — preview without moving files
- `--no-open` — don't auto-open contact sheet
- `--undo LOG_FILE` — reverse a previous group operation

## Testing

```bash
python -m pytest tests/ -v
```

## Architecture

```
photo_organizer/
├── cli.py              # argparse CLI with all subcommands
├── metadata.py         # EXIF reading (Pillow + exifread + rawpy)
├── organizer.py        # Date-based folder organization
├── duplicates.py       # SHA-256 hash-based duplicate detection
├── renamer.py          # Pattern-based batch renaming with undo
├── grouping.py         # Time-based clustering + GPS reverse geocoding
├── contact_sheet.py    # HTML thumbnail generator
├── selector.py         # Photo scoring + tagging for print selection
├── group_organizer.py  # Group-organize workflow (cluster + dedup + move)
└── web/                # Flask web UI
    ├── __init__.py     # App factory
    ├── routes/         # API endpoints for each command
    ├── static/         # CSS + JavaScript (vanilla, no build step)
    └── templates/      # HTML shell
```

## Supported Formats

- **JPEG**: `.jpg`, `.jpeg`
- **RAW**: `.cr2`, `.nef`, `.arw`, `.dng`, `.orf`, `.rw2`, `.raf`

## Known Limitations

- RAF (Fuji RAW) EXIF dates not read by exifread — shows as "undated"
- No GPS on X100V, so `{location}` always requires manual naming
- Contact sheet `webbrowser.open()` can hang in some terminals — use `--no-open`
