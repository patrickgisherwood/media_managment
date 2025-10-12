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

config_file="config/app.yaml"

while IFS=":" read -r key value; do
    key=$(echo "$key" | xargs)     # trim whitespace
    value=$(echo "$value" | xargs) # trim whitespace
    if [[ -n "$key" && -n "$value" ]]; then
        declare "$key=$value"
    fi
done < <(grep -v '^#' "$config_file" | grep ':')


# app.yaml
SKIP_COPY=false
if [ -f "$SCRIPT_DIR/config/app.yaml" ]; then
  if [[ -f "$app_config_path" ]]; then
    echo -e "\033[35mWARNING - App config file alreay exists on device: $app_config_path \033[35m"
    input -e "\033[35mSkip coppying app.yaml which will overrite the current app settings?  [y/n]: \033[35m" CONTINUE
    if [[ "$CONTINUE" != 'y' ]];then
      exit 1   # need to handle this better.  How to exit this part of the code
      SKIP_COPY=true
    fi
  fi
  
  # only copy if user didn't skip
  if [[ "$SKIP_COPY" == false ]]; then
    echo "Copying app.yaml config file..."
    cp "$SCRIPT_DIR/config/app.yaml" "$app_config_path"
  fi
else
  echo -e "WARNING - no default app.yaml file was found from the repo directory to copy the new database"
  echo -e "location of missing file: $SCRIPT_DIR/config/app.yaml "
fi

##################################
# --- Install Dependencies --- # 
echo -e "\033[35mDownloading dependencies!!\033[35m"

if ! command -v yq >/dev/null 2>&1; then
    echo "Installing yq"
    sudo apt-get install yq
fi

# pthon virtual envioronment
echo -e "\033[35mUpdating package lists\033[35m" 
sudo apt update
echo -e "\033[35mInstalling python enviorment\033[35m" 
sudo apt install -y python3 python3-venv python3-pip

##################################
# --- Setting up python venv --- # 
echo -e "\033[35mSetting up python virtual enviornemnt\033[35m"

ENV_DIR="$SCRIPT_DIR"/.env
#create venv folder
if ! [[ -d "$ENV_DIR" ]]; then
    mkdir "$SCRIPT_DIR"/.envx
else
    echo -e "\033[35m.env folder already exists"
fi

python3 -m venv "$SCRIPT_DIR/.env/media_db"
source "$ENV_DIR"/media_db/bin/activate

echo -e "\033[35mInstalling python enviornment dependencies\033[35m" 
# download python packages
python3 -m pip install --upgrade pillow-heif   # get rid of the "python3 -m"???
pip install tqdm 
pip install colorama
python3 -m pip install piexif
python3 -m pip install pyyaml
python3 -m pip install numpy
python3 -m pip install imagehash
python3 -m pip install tqdm




echo -e "\033[35mMedia Managment setup complete\033[35m" 

