"""Command-line interface for Photo Organizer.

argparse is Python's built-in library for building CLIs. It automatically
generates --help text and validates user input for you.
"""

import argparse

from photo_organizer import __version__


def build_parser():
    """Build the argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="photo_organizer",
        description="Organize, deduplicate, and manage photo collections.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- organize command ---
    organize_parser = subparsers.add_parser(
        "organize",
        help="Organize photos into date-based folders",
    )
    organize_parser.add_argument(
        "source",
        help="Directory containing photos to organize",
    )
    organize_parser.add_argument(
        "destination",
        help="Directory to create organized folder structure in",
    )
    organize_parser.add_argument(
        "--move", action="store_true",
        help="Move files instead of copying (default: copy)",
    )
    organize_parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would happen without actually doing it",
    )

    # --- metadata command ---
    metadata_parser = subparsers.add_parser(
        "metadata",
        help="Show metadata for a photo file",
    )
    metadata_parser.add_argument(
        "file",
        help="Path to a photo file",
    )

    return parser


def main():
    """Main entry point for the CLI."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
    elif args.command == "organize":
        _cmd_organize(args)
    elif args.command == "metadata":
        _cmd_metadata(args)


def _cmd_organize(args):
    """Handle the 'organize' subcommand."""
    from photo_organizer.organizer import (
        plan_organization,
        preview_organization,
        execute_organization,
    )

    print(f"Scanning {args.source} for photos...")
    moves = plan_organization(args.source, args.destination)

    if not moves:
        print("No photos found.")
        return

    print(preview_organization(moves))

    if args.dry_run:
        print("(Dry run — no files were changed)")
        return

    mode = "move" if args.move else "copy"
    print(f"{'Moving' if args.move else 'Copying'} {len(moves)} photo(s)...")
    results = execute_organization(moves, mode=mode)

    print(f"Done! {results['success']} succeeded, {results['failed']} failed.")
    for error in results["errors"]:
        print(f"  Error: {error}")


def _cmd_metadata(args):
    """Handle the 'metadata' subcommand."""
    from photo_organizer.metadata import read_metadata, format_metadata

    metadata = read_metadata(args.file)
    print(format_metadata(metadata))


if __name__ == "__main__":
    main()
