#!/usr/bin/env python3
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from utils.database_manager import DatabaseError, catalog_path, load_catalog, normalize_entry, query_database, register_database, resolve_database, validate_database


def print_table(columns, rows):
    if not columns:
        print("OK")
        return
    widths = [len(column) for column in columns]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len("NULL" if value is None else str(value)))
    print("  ".join(column.ljust(widths[index]) for index, column in enumerate(columns)))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(("NULL" if value is None else str(value)).ljust(widths[index]) for index, value in enumerate(row)))


def main():
    parser = argparse.ArgumentParser(description="Manage Media Management databases")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List registered databases")
    register = subparsers.add_parser("register", help="Register an existing database")
    register.add_argument("name")
    register.add_argument("path")
    current = subparsers.add_parser("current", help="Show the currently selected database")
    current.add_argument("--database", help="Database name or path")
    use = subparsers.add_parser("use", help="Select a database")
    use.add_argument("database")
    resolve = subparsers.add_parser("resolve", help="Print the path for a database name or path")
    resolve.add_argument("database", nargs="?")
    query = subparsers.add_parser("query", help="Run one read-only SQL query against a database")
    query.add_argument("database")
    query.add_argument("sql", nargs="+")

    args = parser.parse_args()
    try:
        if args.command == "list":
            entries = load_catalog()
            if not entries:
                print("No databases are registered.")
                return 0
            print(f"Registered databases ({catalog_path()}):")
            active_path = None
            if os.environ.get("MEDIA_DB"):
                try:
                    active_path = Path(os.environ["MEDIA_DB"]).expanduser().resolve()
                except (OSError, RuntimeError):
                    active_path = None
            for raw_entry in entries:
                entry = normalize_entry(raw_entry)
                selected = active_path == Path(entry["path"])
                marker = "* " if selected else "  "
                print(f"{marker}{entry['name']}\t{entry['path']}")
            return 0
        if args.command == "register":
            validate_database(args.path)
            entry = register_database(args.name, args.path)
            print(f"Registered {entry['name']} at {entry['path']}")
            return 0
        if args.command == "current":
            root = resolve_database(args.database)
            registered = [normalize_entry(item) for item in load_catalog()]
            matches = [item for item in registered if Path(item["path"]) == root]
            if matches:
                print(f"{matches[0]['name']}\t{root}")
            else:
                print(f"{root}\t[unregistered]", file=sys.stdout)
                print(f"Warning: current database is not in {catalog_path()} and may be an old database selection.", file=sys.stderr)
            return 0
        if args.command == "resolve":
            print(resolve_database(args.database))
            return 0
        if args.command == "use":
            root = resolve_database(args.database)
            print(f"export MEDIA_DB={shlex.quote(str(root))}")
            return 0
        if args.command == "query":
            root = resolve_database(args.database)
            columns, rows = query_database(root, " ".join(args.sql))
            print(f"Database: {args.database} ({root})")
            print_table(columns, rows)
            return 0
    except DatabaseError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    import shlex
    raise SystemExit(main())
