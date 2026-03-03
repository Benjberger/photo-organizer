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

    # --- duplicates command ---
    dupes_parser = subparsers.add_parser(
        "duplicates",
        help="Find and handle duplicate photos",
    )
    dupes_parser.add_argument(
        "directory",
        help="Directory to scan for duplicates",
    )
    dupes_parser.add_argument(
        "--action", choices=["report", "move", "delete"], default="report",
        help="What to do with duplicates (default: report)",
    )
    dupes_parser.add_argument(
        "--duplicates-dir",
        help="Where to move duplicates (required with --action=move)",
    )

    # --- rename command ---
    rename_parser = subparsers.add_parser(
        "rename",
        help="Batch rename photos using a pattern",
    )
    rename_parser.add_argument(
        "directory",
        help="Directory containing photos to rename",
    )
    rename_parser.add_argument(
        "--pattern", default="{date}_{seq}",
        help="Naming pattern (default: {date}_{seq}). "
             "Placeholders: {date}, {datetime}, {year}, {month}, {day}, "
             "{camera}, {model}, {seq}, {original}, {location}",
    )
    rename_parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview renames without applying them",
    )
    rename_parser.add_argument(
        "--undo-log",
        help="Path to save undo log (JSON file for reversing renames)",
    )
    rename_parser.add_argument(
        "--undo", metavar="LOG_FILE",
        help="Reverse a previous rename using an undo log file",
    )
    rename_parser.add_argument(
        "--gap-hours", type=float, default=3.0,
        help="Hours between photo groups for {location} clustering (default: 3)",
    )

    # --- review command ---
    review_parser = subparsers.add_parser(
        "review",
        help="Generate an HTML contact sheet to visually review photo groups",
    )
    review_parser.add_argument(
        "directory",
        help="Directory containing photos to review",
    )
    review_parser.add_argument(
        "--gap-hours", type=float, default=3.0,
        help="Hours between photo groups (default: 3)",
    )
    review_parser.add_argument(
        "--output", default=None,
        help="Output HTML file path (default: contact_sheet.html)",
    )
    review_parser.add_argument(
        "--no-open", action="store_true",
        help="Don't automatically open the contact sheet in a browser",
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
    elif args.command == "duplicates":
        _cmd_duplicates(args)
    elif args.command == "rename":
        _cmd_rename(args)
    elif args.command == "review":
        _cmd_review(args)


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


def _cmd_duplicates(args):
    """Handle the 'duplicates' subcommand."""
    from photo_organizer.duplicates import (
        find_duplicates,
        format_duplicates_report,
        handle_duplicates,
    )

    print(f"Scanning {args.directory} for duplicates...")
    groups = find_duplicates(args.directory)
    print(format_duplicates_report(groups))

    if args.action != "report" and groups:
        print(f"\n{args.action.title()}ing duplicates...")
        results = handle_duplicates(
            groups, action=args.action, duplicates_dir=args.duplicates_dir
        )
        print(f"Processed {results['processed']} duplicate(s).")
        for error in results["errors"]:
            print(f"  Error: {error}")


def _cmd_rename(args):
    """Handle the 'rename' subcommand."""
    from photo_organizer.renamer import (
        plan_renames,
        preview_renames,
        execute_renames,
        undo_renames,
    )

    # Undo mode: reverse a previous rename
    if args.undo:
        print(f"Undoing renames from {args.undo}...")
        results = undo_renames(args.undo)
        print(f"Restored {results['success']} file(s), {results['failed']} failed.")
        for error in results["errors"]:
            print(f"  Error: {error}")
        return

    # If pattern uses {location}, run the grouping pipeline
    location_map = None
    if "{location}" in args.pattern:
        from photo_organizer.grouping import (
            cluster_by_time,
            resolve_cluster_locations,
            prompt_for_cluster_names,
            build_location_map,
            format_clusters_report,
        )

        from photo_organizer.contact_sheet import generate_contact_sheet

        print(f"Grouping photos by time (gap: {args.gap_hours}h)...")
        clusters = cluster_by_time(args.directory, gap_hours=args.gap_hours)
        clusters = resolve_cluster_locations(clusters)
        print(format_clusters_report(clusters))

        # Generate a contact sheet so you can see the photos before naming
        print("\nGenerating contact sheet for review...")
        sheet_path = generate_contact_sheet(clusters, open_browser=True)
        print(f"Contact sheet: {sheet_path.resolve()}")

        # Prompt user to name any clusters without a location
        if not args.dry_run:
            clusters = prompt_for_cluster_names(clusters)

        location_map = build_location_map(clusters)

    # Normal rename mode
    print(f"\nPlanning renames with pattern: {args.pattern}")
    renames = plan_renames(args.directory, args.pattern, location_map=location_map)

    if not renames:
        print("No files to rename.")
        return

    print(preview_renames(renames))

    if args.dry_run:
        print("(Dry run — no files were changed)")
        return

    results = execute_renames(renames, undo_log_path=args.undo_log)
    print(f"Renamed {results['success']} file(s), {results['failed']} failed.")
    if args.undo_log:
        print(f"Undo log saved to: {args.undo_log}")
    for error in results["errors"]:
        print(f"  Error: {error}")


def _cmd_review(args):
    """Handle the 'review' subcommand."""
    from photo_organizer.grouping import (
        cluster_by_time,
        resolve_cluster_locations,
        format_clusters_report,
    )
    from photo_organizer.contact_sheet import generate_contact_sheet

    print(f"Grouping photos by time (gap: {args.gap_hours}h)...")
    clusters = cluster_by_time(args.directory, gap_hours=args.gap_hours)
    clusters = resolve_cluster_locations(clusters)
    print(format_clusters_report(clusters))

    print("\nGenerating contact sheet...")
    sheet_path = generate_contact_sheet(
        clusters, output_path=args.output, open_browser=not args.no_open
    )
    print(f"Contact sheet saved to: {sheet_path.resolve()}")
    if args.no_open:
        print("Open it in your browser to review the groups.")


if __name__ == "__main__":
    main()
