import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from utils.database_manager import DatabaseError, database_file, query_database, register_database, resolve_database


def create_database(tmp_path, name="photos"):
    root = tmp_path / name
    (root / ".config").mkdir(parents=True)
    (root / ".config" / "properties.yaml").write_text(
        f"database:\n  directory: '{root.as_posix()}'\n  db_path: '{(root / 'media.db').as_posix()}'\n", encoding="utf-8"
    )
    sqlite3.connect(root / "media.db").close()
    return root


def test_databases_have_isolated_settings_and_hash_files(tmp_path, monkeypatch):
    catalog = tmp_path / "databases.json"
    monkeypatch.setenv("MEDIA_MANAGEMENT_DATABASE_CATALOG", str(catalog))
    first = create_database(tmp_path, "first")
    second = create_database(tmp_path, "second")

    register_database("first", first)
    register_database("second", second)

    assert resolve_database("first") == first.resolve()
    assert resolve_database("second") == second.resolve()
    assert database_file(resolve_database("first")) == (first / "media.db").resolve()
    assert json.loads(catalog.read_text())[0]["name"] == "first"


def test_read_only_query_does_not_modify_database(tmp_path, monkeypatch):
    catalog = tmp_path / "databases.json"
    monkeypatch.setenv("MEDIA_MANAGEMENT_DATABASE_CATALOG", str(catalog))
    root = create_database(tmp_path)
    register_database("photos", root)
    db_path = root / "media.db"
    connection = sqlite3.connect(db_path)
    connection.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")
    connection.execute("INSERT INTO items(name) VALUES (?)", ("private",))
    connection.commit()
    connection.close()

    columns, rows = query_database(root, "SELECT name FROM items")

    assert columns == ["name"]
    assert rows == [("private",)]
    for statement in ("DELETE FROM items", "DROP TABLE items", "INSERT INTO items VALUES (2, 'bad')"):
        try:
            query_database(root, statement)
        except DatabaseError:
            pass
        else:
            raise AssertionError(f"Unsafe statement accepted: {statement}")


def test_registered_database_name_matches_current_path(tmp_path, monkeypatch):
    catalog = tmp_path / "databases.json"
    monkeypatch.setenv("MEDIA_MANAGEMENT_DATABASE_CATALOG", str(catalog))
    root = create_database(tmp_path, "photos")
    register_database("photos", root)

    assert str(resolve_database("photos")) == str(root.resolve())


def test_unknown_database_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_MANAGEMENT_DATABASE_CATALOG", str(tmp_path / "databases.json"))
    monkeypatch.delenv("MEDIA_DB", raising=False)
    try:
        resolve_database()
    except DatabaseError:
        pass
    else:
        raise AssertionError("Missing database selection was accepted")
