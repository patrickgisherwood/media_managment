import os
import sys
from utils.utils import setup_logger
from colorama import Fore, Style, init
from Image_Handler import ImgHandler
from utils.confighandler import AppProperties


def main():
    app_properties = AppProperties(r"C:\_Transfer\repos\home-lab\config\properties.yaml")

    root_path = app_properties.get("database.directory")                        # root path of database
    archive_enabled = app_properties.get("image_handling.archive")              # archive enabled bool
    delete_after_copy = app_properties.get("image_handling.delete_after_copy")  # delete after copy enabled bool

    prevent_duplicates = app_properties.get("image_handling.duplicate_detection.prevent_duplicates")            # prevent duplicates bool
    archive_directory = app_properties.get("image_handling.trash_directory")                                    # archive/trash folder
    exclusion_directories = app_properties.get("image_handling.duplicate_detection.exclusion_directories")      # exclusion directories

    # Setup debug logger
    logger = setup_logger("history.log", "history.log", root_path)
    logger.info(f"setup.py - Setting up database.  Note - will not interfere with existing db. ")
    logger.info(f"Database root path: {root_path}")

    # init colorama
    init(autoreset=True)

    def print_setting(name, description, value, color=Fore.CYAN):
        print(f"{name:<30} - {description}")
        print(f"    {color}{value}{Style.RESET_ALL}")

    print(Fore.YELLOW + "\nContinue with the following settings?\n")

    print_setting("Database Root", "Path to the root database folder to import media files to", root_path)
    print_setting("Delete after copy", "WARNING: Permanently deletes originals from import directory", delete_after_copy, Fore.RED)
    print_setting("Enable Duplicate Detection", "Enables or disable duplicate checking when a file is imported", prevent_duplicates)
    print_setting("Archive enabled", "Archives duplicates to this folder", archive_enabled, Fore.GREEN)
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

    os.makedirs(os.path.join(root_path, ".tmp"), exist_ok=True)       # Ensure tmp output directory exists (directory that ProcessImage.heic_to_jpg uses to temp save files to)


main()
