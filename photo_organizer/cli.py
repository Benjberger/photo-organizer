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

    # --- group command ---
    group_parser = subparsers.add_parser(
        "group",
        help="Group, deduplicate, and organize photos into named folders",
    )
    group_parser.add_argument(
        "source",
        help="Directory containing photos to organize",
    )
    group_parser.add_argument(
        "destination",
        help="Root directory to create group folders in",
    )
    group_parser.add_argument(
        "--pattern", default="{location}_{date}_{seq}",
        help="Naming pattern for files (default: {location}_{date}_{seq})",
    )
    group_parser.add_argument(
        "--gap-hours", type=float, default=3.0,
        help="Hours between photo groups for time clustering (default: 3)",
    )
    group_parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview the plan without moving any files",
    )
    group_parser.add_argument(
        "--undo-log",
        help="Path for the undo log (default: destination/.group_undo_log.json)",
    )
    group_parser.add_argument(
        "--undo", metavar="LOG_FILE",
        help="Reverse a previous group operation using an undo log",
    )
    group_parser.add_argument(
        "--no-open", action="store_true",
        help="Don't automatically open the contact sheet in a browser",
    )

    # --- select command ---
    select_parser = subparsers.add_parser(
        "select",
        help="Score photos and identify best candidates for printing",
    )
    select_parser.add_argument(
        "directory",
        help="Directory containing photos to score",
    )
    select_parser.add_argument(
        "--min-score", type=float, default=60,
        help="Minimum score to be a print candidate (0-100, default: 60)",
    )
    select_parser.add_argument(
        "--top", type=int, default=None,
        help="Show only the top N photos",
    )
    select_parser.add_argument(
        "--export", metavar="FILE",
        help="Export selected photo paths to a text file",
    )
    select_parser.add_argument(
        "--tag", metavar="TAG",
        help="Tag all candidates with this label (e.g., 'print')",
    )
    select_parser.add_argument(
        "--tags-file", default="photo_tags.json",
        help="JSON file for storing tags (default: photo_tags.json)",
    )

    # --- web command ---
    web_parser = subparsers.add_parser(
        "web",
        help="Launch the web interface",
    )
    web_parser.add_argument(
        "--port", type=int, default=5000,
        help="Port to run on (default: 5000)",
    )
    web_parser.add_argument(
        "--no-open", action="store_true",
        help="Don't automatically open browser",
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
    elif args.command == "select":
        _cmd_select(args)
    elif args.command == "group":
        _cmd_group(args)
    elif args.command == "web":
        _cmd_web(args)


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


def _cmd_select(args):
    """Handle the 'select' subcommand."""
    from photo_organizer.selector import (
        score_directory,
        get_print_candidates,
        format_scores_report,
        load_tags,
        save_tags,
        tag_photo,
        export_selection,
    )

    print(f"Scoring photos in {args.directory}...")
    scores = score_directory(args.directory)

    if not scores:
        print("No photos found.")
        return

    candidates = get_print_candidates(scores, min_score=args.min_score, top_n=args.top)

    print(f"\nAll {len(scores)} photos scored. "
          f"{len(candidates)} meet the threshold (score >= {args.min_score}).\n")
    print(format_scores_report(candidates))

    # Tag candidates if requested
    if args.tag and candidates:
        tags = load_tags(args.tags_file)
        for s in candidates:
            tag_photo(tags, s["filepath"], args.tag)
        save_tags(tags, args.tags_file)
        print(f"\nTagged {len(candidates)} photo(s) as '{args.tag}' in {args.tags_file}")

    # Export if requested
    if args.export and candidates:
        paths = [str(s["filepath"]) for s in candidates]
        export_selection(paths, args.export)
        print(f"Exported {len(candidates)} path(s) to {args.export}")


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


def _cmd_group(args):
    """Handle the 'group' subcommand."""
    from pathlib import Path

    from photo_organizer.group_organizer import (
        find_group_duplicates,
        format_group_duplicates,
        prompt_duplicate_removal,
        prompt_for_cluster_dates,
        plan_group_moves,
        preview_group_moves,
        execute_group_moves,
        undo_group_moves,
    )

    # Undo mode
    if args.undo:
        print(f"Undoing group moves from {args.undo}...")
        results = undo_group_moves(args.undo)
        print(f"Restored {results['success']} file(s), {results['failed']} failed.")
        for error in results["errors"]:
            print(f"  Error: {error}")
        return

    from photo_organizer.grouping import (
        cluster_by_time,
        resolve_cluster_locations,
        prompt_for_cluster_names,
        format_clusters_report,
    )
    from photo_organizer.contact_sheet import generate_contact_sheet

    # Step 1: Cluster by time
    print(f"Scanning {args.source} for photos...")
    print(f"Grouping by time (gap: {args.gap_hours}h)...")
    clusters = cluster_by_time(args.source, gap_hours=args.gap_hours)
    clusters = resolve_cluster_locations(clusters)
    print(format_clusters_report(clusters))

    if not clusters:
        print("No photos found.")
        return

    # Step 2: Find duplicates within groups
    print("\nChecking for duplicates within groups...")
    group_dupes = find_group_duplicates(clusters)
    if group_dupes:
        print(format_group_duplicates(clusters, group_dupes))
    else:
        print("  No duplicates found.")

    # Step 3: Generate contact sheet for visual review
    print("\nGenerating contact sheet for review...")
    sheet_path = generate_contact_sheet(
        clusters, open_browser=not args.no_open
    )
    print(f"Contact sheet: {sheet_path.resolve()}")

    if args.dry_run:
        # In dry-run mode, show what would happen with placeholder names
        print("\n(Dry run — skipping interactive prompts)")
        exclude = set()
        # Collect all dupes as excluded for dry-run preview
        for dupe_groups in group_dupes.values():
            for group in dupe_groups:
                for dupe in group[1:]:
                    exclude.add(dupe)
    else:
        # Step 4: Prompt user to name groups
        clusters = prompt_for_cluster_names(clusters)

        # Step 4b: Prompt for dates on undated clusters
        clusters = prompt_for_cluster_dates(clusters)

        # Step 5: Prompt for duplicate removal
        exclude = set()
        if group_dupes:
            exclude = prompt_duplicate_removal(clusters, group_dupes)

    # Step 6: Plan moves
    print(f"\nPlanning organization with pattern: {args.pattern}")
    moves = plan_group_moves(
        clusters, args.destination, pattern=args.pattern, exclude=exclude
    )

    if not moves:
        print("No files to move.")
        return

    # Step 7: Preview
    print(preview_group_moves(moves))

    if args.dry_run:
        print("(Dry run — no files were changed)")
        return

    # Step 8: Execute moves
    undo_log = args.undo_log or str(
        Path(args.destination) / ".group_undo_log.json"
    )

    total = len(moves)
    print(f"Moving {total} photo(s) into group folders...")
    results = execute_group_moves(moves, undo_log_path=undo_log)

    dupes_removed = len(exclude)
    print(f"Done! {results['success']} succeeded, {results['failed']} failed.")
    if dupes_removed:
        print(f"{dupes_removed} duplicate(s) removed.")
    print(f"Undo log saved to: {undo_log}")

    for error in results["errors"]:
        print(f"  Error: {error}")


def _cmd_web(args):
    """Handle the 'web' subcommand."""
    from photo_organizer.web import create_app

    app = create_app()
    url = f"http://127.0.0.1:{args.port}"
    print(f"Starting Photo Organizer web UI at {url}")

    if not args.no_open:
        import threading
        import webbrowser
        threading.Timer(1.0, webbrowser.open, args=[url]).start()

    app.run(host="127.0.0.1", port=args.port, debug=False)


if __name__ == "__main__":
    main()
