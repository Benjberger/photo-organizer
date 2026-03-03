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

    # Subcommands will be added here as we build each feature.
    # For example: organize, duplicates, rename, select
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    return parser


def main():
    """Main entry point for the CLI."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()


if __name__ == "__main__":
    main()
