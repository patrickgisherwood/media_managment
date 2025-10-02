import os
import json
import shutil
import exiftool
from datetime import datetime
from utils.utils import FileTools, get_exif_datetime
from DuplicateImageRemover import DuplicateImageRemover


class VideoHandler:
    def __init__(self, filepath, output_directory, logger, remove_files=False):
        self.filepath = filepath
        self.output_directory = output_directory
        self.delete_orig_file = remove_files

        self.filename = os.path.basename(filepath)
        self.extension = os.path.splitext(self.filename)[1]
        self.init_logger(logger)

        self.datetime_taken = None              # initialize to a default value
        self.prevent_duplicates = False         # dont prevent duplicates with DuplicateImageRemover unless enabled

    def run(self):
        ## Starts the backup

        self.load_video_json()                  # Load .json data if it exists
        self.extract_video_metadata()           # Extract metadata
        self.filepath_orig = self.filepath      # stupid variable needed because of self.heic_to_jpg saves a temp file and needs to update self.filepath

        self.get_output_filepath()              # Determine output name of image
        self.save_video()                       # Save image to new filepath with metadata
        self.save_json()                        # Save json to new filepath

        '''
        1. Find all movie files
        2. Move all movie files to output dir and corresponding year subfolder
        3. Rename files based on date taken
        4. Save json files to json folder
        '''

    def prevent_duplicates(self, dir_trash=None, enable=True):
        if enable == False:
            self.prevent_duplicates = False

        dir_path = r"E:\meda_management"
        archive_path = r"E:\trash"
        self.duplicateTracker = DuplicateImageRemover(dir_path)
        if self.dir_trash is not None:
            self.duplicateTracker.archive(archive_path=dir_trash)

    def load_video_json(self):
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

    def extract_video_metadata(self):
        """
        Extracts metadat contgained in self.metadata to EXIF .

        Args:
            self

        Attributes:
            self.exif_data (str): Images metadata formated in exif
            self.datetime_taken (str): datetime the image was taken
        """

        self.exif_new = {}  # no standard structure like image EXIF blocks

        #with exiftool.ExifTool(r'C:\Tools\ExifTool\exiftool.exe') as et:
        ##with exiftool.ExifTool() as et:
        #    metadata = et.get_metadata(self.filepath)

        with exiftool.ExifTool(executable=r"C:\Tools\ExifTool\exiftool.exe") as et:
            
            metadata = et.execute(b"-j", self.filepath.encode("utf-8"))          # -j gives JSON output
            metadata = json.loads(metadata)[0]
            #metadata = json.loads(metadata.decode("utf-8"))[0]              # Decode and parse JSON

        # Example: Try to extract something like "DateTimeOriginal"
        possible_date_tags = [
            "QuickTime:CreateDate",         # Most common for .mov
            "EXIF:DateTimeOriginal",        # Some phones/cameras may include this
            "Composite:DateTimeCreated"     # Fallback if others are missing
        ]

        for tag in possible_date_tags:
            if tag in metadata:
                self.datetime_taken = metadata[tag]
                break

        if self.datetime_taken:
            # Example conversion function to reformat EXIF-style date/time
            date_time_original = get_exif_datetime(self.datetime_taken)
            self.exif_new['EXIF:DatetimeOriginal'] = date_time_original
        else:
            print("No video metadata date found.")

    def get_output_filepath(self):
        """
        Determines filepath that the image will be copied to.

        Args:
            self

        Attributes:
            self.output_filepath (path): Output path that the image will get saved to.

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
            self.output_directory = os.path.join(self.output_directory, folder_year)            # Modify output_directory to include year folder
            FileTools.ensure_folder_exists(self.output_directory)                                         # ensure the output directory exists

            if not self.filename.startswith(formatted_date[:8]):                                # Check if the filename already starts with the correct date string
                base_filename = f"{formatted_date}.mov"                                         # get new base_filename based on date string
                self.output_filepath = FileTools.get_unique_filename(os.path.join(self.output_directory, base_filename))           # ensure unique file path

            else:                                                                               # filename already starts with correct date string
                self.output_filepath = FileTools.get_unique_filename(os.path.join(self.output_directory, self.filename))           # ensure unique file path

        # If datetime taken metadata doesn't exist
        else:                                                                               # no date meta data for .jpg
            self.output_directory = os.path.join(self.output_directory, "unsorted")
            FileTools.ensure_folder_exists(self.output_directory)                                     # ensure the output directory exists
            self.output_filepath = self.filepath.replace(self.extension, ".mov")            # keep original name and ensure .jpg file extnsion
            self.output_filepath = FileTools.get_unique_filename(os.path.join(self.output_directory, self.filename))     # ensure unique name

    def save_video(self):

        file_size_orig = os.path.getsize(self.filepath)                     # get filesize of original file
        if self.delete_orig_file == True:
            shutil.move(self.filepath, self.output_filepath)                # execute the move
        else:
            shutil.copy2(self.filepath, self.output_filepath)               # execute the copy
        file_size_new = os.path.getsize(self.output_filepath)                      # get filesize of the new file
        
        # confirm transfer by checking the filesize
        if file_size_new < file_size_orig:
            print(f'[ERROR] Errory copying file. Filesize of output is smaller then the orgiginal ')
            print(f'[ERROR] Original File: {self.filepath} : {file_size_orig}')
            print(f'[ERROR] New File: {self.output_filepath} : {file_size_new}')
            # logger entry

        # Set datetime
        if self.datetime_taken:
            dt = datetime.strptime(self.datetime_taken, "%Y:%m:%d %H:%M:%S")
            dt = int(dt.timestamp())                                        # Get datetime taken if it exists
            FileTools.set_file_creation_date(self.output_filepath, dt)                # Set file date created time

    def save_json(self):
        new_jpg_name = os.path.basename(self.output_filepath)
        new_json_name = new_jpg_name.replace(".mov", ".json")
        
        new_json_path = os.path.join(self.output_directory, "_json", new_json_name)
        
        if self.json_exists == True:
            FileTools.ensure_folder_exists(os.path.join(self.output_directory, "_json"))    # Ensure json output dir exists
            shutil.copy(self.json_path, new_json_path)                                      # Save the json

            if os.path.exists(new_json_path):                                               # confirm the file saved file actually exists
                file_size = os.path.getsize(new_json_path)                                  # confirm the saved file has a filsize 
                if file_size > 2:
                    if self.delete_orig_file:                                 # check that file size is > 1 bytes
                        os.remove(self.json_path)                                               # Delete the original file if the copy was succesfull 
                else:
                    self.json_saved = False
                    self.logger.info(f"Failed to confirm json saved. Filesize less then 2 bytes: {new_json_path}")

    def init_logger(self, logger):
        self.logger = logger