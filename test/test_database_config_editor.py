import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for candidate in [str(ROOT), str(SRC), str(SRC / "utils")]:
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from confighandler import AppProperties

SPEC = importlib.util.spec_from_file_location("manage_db_config", ROOT / "scripts" / "manage_db_config.py")
manage_db_config = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manage_db_config)


def test_app_properties_can_set_nested_bool_values(tmp_path):
    config_path = tmp_path / "properties.yaml"
    config_path.write_text(
        "image_handling:\n  delete_after_copy: false\n  archive: true\n  duplicate_detection:\n    prevent_duplicates: true\n",
        encoding="utf-8",
    )

    props = AppProperties(str(config_path))
    props.set("image_handling.delete_after_copy", False)
    props.set("image_handling.archive", False)
    props.set("image_handling.duplicate_detection.prevent_duplicates", False)
    props.save()

    reloaded = AppProperties(str(config_path))
    assert reloaded.get("image_handling.delete_after_copy") is False
    assert reloaded.get("image_handling.archive") is False
    assert reloaded.get("image_handling.duplicate_detection.prevent_duplicates") is False


def test_prompt_bool_keeps_existing_value_on_empty_input(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _prompt: "")

    assert manage_db_config.prompt_bool("Enable duplicate detection?", False) is False
    assert manage_db_config.prompt_bool("Archive duplicates?", True) is True
