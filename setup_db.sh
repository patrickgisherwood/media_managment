#!/bin/bash

# get the path to this script even if it's a symlink or being sourced
SOURCE="${BASH_SOURCE[0]:-$0}"
# resolve symlink to the real file (if readlink -f exists)
if command -v readlink >/dev/null 2>&1 && readlink -f / >/dev/null 2>&1; then
  SCRIPT_PATH="$(readlink -f "$SOURCE")"
# fallback to realpath if available
elif command -v realpath >/dev/null 2>&1; then
  SCRIPT_PATH="$(realpath "$SOURCE")"
else
  # last-resort: cd into dirname and use pwd -P (may not resolve symlink)
  SCRIPT_PATH="$(cd "$(dirname "$SOURCE")" && pwd -P)/$(basename "$SOURCE")"
fi

SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"


##################################
# --- source functions --- # 
source "$SCRIPT_DIR"/src/print_messages.sh

##################################
# --- Get Configuration Info --- # 


i=1
while :; do
    read -p "Setup new database on this device? [yes/no] " input

    if [[ $input == "yes" ]]; then
      break
    fi
    if [[ $i -le 3 ]]; then
        echo_warning "Please type "yes" to continue"
    else
        echo_error -p "\n Exiting"
        exit 1
    fi
    i=++
done

# Get database path
i=1
while :; do
    read -p "Inpupt directory path to create database:  " INPUT_DIRECTORY
    if [[ -d  $INPUT_DIRECTORY ]]; then
        break
    elif [[ $i -le 3 ]];then 
        echo_error "Invalid directory passed.  Exiting"
    else
        echo_warning "Path given is not a valid directory.  Please specify again: "
    fi
    i=++
done


# Get database name and confirm creation
read -p "Inpupt database name (EX media-managment) :  " DB_NAME
echo_msg "\nContinue with creation of database:\n  Name = $DB_NAME\n  INPUT_DIRECTORY = $INPUT_DIRECTORY/$DB_NAME\n"
read -p "Continue? [yes/no]: " CONFIRM

if [[ $CONFIRM != "yes" ]]; then 
    echo_error "Operation Canclled"
    exit 1
fi

##########################
# --- Setup Database --- #

# Create database directory
DB_DIRECTORY="$INPUT_DIRECTORY/$DB_NAME"

if [ ! -d "$DB_DIRECTORY/.data" ]; then
  mkdir -p "$DB_DIRECTORY";
  sudo chown "$USER" "$DB_DIRECTORY"
else
  echo_error "ERROR - Database path already exists.  Delete or move the original directory."
  exit 1  
fi

# Create .config directory
CONFIG_DIR="$DB_DIRECTORY/.config"
if [ ! -d "$CONFIG_DIR" ]; then
  echo_msg "Creating .config directory"
  mkdir -p "$CONFIG_DIR";
fi

# Create .data directory
DATA_DIR="$DB_DIRECTORY/.data"
if [ ! -d "$DATA_DIR" ]; then
  echo_msg "Creating .data directory"
  mkdir -p "$DATA_DIR";
fi

# Set env variable (available to all users and services)
echo "export MEDIA_DB=$DB_DIRECTORY" | sudo tee /etc/profile.d/media_db.sh
sudo chmod +x /etc/profile.d/media_db.sh


#############################################
#  --- Copy default configuration files --- #

# properties.yaml
if [ -f "$SCRIPT_DIR"/config/properties.yaml ]; then
  cp "$SCRIPT_DIR/config/properties.yaml" "$CONFIG_DIR"
else
  echo_wwarning "WARNING - no default app.yaml file was found from the repo directory to copy the new database"
  echo_warning "location of missing file: $SCRIPT_DIR/config/app.yaml "
fi


echo_msg "\nDatabase Setup Complete \n"