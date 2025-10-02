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
# --- Get Configuration Info --- # 

i=1
while :; do
    read -p "Setup new database on this device? [yes/no] " input

    if [[ $input == "yes" ]] && break
    if [[ $i -le 3 ]]; then
        echo -p "Please type "yes" to continue"
    else;
        echo -p "\n Exiting"
        exit 1
    fi
    i=++
done

# Get database path
i=1
while :; do
    read -p "Inpupt directory path to create database \nPATH:  " PATH
    if [[ -d  $path ]]; then
        break
    else;
        echo -p "Invalid directory path passed.  Please specify again \nPATH: " PATH
    fi
done


# Get database name and confirm creation
read -p "Inpupt database name (ex: media-managment) \nPATH:  " DB_NAME
read -pe "Continue with creation of datase:  \n  Name = $DB_NAME \n  Path = $PATH/$NAME \n\n Continue? [yes/no]:  " CONFIRM
if [[ $CONFIRM != "yes" ]]; then 
    echo "Operation Canclled"
    exit 1
fi

##########################
# --- Setup Database --- #

# Create database directory
if [ ! -d "$PATH/$DB_NAME" ]; then
  mkdir -p "$PATH/$DB_NAME";
else
  echo -e "ERROR - Database path already exists.  Delete or move the original directory."
fi

# Create .config directory
CONFIG_DIR="$PATH/.config"
if [ ! -d $CONFIG_DIR ]; then
  mkdir -p $CONFIG_DIR;
fi

# Create .data directory
DATA_DIR="$PATH/.data"
if [ ! -d $CONFIG_DIR ]; then
  mkdir -p $CONFIG_DIR;
fi

#############################################
#  --- Copy default configuration files --- #

# app.yaml
if [ -f "$SCRIPT_DIR"/config/app.yaml ]; then
  cp "$SCRIPT_DIR"/config/app.yaml CONFIG_DIR
else
  echo -e "WARNING - no default app.yaml file was found from the repo directory to copy the new database"
  echo -e "location of missing file: $SCRIPT_DIR/config/app.yaml "
fi

# properties.yaml
if [ -f "$SCRIPT_DIR"/config/properties.yaml ]; then
  cp "$SCRIPT_DIR"/config/properties.yaml CONFIG_DIR
else
  echo -e "WARNING - no default app.yaml file was found from the repo directory to copy the new database"
  echo -e "location of missing file: $SCRIPT_DIR/config/app.yaml "
fi
