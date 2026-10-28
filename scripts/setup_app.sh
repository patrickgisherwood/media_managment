#!/bin/bash

# get the path to this script even if it's a symlink or being sourced
SOURCE="${BASH_SOURCE[0]:-$0}"
if command -v readlink >/dev/null 2>&1 && readlink -f / >/dev/null 2>&1; then
  SCRIPT_PATH="$(readlink -f "$SOURCE")"
elif command -v realpath >/dev/null 2>&1; then
  SCRIPT_PATH="$(realpath "$SOURCE")"
else
  SCRIPT_PATH="$(cd "$(dirname "$SOURCE")" && pwd -P)/$(basename "$SOURCE")"
fi
REPO_ROOT="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd -P)"
SCRIPT_DIR="$REPO_ROOT"

APP_INSTALL_ROOT="${MEDIA_MANAGEMENT_ROOT:-/etc/media_management}"
APP_CONFIG_PATH="${MEDIA_MANAGEMENT_CONFIG_PATH:-${APP_INSTALL_ROOT}/app.yaml}"
APP_VENV_PATH="${MEDIA_MANAGEMENT_VENV_PATH:-${APP_INSTALL_ROOT}/.venv}"

if [[ "$REPO_ROOT" == "$APP_INSTALL_ROOT" ]]; then
  echo_error "This installer must run from the repository checkout, not from the runtime directory."
  echo_error "Do not copy app.sh or setup_app.sh into /etc/media_management."
  exit 1
fi

if [[ ! -d "$REPO_ROOT/src" || ! -d "$REPO_ROOT/scripts" ]]; then
  echo_error "Could not detect a valid repository checkout at: $REPO_ROOT"
  echo_error "The app must stay in the checked-out repo and its runtime files should live under /etc/media_management."
  exit 1
fi

##################################
# --- source functions --- #
source "$REPO_ROOT"/src/print_messages.sh

echo_msg "Starting Media Management setup"

