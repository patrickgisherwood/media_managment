from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_script_bootstrap_uses_src_parent_not_src_utils():
    script_text = (REPO_ROOT / "scripts" / "import_media.py").read_text(encoding="utf-8")
    assert 'str(SRC_DIR)' in script_text
    assert 'str(SRC_DIR / "handlers")' in script_text
    assert 'str(SRC_DIR / "core")' in script_text
    assert 'str(SRC_DIR / "utils")' not in script_text


def test_app_shell_exports_parent_src_path_only():
    shell_text = (REPO_ROOT / "app.sh").read_text(encoding="utf-8")
    assert 'src/utils' not in shell_text
    assert 'export PYTHONPATH="$SCRIPT_DIR:$SCRIPT_DIR/src' in shell_text


def test_database_setup_creates_dot_tmp_directory():
    setup_text = (REPO_ROOT / "scripts" / "setup_db.sh").read_text(encoding="utf-8")
    assert '$DB_PATH/.tmp' in setup_text
    assert 'mkdir -p "$DB_PATH/.tmp"' in setup_text


def test_image_import_creates_configured_temporary_directory():
    import_text = (REPO_ROOT / "scripts" / "import_media.py").read_text(encoding="utf-8")
    handler_text = (REPO_ROOT / "src" / "handlers" / "Image_Handler.py").read_text(encoding="utf-8")
    assert 'os.path.join(root_path, ".tmp")' in import_text
    assert 'FileTools.ensure_folder_exists(self.temp_path)' in handler_text
