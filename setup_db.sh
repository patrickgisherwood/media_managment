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
# --- Install Dependencies --- # 

if ! command -v yq >/dev/null 2>&1; then
    echo "Installing yq"
    sudo apt-get install yq  # Ubuntu/Debian
fi




##################################
# --- Get Configuration Info --- # 

i=1
while :; do
    read -p "Setup new database on this device? [yes/no] " input

    if [[ $input == "yes" ]]; then
      break
    fi
    if [[ $i -le 3 ]]; then
        echo -p "Please type "yes" to continue"
    else
        echo -p "\n Exiting"
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
    else
        echo "Invalid directory INPUT_DIRECTORY passed.  Please specify again: " INPUT_DIRECTORY
    fi
done


# Get database name and confirm creation
read -p "Inpupt database name (EX media-managment) :  " DB_NAME
echo -e "\nContinue with creation of database:\n  Name = $DB_NAME\n  INPUT_DIRECTORY = $INPUT_DIRECTORY/$DB_NAME\n"
read -p "Continue? [yes/no]: " CONFIRM

if [[ $CONFIRM != "yes" ]]; then 
    echo "Operation Canclled"
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
  echo -e "ERROR - Database path already exists.  Delete or move the original directory."
  exit 1  
fi

# Create .config directory
CONFIG_DIR="$DB_DIRECTORY/.config"
if [ ! -d "$CONFIG_DIR" ]; then
  echo Creating .config directory
  mkdir -p "$CONFIG_DIR";
fi

# Create .data directory
DATA_DIR="$DB_DIRECTORY/.data"
if [ ! -d "$DATA_DIR" ]; then
  echo "Creating .data directory"
  mkdir -p "$DATA_DIR";
fi

# Set env variable (available to all users and services)
echo "export MEDIA_DB=$DB_DIRECTORY" | sudo tee /etc/profile.d/media_db.sh
sudo chmod +x /etc/profile.d/media_db.sh


#############################################
#  --- Copy default configuration files --- #

# app.yaml
if [ -f "$SCRIPT_DIR/config/app.yaml" ]; then
  cp "$SCRIPT_DIR/config/app.yaml" "$CONFIG_DIR"
else
  echo -e "WARNING - no default app.yaml file was found from the repo directory to copy the new database"
  echo -e "location of missing file: $SCRIPT_DIR/config/app.yaml "
fi

# properties.yaml
if [ -f "$SCRIPT_DIR"/config/properties.yaml ]; then
  cp "$SCRIPT_DIR/config/properties.yaml" "$CONFIG_DIR"
else
  echo -e "WARNING - no default app.yaml file was found from the repo directory to copy the new database"
  echo -e "location of missing file: $SCRIPT_DIR/config/app.yaml "
fi


echo -e "\nSetup Complete \n"