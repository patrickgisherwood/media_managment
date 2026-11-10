import json
import os
import sqlite3
from pathlib import Path


class DatabaseError(RuntimeError):
    pass


def runtime_root():
    return Path(os.environ.get("MEDIA_MANAGEMENT_ROOT", "/etc/media_management")).expanduser()


def catalog_path():
    return Path(os.environ.get("MEDIA_MANAGEMENT_DATABASE_CATALOG", runtime_root() / "databases.json"))


def load_catalog():
    path = catalog_path()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        raise DatabaseError(f"Could not read database catalog {path}: {error}") from error
    if not isinstance(data, list):
        raise DatabaseError(f"Database catalog must contain a JSON list: {path}")
    return data


def save_catalog(entries):
    path = catalog_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    unique = {}
    for entry in entries:
        normalized = normalize_entry(entry)
        unique[normalized["name"]] = normalized
    path.write_text(json.dumps(list(unique.values()), indent=2) + "\n", encoding="utf-8")


def normalize_entry(entry):
    if not isinstance(entry, dict) or not entry.get("name") or not entry.get("path"):
        raise DatabaseError("Database catalog entries require name and path")
    return {"name": str(entry["name"]), "path": str(Path(entry["path"]).expanduser().resolve())}


def register_database(name, path):
    entry = normalize_entry({"name": name, "path": path})
    entries = load_catalog()
    entries = [item for item in entries if normalize_entry(item)["name"] != entry["name"] and normalize_entry(item)["path"] != entry["path"]]
    entries.append(entry)
    save_catalog(entries)
    return entry


def validate_database(path):
    db_root = Path(path).expanduser().resolve()
    properties = db_root / ".config" / "properties.yaml"
    if not db_root.is_dir():
        raise DatabaseError(f"Database directory does not exist: {db_root}")
    if not properties.is_file():
        raise DatabaseError(f"Database configuration does not exist: {properties}")
    return db_root


def resolve_database(selector=None):
    selector = selector or os.environ.get("MEDIA_DB")
    if not selector:
        raise DatabaseError("No database selected. Use --database NAME, set MEDIA_DB, or run a database setup.")

    candidate = Path(selector).expanduser()
    if candidate.exists():
        return validate_database(candidate)

    matches = []
    for raw_entry in load_catalog():
        entry = normalize_entry(raw_entry)
        if entry["name"] == selector:
            matches.append(entry)
    if len(matches) == 1:
        return validate_database(matches[0]["path"])
    if len(matches) > 1:
        raise DatabaseError(f"Database name is ambiguous: {selector}")

    raise DatabaseError(f"Unknown database {selector!r}")


def read_database_properties(db_root):
    try:
        from utils.confighandler import AppProperties
        properties = db_root / ".config" / "properties.yaml"
        return AppProperties(str(properties))
    except ImportError as error:
        raise DatabaseError(f"Could not load database configuration support: {error}") from error


def database_file(db_root):
    props = read_database_properties(db_root)
    configured = props.get("database.db_path")
    db_path = Path(configured).expanduser() if configured else db_root / "media.db"
    if not db_path.is_absolute():
        db_path = db_root / db_path
    db_path = db_path.resolve()
    if db_path.parent != db_root.resolve() and db_root.resolve() not in db_path.parents:
        raise DatabaseError(f"Database file escaped database root: {db_path}")
    if not db_path.is_file():
        raise DatabaseError(f"Database file does not exist: {db_path}")
    return db_path


def query_database(db_root, sql):
    db_path = database_file(db_root)
    normalized = sql.strip().rstrip(";")
    if not normalized or ";" in normalized:
        raise DatabaseError("Provide exactly one read-only SQL statement without semicolons.")
    first_word = normalized.split(None, 1)[0].upper()
    if first_word not in {"SELECT", "PRAGMA", "EXPLAIN"}:
        raise DatabaseError("Only SELECT, PRAGMA, and EXPLAIN queries are allowed.")
    uri = f"file:{db_path.as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        cursor = connection.execute(normalized)
        columns = [description[0] for description in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        return columns, rows
    finally:
        connection.close()
