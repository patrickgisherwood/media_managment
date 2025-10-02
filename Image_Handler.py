import os
import json
import shutil
import piexif
import traceback        # only for debugging of traceback.  Possibly remove?
from utils.utils import FileTools, get_exif_datetime
from utils.confighandler import AppProperties
from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime
import pillow_heif
from pillow_heif import register_heif_opener
from DuplicateImageRemover import DuplicateImageRemover
from utils.confighandler import AppProperties


class ImgHandler:
    def __init__(self, logger, app_properties_filepath):
        

        # initilize configurabel settings
        self.datetime_taken = None                                  # initialize to a default value
        self.tmp_file_exists = False                                # initilize as false
        self._prevent_duplicates_enabled = False                    # initilize as false

        self.app_properties = AppProperties(app_properties_filepath)

        self.output_dir_root = self.app_properties.get("database.directory")
        self.delete_orig_file = self.app_properties.get("image_handling.delete_after_copy")
        self.temp_path = self.app_properties.get("database.temp_path")

        # initilize objects
        self.logger = logger
        self.duplicateTracker = DuplicateImageRemover(self.output_dir_root, self.logger)
        self.duplicateTracker.load_image_hash_db(self.app_properties.get("database.db_path") )
        self.duplicateTracker.exclude_dir(os.path.join(self.output_dir_root, "unsorted"))      # Exclude unsorted from duplicate tracker (if its enabled)

        # ensure unsorted filepath exists
        FileTools.ensure_folder_exists(os.path.join(self.output_dir_root, "unsorted"))          # ensure the output directory exists

    def process_img(self, filepath):
        """
        Currently, due to handling of HEIC images, the json needs to be loaded prior to the heic
        to jpg conversion since self.heic_to_jpg sets a new filename based on the new saved jpg file.
        """
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.extension = os.path.splitext(self.filename)[1]
        self.file_output_dir = self.output_dir_root         # Reset output directory
        self.json_exists = False                            # reset json exists flag

        self.load_image_json()                              # Load .json data if it exists

        # If heic, convert it to a jpg for processing
        if self.extension.endswith((".heic", "HEIC")):
            
            exif_data = self.extract_heic_metadata()                    # extract .heic metadata
            self.heic_to_jpg()                              # convert image to jpg
            self.loaded_img = Image.open(self.filepath)     # load the new jpg image

        else:  
            self.loaded_img = Image.open(self.filepath)     # load the image
            exif_data = self.extract_jpg_metadata()         # Extract metadata
            self.filepath_orig = self.filepath              # stupid variable needed because of self.heic_to_jpg saves a temp file and needs to update self.filepath

        # Output file to new directory with metadata
        output_path = self.get_output_filepath()            # Determine output name of image
        self.save_image(exif_data, output_path)             # Save image to new filepath with metadata
        self.save_json(output_path)                         # Save json to new filepath

    def update_db(self, dir):
        """ Scans and updates DB for all files contained within path"""
        self.duplicateTracker.scan_images(dir)

    def load_image_json(self):

        # Handle json file naming conventions
        json_path_1 = self.filepath.replace(self.extension, ".json")
        json_path_2 = self.filepath + ".json"

        if os.path.exists(json_path_1):
            self.json_path = json_path_1    
            self.json_exists = True
        elif os.path.exists(json_path_2):
            self.json_path = json_path_2
            self.json_exists = True
        else:
            self.json_exists = False

        # Process JSON metadata
        if self.json_exists == True:
            with open(self.json_path, 'r') as json_file:
                self.metadata = json.load(json_file)
        else:
            self.metadata = False                               # Creates an empty JSON object

    def prevent_duplicates(self, enable=True, exclude_directories=None):
        """
        - Enable or disable duplicate checks
        - Allows for directories to skip looking for duplicates to be set with exclude_directories (list or single dir works)
        - Allows for a trash 
        """

        self._prevent_duplicates_enabled = enable
        #sif self._prevent_duplicates_enabled is True:
            #self.duplicateTracker.run(delete=False)             # run but don't delete any immediate duplicates
        
        self.logger.info(f"Adding exclusion directory: {exclude_directories}")

        if exclude_directories is not None:
            self.logger.info(f"Adding exclusion directory: {exclude_directories}")
            self.duplicateTracker.exclude_dir(exclude_directories)

    def archive_path(self, archive_path=None, enable=True):
        """
        - Enables / disables archive mode to archive duplicate images
        - Sets directory to archive files to when a duplicate is fond
        """
        if enable is False:
            self.duplicateTracker.archive_path(enable=False)
        if archive_path is not None: 
            self.duplicateTracker.archive(archive_path, archive=True)
        else:
            self.logger.info(f"Archive path can't be None!!")

    def heic_to_jpg(self):
        """
        Converts heic images to a .jpg and saves the file to the original containing folder for processing.

        Args:
            self

        Attributes:
            self.filepath (path): Replaces filepath with new .jpg filepath
            self.filename (path): Replaces filename with new .jgp filename

        """
        # Register HEIF support with Pillow (handles .heic and .heif)
        pillow_heif.register_heif_opener()

        try:
            with Image.open(self.filepath) as image:                            # Open the .HEIC file
                jpg_path = os.path.join(self.file_output_dir, ".tmp", self.filename.replace(self.extension, ".jpg"))    # create tmp filepath
                jpg_path = FileTools.get_unique_filename(jpg_path)                                                     # ensure this is a unique filename
                image.save(jpg_path, "jpeg")                                                                            # Save the new .jpg file
                self.filepath_orig = self.filepath                                                                      # save original filepath for deletion of og image
                self.filepath = jpg_path                                                                                # set new filepath
                self.filename = os.path.basename(jpg_path)                                              # set new filename

                self.tmp_file_exists = True

        except Exception as e:
            # Print the error message and the full traceback
            self.logger.info(f"Error converting {self.filepath} to JPEG: {e}")
            self.logger.info("Full traceback:")
            self.logger.info(traceback.format_exc())  # Prints the full traceback

            self.logger.info(f"Error converting {self.filepath} to JPEG: {e}")

    def extract_jpg_metadata(self):
        """
        Extracts metadat contgained in self.metadata to EXIF .

        Args:
            self

        Attributes:
            self.exif_data (str): Images metadata formated in exif
            self.datetime_taken (str): datetime the image was taken
        """

        exif_new = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

        exif_orig = self.loaded_img._getexif()
        if exif_orig:
            for tag_id, value in exif_orig.items():
                tag_name = TAGS.get(tag_id, tag_id)     # Get human-readable tag name
                if tag_name == "DateTimeOriginal":      # "Date Taken" metadata
                    self.datetime_taken = value

                    try:
                        date_time_original = get_exif_datetime(self.datetime_taken)
                        exif_new['Exif'][piexif.ExifIFD.DateTimeOriginal] = date_time_original.encode('utf-8')
                        return exif_new
                    except Exception as e:
                        self.logger.info(f"ERROR setting DateTimeOriginal: while processing {self.filepath_orig}")
                        self.logger(f"ERROR Traceback: {e}")

        else:
            pass

        # Unsure if any of the following is working, commenting out for now.  This is supposed to be
        # extracting metadata, but uses a different method then what is used above.
        """# Load exif data via pillow for processing 
        exif_data = piexif.load(self.loaded_img.info.get('exif', b"")) if 'exif' in self.loaded_img.info else {'0th': {}, 'Exif': {}, 'GPS': {}}

        if self.metadata == False:              # if no metadata exists, exit
            return

        if 'thumbnail' in exif_data:            # Remove the thumbnail from EXIF data
            exif_data.pop('thumbnail')
        
        if 'description' in self.metadata:      # Title and description
            exif_data['0th'][piexif.ImageIFD.ImageDescription] = self.metadata['description'].encode('utf-8')

        # Dates
        #self.datetime_taken = self.metadata.get('photoTakenTime', {}).get('timestamp')

        datetime_created = self.metadata.get('creationTime', {}).get('timestamp')

        if datetime_created:
            try:
                date_time_digitized = get_exif_datetime(datetime_created)
                exif_data['Exif'][piexif.ExifIFD.DateTimeDigitized] = date_time_digitized.encode('utf-8')
            except Exception as e:
                print(f"Error setting DateTimeDigitized: {e}")

        # GPS Data
        geo_data = self.metadata.get("geoData", {})
        if "latitude" in geo_data and "longitude" in geo_data:
            try:
                exif_data['GPS'][piexif.GPSIFD.GPSLatitude] = to_deg_min_sec(geo_data["latitude"])
                exif_data['GPS'][piexif.GPSIFD.GPSLatitudeRef] = b'N' if geo_data["latitude"] >= 0 else b'S'
                exif_data['GPS'][piexif.GPSIFD.GPSLongitude] = to_deg_min_sec(geo_data["longitude"])
                exif_data['GPS'][piexif.GPSIFD.GPSLongitudeRef] = b'E' if geo_data["longitude"] >= 0 else b'W'
            except Exception as e:
                print(f"Error setting GPS data: {e}")
                self.logger.info(f"Error setting GPS data: {e}")

        ## Fix any possible invalid data in metadata
        # Fix GPS Longitude (remove negative values)
        if 4 in exif_data["GPS"]:
            exif_data["GPS"][4] = [(abs(coord[0]), coord[1]) for coord in exif_data["GPS"][4]]

        # Fix GPS Latitude (convert list to tuple)
        if 2 in exif_data["GPS"]:
            exif_data["GPS"][2] = tuple(exif_data["GPS"][2])


        # Remove "1st" section if it exists
        if "1st" in exif_data:
            del exif_data["1st"]

        self.exif_data = exif_data"""

        return None

    def extract_heic_metadata(self):
        register_heif_opener()
        img = Image.open(self.filepath)         # load image.  Not saved to self.loaded_img since its the temp .heic file

        exif_old = img.getexif()
        exif_new = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

        if exif_old:
            self.datetime_taken = exif_old.get(306)  # 36867 = DateTimeOriginal
            if self.datetime_taken:
                try:
                    date_time_original = get_exif_datetime(self.datetime_taken)
                    exif_new['Exif'][piexif.ExifIFD.DateTimeOriginal] = date_time_original.encode('utf-8')
                    return exif_new
                except Exception as e:
                    self.logger.info(f"Error extracintng heic metadata: {e}")  

        return None

    def get_output_filepath(self):
        """
        Determines filepath that the image will be copied to.

        Args:
            self

        Attributes:
            output_filepath (path): Output path that the image will get saved to.

        """

        dt = None

        # Uses self.datetime_taken as date stamp for filename, and looks through metadata for datetime_original if non existant
        if self.datetime_taken:
            # Format the datestamp for the image name
            dt = datetime.strptime(self.datetime_taken, "%Y:%m:%d %H:%M:%S")

        elif self.metadata != False:    # look for datetime_original
            # Format the datestamp for the image name
            timestamp = int(self.metadata["photoTakenTime"]["timestamp"])
            dt = datetime.utcfromtimestamp(timestamp)  # Use utcfromtimestamp if it's in UTC

        # If dt is defined, datetime metadata exists for the image
        if dt:
            formatted_date = dt.strftime("%Y%m%d_%H%M%S")
            folder_year = formatted_date[:4] 
            self.file_output_dir = os.path.join(self.output_dir_root, folder_year)            # Modify file_output_dir to include year folder
            FileTools.ensure_folder_exists(self.file_output_dir)                               # ensure the output directory exists

            if not self.filename.startswith(formatted_date[:8]):                                # Check if the filename already starts with the correct date string
                base_filename = f"{formatted_date}.jpg"                                         # get new base_filename based on date string
            else:                                                                               # filename already starts with correct date string
                base_filename = self.filename
            output_filepath = FileTools.get_unique_filename(os.path.join(self.file_output_dir, base_filename))    # ensure unique file path

        # If datetime taken metadata doesn't exist, save to "unsorted" folder
        else:                                                                           # no date meta data for .jpg
            self.file_output_dir = os.path.join(self.output_dir_root, "unsorted")
            output_filepath = self.filepath.replace(self.extension, ".jpg")             # keep original name and ensure .jpg file extnsion
            output_filepath = FileTools.get_unique_filename(os.path.join(self.file_output_dir, self.filename))     # ensure unique name
            self.logger.info(f"Saving to unsorted path: {output_filepath}")

        return output_filepath

    def save_image(self, exif_data, output_filepath):
        """
        - Checks if self.prevent_duplicate==True, and checks if img will be a duplicate if its enabled
        """
 
        # Check image for duplicates
        try:
            if self._prevent_duplicates_enabled is True:
                duplicate_detected = self.duplicateTracker.check_image(self.filepath)
                if duplicate_detected is True:
                    self.file_output_dir = self.duplicateTracker.archive_path
                    output_filepath = os.path.join(self.file_output_dir, os.path.basename(output_filepath))      # set output dir to archive
        except Exception as e:
            print(f"Error porcessing duplcate detection for {output_filepath}: {e}")
            self.logger.info(f"error porcessing duplcate detection for output filepath {output_filepath}: {e}")
            self.logger.info(f"Original IMG path that caused error: {self.filepath}")

        # Save the image 
        if self.json_exists is True:                                # if json exists, apply metadata as new image is saved
            exif_bytes = piexif.dump(exif_data)                     # Convert exif data into byte stream so it can be embeded into image
            self.loaded_img.save(output_filepath, "jpeg", exif=exif_bytes)
            self.loaded_img.close()
        else:                                                       # if no metadata, save without
            self.loaded_img.save(output_filepath, "jpeg")
            self.loaded_img.close()

        # Set date created once the image is saved
        try:
            if self.datetime_taken:
                dt = datetime.strptime(self.datetime_taken, "%Y:%m:%d %H:%M:%S")
                dt = int(dt.timestamp())                      # Get datetime taken if it exists
                FileTools.set_file_creation_date(output_filepath, dt)     # Set file date created time

        except Exception as e:
            print(f"Failed to save EXIF data for {output_filepath}: {e}")
            self.logger.info(f"ERROR Failed to save EXIF data for {output_filepath}: {e}")
            self.logger.info(f"Original IMG path that caused error: {self.filepath}")

        # Delete the original file
        if os.path.exists(output_filepath):                        # confirm the file saved file actually exists
            file_size = os.path.getsize(output_filepath)           # confirm the saved file has a filsize 
            if file_size > 250 and self.delete_orig_file == True:       # check that file size is > 500 bytes
                try: 
                    os.remove(self.filepath_orig)                           # Delete the original file if the copy was succesfull 
                except FileNotFoundError as e:
                    print(f"FileNotFoundError caught: {e}")
                    self.logger.info(f"FileNotFoundError caught: {e}")
            elif self.delete_orig_file == True:
                self.image_saved = False
                self.logger.info(f"File size too small. Failed to save image [{self.filepath}] to output directory [{output_filepath}]")
                self.logger.info(f"File size: {file_size}")

        # Delete the tmp file if it exists
        try:
            if self.tmp_file_exists == True:
                file_size = os.path.getsize(output_filepath)           # confirm the saved file has a filsize 
                if file_size > 250:                                         # check that file size is > 250 bytes
                    tmp_filename = os.path.join(self.output_dir_root, ".tmp", self.filename.replace(self.extension, ".jpg"))
                    os.remove(tmp_filename)                                 # Delete the tmp file
                    self.tmp_file_exists = False                            # reset the flag
                else:
                    self.image_saved = False
                    self.logger.info(f"File size too small. Failed to save image [{self.filepath}] to output directory [{output_filepath}]")
                    self.logger.info(f"File size: {file_size}")

        except Exception as e:
            print(f"Failed to confirm {self.filepath} was deleted from tmp directory: {e}")
            self.logger.info(f"Failed to confirm {self.filepath} was deleted from tmp directory: {e}")

    def save_json(self, output_filepath):   
        new_jpg_name = os.path.basename(output_filepath)
        new_json_name = new_jpg_name.replace(".jpg", ".json")

        new_json_path = os.path.join(self.file_output_dir, "_json", new_json_name)
        
        if self.json_exists == True:
            FileTools.ensure_folder_exists(os.path.join(self.file_output_dir, "_json"))              # Ensure json output dir exists
            shutil.copy(self.json_path, new_json_path)                                  # copy the json

            if os.path.exists(new_json_path):                                           # confirm the file saved file actually exists
                file_size = os.path.getsize(new_json_path)                              # confirm the saved file has a filsize 
                if file_size > 2:                                                       # check that file size is > 1 bytes
                    if self.delete_orig_file: 
                        os.remove(self.json_path)                                       # Delete the original file if the copy was succesfull 
                else:
                    self.json_saved = False
                    self.logger.info(f"Failed to confirm json saved. Filesize less then 2 bytes: {new_json_path}")