##################################
# --- Parse Arguments --- #
UPDATE_PACKAGES=true
if [[ $# -gt 0 ]]; then
  case "$1" in
    --skip-update|skip-update)
      UPDATE_PACKAGES=false
      ;;
  esac
fi

#######################################
# --- Confirm internet connection --- #
if command -v ping >/dev/null 2>&1 && ! ping -c 1 1.1.1.1 >/dev/null 2>&1; then
  echo_warning "No external network connectivity detected. Package installation may fail if the system cannot reach apt/pip repos."
  echo_warning "Continuing anyway so the app can still refresh its runtime dependencies if available."
fi

##################################
# --- Set file permissions --- #
sudo mkdir -p "$APP_INSTALL_ROOT"
sudo chmod -R u+x "$REPO_ROOT"
sudo chmod +x "$REPO_ROOT"/app.sh "$REPO_ROOT"/scripts/setup_app.sh "$REPO_ROOT"/scripts/setup_db.sh

##################################
# --- Shell hook setup --- #
BASHRC_FILE="$HOME/.bashrc"
if [[ -n "${ZSH_VERSION:-}" ]]; then
  BASHRC_FILE="$HOME/.zshrc"
fi

SOURCE_LINE="if [ -f \"$REPO_ROOT/app.sh\" ] && [ -d \"$REPO_ROOT/src\" ]; then . \"$REPO_ROOT/app.sh\"; fi"
if [[ -f "$BASHRC_FILE" ]]; then
  if ! grep -Fqx "$SOURCE_LINE" "$BASHRC_FILE"; then
    echo "" >> "$BASHRC_FILE"
    echo "# Media Management shell hook" >> "$BASHRC_FILE"
    echo "$SOURCE_LINE" >> "$BASHRC_FILE"
    echo_msg "App shell hook added to $BASHRC_FILE"
  else
    echo_msg "Shell hook already present in $BASHRC_FILE"
  fi
else
  echo "$SOURCE_LINE" > "$BASHRC_FILE"
  echo_msg "Created $BASHRC_FILE and added the Media Management shell hook"
fi

##################################
# --- Runtime config location --- #
APP_CONFIG_EXISTS=false
if [[ -f "$APP_CONFIG_PATH" ]]; then
  APP_CONFIG_EXISTS=true
fi

APP_VENV_EXISTS=false
if [[ -d "$APP_VENV_PATH" ]]; then
  APP_VENV_EXISTS=true
fi

if [[ "$APP_CONFIG_EXISTS" == "true" || "$APP_VENV_EXISTS" == "true" ]]; then
  echo_warning "Detected existing Media Management runtime artifacts:"
  if [[ "$APP_CONFIG_EXISTS" == "true" ]]; then
    echo_warning " - Runtime config found: $APP_CONFIG_PATH"
  else
    echo_warning " - Runtime config missing: $APP_CONFIG_PATH"
  fi
  if [[ "$APP_VENV_EXISTS" == "true" ]]; then
    echo_warning " - Virtual environment found: $APP_VENV_PATH"
  else
    echo_warning " - Virtual environment missing: $APP_VENV_PATH"
  fi
  echo_warning "The app setup will keep the current runtime config unless you explicitly confirm an overwrite."
  echo_msg "Continuing with the runtime dependency refresh flow."
fi

if [ -f "$SCRIPT_DIR/config/app.yaml" ]; then
  if [[ -f "$APP_CONFIG_PATH" ]]; then
    echo_warning "Custom runtime config already exists at: $APP_CONFIG_PATH"
    echo_warning "This file may contain machine-specific settings. It will NOT be overwritten unless you explicitly confirm."
    read -r -p "Overwrite the current runtime config with the repo default? [y/N]: " CONTINUE
    if [[ "$CONTINUE" != "y" && "$CONTINUE" != "Y" ]]; then
      echo_msg "Keeping the existing custom runtime config."
    else
      sudo mkdir -p "$(dirname "$APP_CONFIG_PATH")"
      sudo cp "$SCRIPT_DIR/config/app.yaml" "$APP_CONFIG_PATH"
      echo_msg "Copied app.yaml to $APP_CONFIG_PATH"
    fi
  else
    sudo mkdir -p "$(dirname "$APP_CONFIG_PATH")"
    sudo cp "$SCRIPT_DIR/config/app.yaml" "$APP_CONFIG_PATH"
    echo_msg "Copied app.yaml to $APP_CONFIG_PATH"
  fi
else
  echo_warning "Default app.yaml was not found in the repo at $SCRIPT_DIR/config/app.yaml"
fi

##################################
# --- Install Dependencies --- #
echo_msg "Downloading dependencies"
if [[ "$UPDATE_PACKAGES" == "true" ]]; then
  echo_msg "Updating packages ..."
  set -euo pipefail
  sudo apt update
else
  echo_msg "Package updates skipped"
fi

if ! command -v yq >/dev/null 2>&1; then
    echo "Installing yq"
    sudo apt-get install yq
    sudo pip3 install yq
fi

# install common system dependencies
export DEBIAN_FRONTEND=noninteractive
sudo apt install -y \
    libheif-dev \
    libde265-dev \
    pkg-config \
    cmake \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libtiff-dev \
    libopenjp2-7-dev \
    libfreetype6-dev \
    exiftool

##################################
# --- Setting up python venv --- # 

echo_msg "# --- Python Setup --- #"

if [[ -z "$APP_VENV_PATH" ]]; then
  echo_error "Critical Error - runtime venv path is empty."
  exit 1
fi

if ! [[ -d "$APP_VENV_PATH" ]]; then
    sudo mkdir -p "$APP_VENV_PATH"
    sudo chown "$USER":"$USER" "$APP_VENV_PATH"
    echo_msg "Virtual environment path created: $APP_VENV_PATH"
else
    echo_warning "Python virtual env folder already exists: $APP_VENV_PATH"
    echo_warning "This venv is part of the runtime setup and will not be recreated unless you explicitly continue."
    read -r -p "Recreate or refresh the existing virtual environment? [y/N]: " REFRESH_VENV
    if [[ "$REFRESH_VENV" != "y" && "$REFRESH_VENV" != "Y" ]]; then
      echo_msg "Keeping the current virtual environment and skipping venv refresh."
      echo_msg "Media Management setup complete."
      exit 0
    fi
fi

echo_msg "Installing virtual environment"
python3 -m venv "$APP_VENV_PATH"
if [[ $? -ne 0 ]]; then
    echo_error "Failed to create virtual environment"
    exit 1
fi

echo_msg "Attempting to activate virtual env: $APP_VENV_PATH/bin/activate"
if [[ -f "$APP_VENV_PATH/bin/activate" ]]; then
    source "$APP_VENV_PATH/bin/activate"
    echo_msg "Virtual environment activated"
else
    echo_error "Failed to source virtual environment: activate script not found"
    exit 1
fi

echo_msg "Installing python environment dependencies"
export PKG_CONFIG_PATH="/usr/lib/arm-linux-gnueabihf/pkgconfig:${PKG_CONFIG_PATH:-}"

python3 -m pip install --upgrade pip setuptools wheel
python3 -m pip install --no-cache-dir --upgrade pillow
python3 -m pip install --extra-index-url https://www.piwheels.org/simple --upgrade pillow-heif || \
python3 -m pip install --extra-index-url https://www.piwheels.org/simple --upgrade "pillow-heif==0.8.0"
python3 -m pip install imagehash
python3 -m pip install tqdm
python3 -m pip install colorama
python3 -m pip install piexif
python3 -m pip install pyyaml
python3 -m pip install numpy
python3 -m pip install pyexiftool

echo_msg "Media Management setup complete"
