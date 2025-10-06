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
echo "Downloading dependencies"

if ! command -v yq >/dev/null 2>&1; then
    echo "Installing yq"
    sudo apt-get install yq  # Ubuntu/Debian
fi

# pthon virtual envioronment
sudo apt update && sudo apt install -y python3 python3-venv python3-pip

##################################
# --- Setting up python venv --- # 
echo "Setting up python virtual enviornemnt"

#create venv folder
mkdir "$SCRIPT_DIR"/.env

#setup and install python virtual enviornment
python3 -m meda_db "$SCRIPT_DIR"/.env

#download python packages required


