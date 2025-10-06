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
echo -e "\033[35mDownloading dependencies\033[35m"

if ! command -v yq >/dev/null 2>&1; then
    echo "Installing yq"
    sudo apt-get install yq  # Ubuntu/Debian
fi

# pthon virtual envioronment
echo -e "\033[35mUpdating package lists" 
sudo apt update
echo -e "\033[35mInstalling python enviorment" 
sudo apt install -y python3 python3-venv python3-pip

##################################
# --- Setting up python venv --- # 
echo -e "\033[35mSetting up python virtual enviornemnt\033[35m"

ENV_DIR="$SCRIPT_DIR"/.env
#create venv folder
if ! [[ -d "$ENV_DIR" ]]; then
    mkdir "$SCRIPT_DIR"/.env
else
    echo -e "\033[35m.env folder already exists"
fi

#setup and install python virtual enviornment
python3 -m meda_db "$SCRIPT_DIR"/.env

source "$ENV_DIR"/


#download python packages required


