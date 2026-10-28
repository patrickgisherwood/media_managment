import json
import os
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
preferred = [
    str(SRC_DIR),
    str(SRC_DIR / "handlers"),
    str(SRC_DIR / "core"),
    str(SRC_DIR / "utils"),
    str(ROOT),
]
filtered = [p for p in sys.path if p not in preferred]
sys.path[:] = preferred + filtered

from Video_Handler import VideoHandler


def test_video_uses_date_based_name_and_preserves_original_extension(tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"fake video data")

    video = VideoHandler(str(source), str(tmp_path / "library"), logger=None, remove_files=True)
    video.datetime_taken = "2024:05:07 18:30:15"
    video.metadata = False
    video.filepath_orig = str(source)
    video.get_output_filepath()

    assert os.path.basename(video.output_filepath).startswith("20240507_183015")
    assert os.path.basename(video.output_filepath).endswith(".mp4")


def test_video_copy_keeps_original_and_json_files_when_not_opted_in(tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source = source_dir / "clip.mp4"
    source.write_bytes(b"fake video data")
    source_json = source_dir / "clip.json"
    source_json.write_text(json.dumps({"photoTakenTime": {"timestamp": "1715083815"}}))

    output_dir = tmp_path / "library"
    output_dir.mkdir()

    video = VideoHandler(str(source), str(output_dir), logger=None, remove_files=False)
    video.datetime_taken = "2024:05:07 18:30:15"
    video.metadata = {"photoTakenTime": {"timestamp": "1715083815"}}
    video.json_path = str(source_json)
    video.json_exists = True
    video.output_filepath = str(output_dir / "20240507_183015.mp4")

    video.save_video()
    video.save_json()

    assert source.exists()
    assert source_json.exists()
    assert os.path.exists(video.output_filepath)


def test_video_original_and_json_can_be_deleted_when_explicitly_opted_in(tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source = source_dir / "clip.mp4"
    source.write_bytes(b"fake video data")
    source_json = source_dir / "clip.json"
    source_json.write_text(json.dumps({"photoTakenTime": {"timestamp": "1715083815"}}))

    output_dir = tmp_path / "library"
    output_dir.mkdir()

    video = VideoHandler(str(source), str(output_dir), logger=None, remove_files=True)
    video.datetime_taken = "2024:05:07 18:30:15"
    video.metadata = {"photoTakenTime": {"timestamp": "1715083815"}}
    video.json_path = str(source_json)
    video.json_exists = True
    video.output_filepath = str(output_dir / "20240507_183015.mp4")

    video.save_video()
    video.save_json()

    assert not source.exists()
    assert not source_json.exists()
    assert os.path.exists(video.output_filepath)


def test_image_original_is_not_deleted_by_default(tmp_path):
    source = tmp_path / "photo.jpg"
    image = Image.new("RGB", (10, 10), "red")
    image.save(source)

    handler = object.__new__(__import__("Image_Handler").ImgHandler)
    handler.filepath = str(source)
    handler.filepath_orig = str(source)
    handler.output_dir_root = str(tmp_path)
    handler.file_output_dir = str(tmp_path)
    handler.delete_orig_file = False
    handler.logger = None
    handler.json_exists = False
    handler.loaded_img = image
    handler.tmp_file_exists = False
    handler._prevent_duplicates_enabled = False
    handler.datetime_taken = "2024:05:07 18:30:15"

    target = tmp_path / "exported.jpg"
    handler.save_image(None, str(target))

    assert source.exists()
    assert target.exists()


def test_image_original_can_be_deleted_when_explicitly_opted_in(tmp_path):
    source = tmp_path / "photo.jpg"
    image = Image.new("RGB", (10, 10), "red")
    image.save(source)

    handler = object.__new__(__import__("Image_Handler").ImgHandler)
    handler.filepath = str(source)
    handler.filepath_orig = str(source)
    handler.output_dir_root = str(tmp_path)
    handler.file_output_dir = str(tmp_path)
    handler.delete_orig_file = True
    handler.logger = None
    handler.json_exists = False
    handler.loaded_img = image
    handler.tmp_file_exists = False
    handler._prevent_duplicates_enabled = False
    handler.datetime_taken = "2024:05:07 18:30:15"

    target = tmp_path / "exported.jpg"
    handler.save_image(None, str(target))

    assert not source.exists()
    assert target.exists()
