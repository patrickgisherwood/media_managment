import os
import json
import shutil
from PIL import Image
from datetime import datetime

parent_directory = r"Z:\Vault\Pictures\All Photos\2013"
output_directory = r"Z:\Vault\Pictures\All Photos\2013\pic-managment-out"

def apply_metadata_to_image(image_path, metadata, save_directory, json_path):
    # Get date and time for renaming from metadata
    date_taken = metadata.get("photoTakenTime", {}).get("timestamp")
    if date_taken:
        # Convert timestamp to datetime
        date_time = datetime.utcfromtimestamp(int(date_taken))
        date_str = date_time.strftime("%Y%m%d_%H%M%S")
    else:
        # Default name if timestamp is missing
        date_str = "unknown_date"

    # Base filename with date and time
    base_filename = f"{date_str}.jpg"
    original_name = os.path.basename(image_path)

    # Check if the file already starts with a date
    if not original_name.startswith(date_str[:8]):
        # Ensure unique filename if it exists in the save directory
        unique_filename = get_unique_filename(os.path.join(save_directory, base_filename))
    else:
        unique_filename = original_name

    # New save path with unique name
    new_image_path = os.path.join(save_directory, unique_filename)

    # Copy image and save with metadata
    with Image.open(image_path) as img:
        img.info['Description'] = metadata.get('description', '')

        img.save(new_image_path)
        print(f"Saved {new_image_path} with applied metadata.")


    # Define unique name and path for JSON file copy
    json_filename = os.path.basename(unique_filename.replace(".jpg", ".json"))
    json_save_directory = os.path.join(save_directory, "_json")
    json_copy_path = os.path.join(json_save_directory, json_filename)

    # Copy JSON file to _json directory
    shutil.copy(json_path, json_copy_path)
    print(f"Copied JSON from {json_path} to {json_copy_path}")

def get_unique_filename(filepath):
    """Increment filename if it already exists."""
    base, ext = os.path.splitext(filepath)
    counter = 1
    unique_filepath = filepath
    while os.path.exists(unique_filepath):
        unique_filepath = f"{base}-{counter:02d}{ext}"
        counter += 1
    return unique_filepath

def find_and_process_images(parent_directory, save_directory):
    # Ensure save directory exists
    os.makedirs(save_directory, exist_ok=True)
    # Ensure _json directory exists
    os.makedirs(os.path.join(save_directory, "_json"), exist_ok=True)

    for root, dirs, files in os.walk(parent_directory):
        print('heree - 1 ')
        for file in files:
            if file.endswith(".jpg"):
                print('here -2 ')
                jpg_path = os.path.join(root, file)
               
                json_path = file.replace(".jpg", "json")        # get correspoding json file

                # Check if corresponding .jpg file exists and load JSON metadata
                if os.path.exists(json_path):
                    
                    print(json_path)
                    with open(json_path, 'r') as json_file:         # open jsonfile
                        metadata = json.load(json_file)             # extract json meta data

                    # Apply metadata to the image and save it to a new directory with unique naming
                    apply_metadata_to_image(jpg_path, metadata, save_directory, json_path)
                
                # Copy over to new dir without any meta data updates
                else:
                    new_image_path = os.path.join(output_directory, os.path.basename(jpg_path))
                    print(new_image_path)

                    with Image.open(jpg_path) as img:
                        img.save(new_image_path)
                        print(f"Saved {new_image_path} with no metadata applied.")
                    

# Replace with the paths to your parent directory and output directory
find_and_process_images(parent_directory, output_directory)
