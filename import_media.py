import os
import sys
from tqdm import tqdm
from pathlib import Path
from datetime import datetime
from Image_Handler import ImgHandler
from Video_Handler import VideoHandler
from colorama import Fore, Style, init
from utils.confighandler import AppProperties
from utils.utils import setup_logger, FileTools


def main():

    # Get database path from env variable 
    DB_DIR = Path(os.environ["MEDIA_DB"])
    CONFIG_DIR = DB_DIR / ".config/properties.yaml"

    # load app properties
    app_properties = AppProperties(CONFIG_DIR)

    import_directory = input(Fore.YELLOW+"Provide Directory to import media from: "+Fore.RESET).strip()

    root_path = app_properties.get("database.directory")                        # root path of database
    archive_enabled = app_properties.get("image_handling.archive")              # archive enabled bool
    delete_after_copy = app_properties.get("image_handling.delete_after_copy")  # delete after copy enabled bool

    prevent_duplicates = app_properties.get("image_handling.duplicate_detection.prevent_duplicates")            # prevent duplicates bool
    archive_directory = app_properties.get("image_handling.trash_directory")                                    # archive/trash folder
    exclusion_directories = app_properties.get("image_handling.duplicate_detection.exclusion_directories")      # exclusion directories

    # Setup debug logger
    print(root_path)
    logger = setup_logger("history.log", "history.log", root_path)
    logger.info(f"\nStarting main.py")
    logger.info(f"Database root path: {root_path}")
    logger.info(f"Importing files from: {import_directory}")

    img_extensions = (".heic", "HEIC", ".jpg", ".JPG", ".jpeg", ".PNG")
    video_extensions = ('.MOV', '.mov', '.mp4', '.MP4')

    # Get statistics
    start_time = datetime.now()
    number_images = FileTools.count_media_files(import_directory, img_extensions)
    number_videos = FileTools.count_media_files(import_directory, video_extensions)


    print(Fore.WHITE + "\nImport Directory File Counts:"+Fore.RESET)
    print(f"{'Number of VIDEO files in Copy Directory':<40} - {number_videos}")
    print(f"{'Number of IMAGE files in Copy Directory':<40} - {number_images}")

    # init colorama 
    init(autoreset=True)

    def print_setting(name, description, value, color=Fore.CYAN):
        # Handle booleans
        if isinstance(value, bool):
            value_str = str(value)
            color = Fore.GREEN if value else Fore.RED
        else:
            value_str = str(value)
        print(f"{name:<30} - {description}")
        print(f"    {color}{value}{Style.RESET_ALL}")

    print(Fore.RESET + "\nContinue with the following settings?\n")

    print_setting("Delete after copy", "WARNING: Permanently deletes originals from import directory", delete_after_copy)
    print_setting("Enable Duplicate Detection", "Enables or disable duplicate checking when a file is imported", prevent_duplicates)
    print_setting("Archive enabled", "Archives duplicates to this folder", archive_enabled)
    print_setting("Database Root", "Path to the root database folder to import media files to", root_path)
    print_setting("Archive directory", "Directory where archives are stored when a duplicate is detected", archive_directory)
    print_setting("Exclusion directories", "Directories to exclude from duplicate checking", exclusion_directories)

    # confirm settings
    user_accepted = input (Fore.YELLOW + f"\n[yes/no]:  "+Fore.RESET)

    if user_accepted not in ("yes", "y", "YES"):
        print(Fore.RED + "Exiting")
        sys.exit(1)

    # Re-scan images user input
    for i in range(2):
        run_scan = input(Fore.YELLOW+"\nExecute hash scan on all images currently contained in the database?"+Fore.RESET +" [yes/no]:  ").strip().lower()
        if run_scan in "yes":
            scan_images = True
            break
        elif run_scan == "no":
            scan_images = False
            break
        else:
            print("Invalid input. Please type 'yes' or 'no'.")
    else:
        print("Too many invalid attempts. Exiting.")
        exit()        

    # Setup image handler based on app properties
    image_handler = ImgHandler(logger, app_properties.filepath)
    image_handler.prevent_duplicates(prevent_duplicates, exclusion_directories)
    image_handler.archive_path(archive_directory, archive_enabled)
    if scan_images:
        logger.info(f"Scanning images and updating database")
        image_handler.update_db(root_path)

    os.makedirs(os.path.join(root_path, "tmp"), exist_ok=True)       # Ensure tmp output directory exists (directory that ProcessImage.heic_to_jpg uses to temp save files to)
    max_copy_attempts = 10

    
    # confirm settings
    for i in range(2):
        user_accepted = input(f"\nContinue with the transfer? [yes/no]:  ")
        if user_accepted == "yes": 
            break
        elif i == 3:
            print("Invalid input. Exiting")
            exit()

    number_images_processed = 0
    number_videos_processed = 0
    num_images_failed = 0
    num_videos_failed = 0 

    print(f"Starting transfer. \n")
    logger.info("Starting Transfer")

    # 1️⃣ Collect all files to process
    all_files = []
    for root, dirs, files in os.walk(import_directory):
        for file in files:
            if file.endswith(img_extensions) or file.endswith(video_extensions):
                all_files.append(os.path.join(root, file))

    # image processing
    for file in tqdm(all_files, desc="Importing Images", unit="file"):
        if file.endswith(img_extensions):
            for attempt in range(1, max_copy_attempts+1):
                try:
                    image_handler.process_img(file)
                    number_images_processed += 1
                    break     # success

                except Exception as e:
                    if attempt == max_copy_attempts:
                        logger.info(f"Failed processing Image: [{file}]")
                        num_images_failed += 1
                        break                            

        elif file.endswith(video_extensions):                                   # video processing
            for attempt in range(1, max_copy_attempts):
                try:
                    video = VideoHandler(file_path, root_path, logger, remove_files=False)
                    video.run()
                    number_videos_processed += 1
                    break  # success

                except Exception as e:
                    if attempt == max_copy_attempts:
                        logger.info(f"Failed processing Video [{file}]")
                        num_videos_failed += 1
                        break

    logger.info("Transfer Complete!!")
    print(f"\nTransfer Complete!!")

    endtime = datetime.now()
    elapsed_time = endtime - start_time

    # Convert timedelta to HH:MM:SS
    seconds = int(elapsed_time.total_seconds())
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    print(f"Elapsed Runtime: {hours:02}:{minutes:02}:{seconds:02}")

    print("Total Image files processed", number_images_processed)
    print("Total Video files processed", number_videos_processed)

    print(f"\nFailed Meda Files:")
    print(f"    failed Image files: {num_images_failed}")
    print(f"    failed Video files: {num_videos_failed}")


main()
