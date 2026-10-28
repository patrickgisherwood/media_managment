#!/usr/bin/env python3

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
UTILS_DIR = SRC_DIR / "utils"
for candidate in [str(SRC_DIR), str(UTILS_DIR), str(ROOT_DIR)]:
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from confighandler import AppProperties


def get_config_path():
    db_root = os.environ.get("MEDIA_DB")
    if not db_root:
        raise RuntimeError("MEDIA_DB is not set. Export it or source /etc/profile.d/media_db.sh first.")
    db_dir = Path(db_root)
    config_path = db_dir / ".config" / "properties.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Database config not found: {config_path}")
    return config_path


def prompt_bool(label, current_value):
    default = "y" if bool(current_value) else "n"
    raw = input(f"{label} [{default.upper() if default == 'y' else default.lower()}] (y/N): ").strip().lower()
    if raw == "":
        return bool(current_value)
    if raw in ("y", "yes"):
        return True
    if raw in ("n", "no"):
        return False
    return bool(current_value)


def main():
    config_path = get_config_path()
    props = AppProperties(str(config_path))

    print(f"Editing database config: {config_path}")
    print()

    delete_after_copy = prompt_bool(
        "Delete after copy? (WARNING: permanently deletes originals from the import directory).  Current Config Value: "+str(props.get("image_handling.delete_after_copy", False)),
        props.get("image_handling.delete_after_copy", False),
    )
    prevent_duplicates = prompt_bool(
        "Enable duplicate detection?",
        props.get("image_handling.duplicate_detection.prevent_duplicates", True),
    )
    archive_enabled = prompt_bool(
        "Archive duplicates?",
        props.get("image_handling.archive", True),
    )

    props.set("image_handling.delete_after_copy", delete_after_copy)
    props.set("image_handling.duplicate_detection.prevent_duplicates", prevent_duplicates)
    props.set("image_handling.archive", archive_enabled)
    props.save()

    print()
    print("Updated database settings:")
    print(f"  delete_after_copy = {delete_after_copy}")
    print(f"  prevent_duplicates = {prevent_duplicates}")
    print(f"  archive = {archive_enabled}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
