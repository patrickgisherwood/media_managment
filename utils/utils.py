import os
import ctypes
import platform
import logging
from pathlib import Path
from datetime import datetime

# Sets up logger function
def setup_logger(name, log_filename, log_path, level=logging.DEBUG):
    formatter = logging.Formatter(fmt='%(asctime)s %(message)s', datefmt="%Y-%m-%d %H:%M:%S - ")

    log_path = os.path.join(log_path, log_filename)
    handler = logging.FileHandler(log_path, mode='a')
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger


# Function to convert timestamp to EXIF format
def get_exif_datetime(date_str):
    """
    Converts an EXIF-style datetime string ('YYYY:MM:DD HH:MM:SS')
    into a formatted datetime object or re-serialized string.
    """
    try:
        dt = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
        return dt.strftime("%Y:%m:%d %H:%M:%S")  # or return dt if you want a datetime object
    except ValueError as e:
        print(f"Date parsing error: {e}")
        return None

# converts lat/long values to DMS
def to_deg_min_sec(value):
    degrees = int(value)
    minutes = int((value - degrees) * 60)
    seconds = round(((value - degrees) * 60 - minutes) * 60 * 10000)  # Ensure seconds are rounded
    return [(degrees, 1), (minutes, 1), (seconds, 10000)]


class FileTools():
    def __init__(self):
        pass

    # Checks if filename is unique and increments filename if it already exists
    def get_unique_filename(filepath):
        """Checks if filename is unique and increments filename if it already exists"""
        base, ext = os.path.splitext(filepath)
        counter = 1
        unique_fielpath = filepath
        while os.path.exists(unique_fielpath):
            unique_fielpath = f"{base}-{counter:02d}{ext}"
            counter += 1
        return unique_fielpath

    def ensure_folder_exists(folder_path):
        """ Checks to see if folder path exists and creates it if it doesn't exits  """
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        
    def get_unique_filename(filepath):
        """
        Checks if filename is unique and increments filename if it already exists.

        Args:
            filepath (path): Filepath that will be checked to make sure it is unique. 

        Returns:
            unique_filepath (path): Output filepath that is ensured ot be unique.

        """

        base, ext = os.path.splitext(filepath)
        counter = 1
        unique_fielpath = filepath
        while os.path.exists(unique_fielpath):
            unique_fielpath = f"{base}-{counter:02d}{ext}"
            counter += 1
        return unique_fielpath
    
    def set_file_creation_date(filepath, created_timestamp):
        """
        Sets the file creation date of the <filepath> given, based on the date defined
        by <created_timestamp>.

        ########################
        filepath            ---> "C:/path/to/image.jpg"     # Filepath 
        created_timestamp   ---> 1705502668                 # Unix timestamp (int)


        """
        # Ensure created_timestamp is an integer
        if not isinstance(created_timestamp, int):
            raise ValueError(f"created_timestamp must be an integer, got {type(created_timestamp)}")

        # Set modification and access time (works on both Linux and Windows)
        os.utime(filepath, (created_timestamp, created_timestamp))

        current_os = platform.system()

        if current_os == 'Windows':
            # Windows: Set file creation time
            FILETIME_OFFSET = 116444736000000000  # Windows FILETIME epoch adjustment
            hundred_ns = int(created_timestamp * 10000000) + FILETIME_OFFSET
            ctime = ctypes.c_ulonglong(hundred_ns)

            handle = ctypes.windll.kernel32.CreateFileW(
                str(filepath), 256, 0, None, 3, 128, None
            )
            if handle != -1:
                ctypes.windll.kernel32.SetFileTime(handle, ctypes.byref(ctime), None, None)
                ctypes.windll.kernel32.CloseHandle(handle)

        elif current_os == 'Linux':
            # Linux: No native "creation time" modification, only modification/access times

            # Set modification and access times to the "created" timestamp
            os.utime(filepath, (created_timestamp, created_timestamp))

        else:
            print(f"Unsupported OS: {current_os}")

    def sort_jpg_by_year_created(directory):
        """
        Sorts .jpg files in the given directory into subfolders based on the year they were created.

        Args:
            directory (str): Path to the directory containing .jpg files.
        """
        # Ensure the directory exists
        if not os.path.exists(directory):
            raise FileNotFoundError(f"The directory '{directory}' does not exist.")

        # Get a list of all .jpg files in the directory
        jpg_files = [f for f in os.listdir(directory) if f.lower().endswith('.jpg')]

        if not jpg_files:
            print("No .jpg files found in the directory.")
            return

        for file_name in jpg_files:
            file_path = os.path.join(directory, file_name)
            
            # Get the file's creation time (epoch time)
            if os.name == 'nt':  # Windows
                creation_time = os.path.getctime(file_path)
            else:  # macOS/Linux
                # Fallback to use the last metadata change time
                stat = os.stat(file_path)
                creation_time = getattr(stat, 'st_birthtime', stat.st_mtime)

            # Convert creation time to year
            year = datetime.fromtimestamp(creation_time).year

            # Create a subdirectory for the year if it doesn't exist
            year_directory = os.path.join(directory, str(year))
            os.makedirs(year_directory, exist_ok=True)

            # Move the file into the year directory
            shutil.move(file_path, os.path.join(year_directory, file_name))

        return 1

    def is_child_of_any(dirpath, exclude_dirs):
        """
        - Checks if dirpath is a child path to any of the exclude_dirs
        - Returns True if dirpath is a childpath to any of the exclude dirs
        """
        dirpath = Path(dirpath).resolve()

        for excl_dir in exclude_dirs:
            excl_dir = Path(excl_dir).resolve()
            try:
                # Check if dirpath is inside excl_dir (or equal)
                if excl_dir == dirpath or excl_dir in dirpath.parents:
                    return True
            except RuntimeError:
                # If resolve() or parent lookup fails, just skip that excl_dir
                pass
        return False

    def count_media_files(directory, extensions):
        """ Counts number of files nested within dir that match the extension types passed"""
        count = 0
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(extensions) :
                    count += 1
        return count
