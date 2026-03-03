# Photo Organizer

A command-line tool for organizing, deduplicating, and managing photo collections.

## Features

- Read EXIF metadata from JPEG and RAW files (CR2, NEF, ARW)
- Organize photos into date-based folder structures
- Detect and handle duplicate photos
- Batch rename photos using customizable patterns
- Identify best photos for printing

## Setup

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

```bash
python -m photo_organizer --help
```
