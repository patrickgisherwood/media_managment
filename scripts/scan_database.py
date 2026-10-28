
import os
import sys
import threading
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
for candidate in [
    str(ROOT_DIR),
    str(SRC_DIR),
    str(SRC_DIR / "handlers"),
    str(SRC_DIR / "core"),
]:
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from tqdm import tqdm
from handlers.Image_Handler import ImgHandler
from utils.confighandler import AppProperties
from utils.utils import setup_logger


def format_duration(elapsed_seconds):
    total_seconds = int(elapsed_seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def report_elapsed_time(stop_event, start_time, logger):
    while not stop_event.wait(60):
        elapsed = format_duration(time.monotonic() - start_time)
        message = f"Database scan is still running. Elapsed time: {elapsed}"
        logger.info(message)
        tqdm.write(message)


def main():
    media_db = os.environ.get("MEDIA_DB")
    if not media_db:
        print(
            "MEDIA_DB is not set. Source /etc/profile.d/media_db.sh or export MEDIA_DB first.",
            file=sys.stderr,
        )
        return 1

    db_root = Path(media_db).expanduser().resolve()
    properties_path = db_root / ".config" / "properties.yaml"
    if not db_root.is_dir():
        print(f"Database directory does not exist: {db_root}", file=sys.stderr)
        return 1
    if not properties_path.is_file():
        print(f"Database properties file does not exist: {properties_path}", file=sys.stderr)
        return 1

    app_properties = AppProperties(str(properties_path))
    if app_properties.get("database.directory") != str(db_root):
        app_properties.set("database.directory", str(db_root))
        app_properties.set("database.db_path", str(db_root / "media.db"))
        app_properties.set("database.temp_path", str(db_root / ".tmp"))
        app_properties.set("image_handling.unsorted_images", str(db_root / "unsorted"))
        app_properties.set("image_handling.trash_directory", str(db_root / ".archive"))
        app_properties.set(
            "image_handling.duplicate_detection.exclusion_directories",
            [str(db_root / "unsorted"), str(db_root / ".archive")],
        )
        app_properties.save()

    temp_path = str(db_root / ".tmp")
    if app_properties.get("database.temp_path") != temp_path:
        app_properties.set("database.temp_path", temp_path)
        app_properties.save()
    temp_path_obj = db_root / ".tmp"
    temp_path_obj.mkdir(parents=True, exist_ok=True)

    logger = setup_logger("database_scan", "database_scan.log", str(db_root))
    warning = (
        "\nThis will scan every eligible image in the selected database and update "
        "the image hash database.\n"
        "Depending on the number and size of images and the Raspberry Pi's storage "
        "and CPU, this can take multiple hours.\n"
        "The progress display includes elapsed time; periodic elapsed-time updates "
        "will also be written to the log."
    )
    print(warning)
    logger.info("Database hash scan confirmation requested for %s", db_root)

    confirmation = input("\nStart the database scan? [yes/no]: ").strip().casefold()
    if confirmation not in ("yes", "y"):
        logger.info("Database hash scan cancelled by user")
        print("Database scan cancelled.")
        return 0

    exclusion_directories = app_properties.get(
        "image_handling.duplicate_detection.exclusion_directories", []
    )
    start_time = time.monotonic()
    stop_timer = threading.Event()
    timer_thread = threading.Thread(
        target=report_elapsed_time,
        args=(stop_timer, start_time, logger),
        daemon=True,
    )

    logger.info("Starting database hash scan for %s", db_root)
    print(f"\nStarting database scan. Log: {db_root / 'database_scan.log'}")
    timer_thread.start()
    try:
        image_handler = ImgHandler(logger, app_properties.filepath)
        image_handler.prevent_duplicates(True, exclusion_directories)
        image_handler.update_db(str(db_root))
    except Exception:
        elapsed = format_duration(time.monotonic() - start_time)
        logger.exception("Database hash scan failed after %s", elapsed)
        print(f"Database scan failed after {elapsed}. See the log for details.", file=sys.stderr)
        return 1
    finally:
        stop_timer.set()
        timer_thread.join()

    elapsed = format_duration(time.monotonic() - start_time)
    logger.info("Database hash scan completed in %s", elapsed)
    print(f"Database scan completed. Total elapsed time: {elapsed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())