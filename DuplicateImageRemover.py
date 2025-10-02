import os
import ctypes
import shutil
import imagehash
from PIL import Image
from utils.utils import setup_logger
from collections import defaultdict
from utils.utils import FileTools
from utils.media_db import FileHashDB
from colorama import Fore, Style, init
from tqdm import tqdm


"""
Currently scan images will exclude any exclusion directories set by self.exclusion_directories, but if the the scan_image method 
"""

class DuplicateImageRemover:
    def __init__(self, root_dir, logger, extensions=(".jpg", ".jpeg", ".JPG", ".JPEG")):
        self.root_dir = root_dir
        self.extensions = extensions
        self.images_by_size = defaultdict(list)
        self.seen_hashes = {}
        self.duplicates = []
        self.exclude_directories = []

        self.logger = logger
        self.logger.info("TEST TEST TEST")

    def load_image_hash_db(self, path):
        self.logger.info(f"Loading hash database: {path}")
        self.img_hash_db = FileHashDB(path)

        if os.path.isfile(path):
            print("Media database loaded")
        else:
            print(f"\nWARNING - No Database file found at {path}")
            self.logger.info(f"WARNING -Database doesn't exist: {path}")
            for i in range(2):
                create_db_input = input(f"Create new media.db [yes/no]? ")
                if create_db_input == "yes":
                    media_db = FileHashDB()
                    media_db._init_db()
                    if os.path.isfile(path):
                        print(f"Database created Succesfully\n")
                        self.logger.info("Database created Succesfully")

                        break
                    else:
                        print(f"Failed to create database")
                        self.logger.info(f"Failed to create database")
                elif i == 3:
                    print("Invalid input. Exiting")
                    self.logger.info("Invalid input given when prompting for database creation.  Exiting")
                    exit()
                else:
                    print("invalid Input.  Input 'yes' to continue")

        self.img_hash_db._init_db()

    def get_image_hash(self, path, logger=None, hash_obj=False):
        """
        Load image and return hash based on pixel content (ignores metadata).
        """

        hash = self.img_hash_db.get_hash(path)

        if hash is None:
            try:
                with Image.open(path) as img:
                    # Convert to a fixed format so compression artifacts don’t alter the hash
                    img = img.convert("RGB")  # ensure consistent color mode
                    img = img.resize((256, 256), Image.LANCZOS)  # fixed size normalization

                    if hash is True:
                        return imagehash.phash(img)             # return hash object
                    else:
                        return str(imagehash.phash(img))        # return hash string (default)

            except Exception as e:
                message = f"Failed to get image hash for {path}: {e}"
                if logger is not None:
                    logger.info(message)
                else:
                    print(message)
                return None
        else:
            return hash

    def exclude_dir(self, exlusion_dir, enable=True):
        """
        - Takes in a single directory or a list of directories and excludes them from the search.
        - Must be the full path from self.root_dir
        """

        if isinstance(exlusion_dir, str):
            # Single directory path
            full_path = os.path.join(self.root_dir, exlusion_dir)
            self.exclude_directories.append(full_path)
        elif isinstance(exlusion_dir, list):
            # List of directories
            for d in exlusion_dir:
                full_path = os.path.join(self.root_dir, d)
                self.exclude_directories.append(full_path)
        else:
            raise TypeError("new_dirs must be a string or a list of strings")

    def get_size_on_disk(self, path):
        """Returns the size on disk in bytes (Windows only).  Currently didn't lead to any more duplicates being removed"""
        if not os.path.exists(path):
            return 0
        GetCompressedFileSizeW = ctypes.windll.kernel32.GetCompressedFileSizeW
        GetCompressedFileSizeW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_ulong)]
        GetCompressedFileSizeW.restype = ctypes.c_ulong

        high = ctypes.c_ulong(0)
        low = GetCompressedFileSizeW(path, ctypes.byref(high))
        return (high.value << 32) + low

    def scan_images(self, dir):
        self.logger.info("Scanning images")

        # Collect all files to scan
        all_files = []
        duplicate_count = 0
        for dirpath, _, files in os.walk(dir):
            if FileTools.is_child_of_any(dirpath, self.exclude_directories):
                self.logger.info(f"Exclusion Directory. Skipping {dirpath}")
                continue
            all_files.extend([os.path.join(dirpath, f) for f in files if f.endswith(self.extensions)])

        print(Fore.MAGENTA + f"\nScanning {len(all_files)} images")
        # Global progress bar
        for file_path in tqdm(all_files, desc="Scanning Images", unit="file"):
            duplicate = self.check_image(file_path)
            if duplicate:
                duplicate_count += 1
        print(Fore.MAGENTA + f"\nScan Complete."+Fore.CYAN+f"{duplicate_count} Duplicates detected\n")

    def check_image(self, image_path):
        """
        - Check if a single image is a duplicate based on its hash.
        - Adds image to db if no duplicate hash is found
        - Skips of folderpath is listed in self.exclusion_directories

        """
        base_filepath = os.path.dirname(image_path)
        exclusion_dir_check = FileTools.is_child_of_any(base_filepath, self. exclude_directories)

        if exclusion_dir_check is False:
            img_hash = self.get_image_hash(image_path, self.logger)
            if img_hash is None:
                self.logger.info(f"[ERROR] Image hash returned: None {image_path}")
                return False  # can't hash, treat as not a duplicate

            if self.img_hash_db.hash_exists(img_hash):
                # Already seen → duplicate
                self.duplicates.append(image_path)
                return True
            else:
                # Not seen yet → add to database
                self.img_hash_db.add_file(image_path, img_hash) 
                return False

    def delete_duplicates(self):
        """Delete or archive all detected duplicate files."""
        self.logger.info(f"Deleting {len(self.duplicates)} duplicate images...")

        for path in self.duplicates:
            try:
                if getattr(self, 'archive', False) and getattr(self, 'archive_path', None):

                    # Move the file to the archive directory
                    filename = os.path.basename(path)
                    archived_path = os.path.join(self.archive_path, filename)

                    self.logger.info(f"Archiving: {path} -> {archived_path}")
                    shutil.move(path, archived_path)
                else:
                    # Directly delete the file
                    os.remove(path)
                    self.logger.info(f"Deleted: {path}")

            except Exception as e:
                self.logger.info(f"Failed to process {path}: {e}")

    def archive(self, archive_path=None, archive=True):
        self.archive = archive
        self.archive_path = archive_path
        FileTools.ensure_folder_exists(self.archive_path)       # Ensure the archive directory exists

    def run(self, delete=False):
        """Run the full scan and optionally delete duplicates."""
        self.scan_images()
        #self.find_duplicates()
        if delete:
            self.delete_duplicates()
        else:
            self.logger.info("Duplicates found:")
            for dup in self.duplicates:
                self.logger.info(dup)


if __name__ == "__main__":
    dir_path = r"C:\Users\patri\Desktop\Photo_MetaData_Test\output\2024"
    archive_path = r"C:\Users\patri\Desktop\Photo_MetaData_Test\archive"

    # initilize objects
    logger = setup_logger("DuplicateImageRemover", "DuplicateImageRemover.log", r"C:\Users\patri\Desktop\Photo_MetaData_Test\output")
    logger.info("Starting DuplicateImageRemover.py")

    remover = DuplicateImageRemover(dir_path, logger)
    remover.archive(archive_path=archive_path)
    remover.run(delete=True)  # Set to False to preview duplicates