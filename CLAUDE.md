# Photo Organizer - Project Notes

## Project Overview
A CLI photo organizing tool built as a Python learning project.
- **Repo:** https://github.com/Benjberger/photo-organizer
- **Python:** 3.14.3, virtual env in `venv/`
- **Camera:** Fujifilm X100V (no GPS, shoots JPEG + RAF RAW)

## How to Run
```bash
cd C:\Users\benjb\photo-organizer
.\venv\Scripts\activate           # activate virtual env
python -m photo_organizer --help  # see all commands
python -m photo_organizer web     # launch web UI at http://127.0.0.1:5000
python -m pytest tests/ -v        # run all 116 tests
```
Or double-click `Photo Organizer.bat` to launch the web UI without a terminal.

## Commands
| Command | Purpose |
|---------|---------|
| `metadata <file>` | Show EXIF data for a photo |
| `organize <src> <dest> [--dry-run] [--move]` | Sort photos into YYYY/YYYY-MM-DD folders |
| `duplicates <dir> [--action report\|move\|delete]` | Find duplicate photos by content hash |
| `rename <dir> --pattern "{location}_{date}_{seq}" [--dry-run]` | Batch rename with metadata placeholders |
| `review <dir> [--no-open]` | Generate HTML contact sheet for visual review |
| `select <dir> [--top N] [--min-score N] [--tag TAG]` | Score photos for print quality |
| `group <src> <dest> [--dry-run] [--no-open]` | Group, deduplicate, and organize photos into named folders |
| `web [--port N] [--no-open]` | Launch the web UI (default: http://127.0.0.1:5000) |

## Architecture
```
photo_organizer/
├── __init__.py       # Package version
├── __main__.py       # Entry point for `python -m`
├── cli.py            # argparse CLI with all subcommands
├── metadata.py       # EXIF reading (Pillow + exifread + rawpy)
├── organizer.py      # Date-based folder organization
├── duplicates.py     # SHA-256 hash-based duplicate detection
├── renamer.py        # Pattern-based batch renaming with undo
├── grouping.py       # Time-based clustering + GPS reverse geocoding
├── contact_sheet.py  # HTML thumbnail generator
├── selector.py       # Photo scoring + tagging for print selection
├── group_organizer.py # Group-organize workflow (cluster + dedup + move)
└── web/              # Flask web UI (vanilla HTML/JS, dark theme)
    ├── __init__.py   # App factory: create_app()
    ├── routes/       # API endpoints (browse, thumbnails, metadata, organize, duplicates, rename, review, select, group)
    ├── static/       # CSS + JS (no build step)
    └── templates/    # SPA shell (index.html)
```

## Known Limitations / Next Steps
- RAF (Fuji RAW) EXIF dates not read by exifread — shows as "undated"
- No GPS on X100V, so {location} always requires manual naming
- Contact sheet `webbrowser.open()` can hang in some terminal contexts — use `--no-open`
- Needs more testing on larger/mixed photo libraries before production use
- Future features: backup to external drive, HEIC conversion, camera stats
