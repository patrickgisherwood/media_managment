#!/usr/bin/env bash

####################################################
####################################################
#  ---- Setup  ---- #

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
source "$REPO_ROOT"/src/print_messages.sh

APP_INSTALL_ROOT="${MEDIA_MANAGEMENT_ROOT:-/etc/media_management}"
APP_CONFIG_PATH="${MEDIA_MANAGEMENT_CONFIG_PATH:-${APP_INSTALL_ROOT}/app.yaml}"
DEFAULT_DB_ROOT="${MEDIA_MANAGEMENT_DB_ROOT:-${APP_INSTALL_ROOT}/databases}"

####################################################
####################################################
#  ---- Functions  ---- #

makeDirectory() {
  DIRECTORY=$1

  if [[ -z "$DIRECTORY" ]]; then
    echo "❌ Error: Missing path argument into makeDirectory()." >&2
    exit 1
  fi

  if [ ! -d "$DIRECTORY" ]; then
    echo_msg "Creating directory: $DIRECTORY"
    sudo mkdir -p "$DIRECTORY"
    sudo chown "$USER":"$USER" "$DIRECTORY"
  else
    echo "$DIRECTORY already exists"
  fi
}

####################################################
####################################################
#  ---- User Input  ---- #

read -r -p "Create a new database now? [Y/n]: " CREATE_DB
CREATE_DB="${CREATE_DB:-Y}"
if [[ "$CREATE_DB" =~ ^[Nn]$ ]]; then
    echo_msg "Database setup skipped."
    echo_msg "You can create a database later by running ./app.sh setup again."
    exit 0
fi

if [[ $- == *i* ]]; then
  bind 'TAB:complete'
  bind 'set completion-ignore-case on'
  bind 'TAB:menu-complete'
fi

sudo mkdir -p "$APP_INSTALL_ROOT" "$DEFAULT_DB_ROOT"

INPUT_DIRECTORY="$DEFAULT_DB_ROOT"
read -r -e -p "Database directory [${DEFAULT_DB_ROOT}]: " INPUT_DIRECTORY
INPUT_DIRECTORY="${INPUT_DIRECTORY:-$DEFAULT_DB_ROOT}"
INPUT_DIRECTORY="${INPUT_DIRECTORY%/}"
INPUT_DIRECTORY="${INPUT_DIRECTORY/#\~/$HOME}"

if [[ -z "$INPUT_DIRECTORY" ]]; then
  INPUT_DIRECTORY="$DEFAULT_DB_ROOT"
fi

if [[ ! -d "$INPUT_DIRECTORY" ]]; then
  echo_warning "Directory does not exist yet; creating $INPUT_DIRECTORY"
  sudo mkdir -p "$INPUT_DIRECTORY"
  sudo chown "$USER":"$USER" "$INPUT_DIRECTORY"
fi

read -r -p "Database name (example: my-media-db) [media-management]: " USER_DB_NAME
USER_DB_NAME="${USER_DB_NAME:-media-management}"
USER_DB_PATH="$INPUT_DIRECTORY/$USER_DB_NAME"

if [[ -e "$USER_DB_PATH" ]]; then
  echo_error "Database path already exists: $USER_DB_PATH"
  exit 1
fi

echo_msg "\nDatabase summary:\n  Name = $USER_DB_NAME\n  Directory = $USER_DB_PATH\n"
read -r -p "Create this database? [Y/n]: " CONFIRM
CONFIRM="${CONFIRM:-Y}"

if [[ "$CONFIRM" =~ ^[Nn]$ ]]; then
    echo_error "Operation Cancelled"
    exit 1
fi

####################################################
####################################################
# --- SETUP DATABASE --- #

DB_PATH="$USER_DB_PATH"
DB_NAME="$USER_DB_NAME"
CONFIG_DIR="$DB_PATH/.config"
DATA_DIR="$DB_PATH/.data"
ARCHIVE_DIR="$DB_PATH/.archive"
UNSORTED_DIR="$DB_PATH/unsorted"

makeDirectory "$DB_PATH"
makeDirectory "$CONFIG_DIR"
makeDirectory "$DATA_DIR"
makeDirectory "$ARCHIVE_DIR"
makeDirectory "$UNSORTED_DIR"

DB_PROPERTIES_FILE="$CONFIG_DIR/properties.yaml"
DEFAULT_PROPERTIES="$REPO_ROOT/config/properties.yaml"

if [[ -f "$DEFAULT_PROPERTIES" ]]; then
  cp "$DEFAULT_PROPERTIES" "$DB_PROPERTIES_FILE"
else
  echo_error "Missing default properties template: $DEFAULT_PROPERTIES"
  exit 1
fi

yq -i ".app.path = \"$DB_PATH\"" "$DB_PROPERTIES_FILE"
yq -i ".database.directory = \"$DB_PATH\"" "$DB_PROPERTIES_FILE"
yq -i ".database.db_path = \"$DB_PATH/media.db\"" "$DB_PROPERTIES_FILE"
yq -i ".database.temp_path = \"$DB_PATH/.tmp\"" "$DB_PROPERTIES_FILE"
yq -i ".database.name = \"$DB_NAME\"" "$DB_PROPERTIES_FILE"
yq -i ".image_handling.unsorted_images = \"$UNSORTED_DIR\"" "$DB_PROPERTIES_FILE"
yq -i ".image_handling.trash_directory = \"$ARCHIVE_DIR\"" "$DB_PROPERTIES_FILE"
yq -i ".image_handling.duplicate_detection.exclusion_directories = [\"$UNSORTED_DIR\", \"$ARCHIVE_DIR\"]" "$DB_PROPERTIES_FILE"

mkdir -p "$DB_PATH/.tmp"
sudo chown -R "$USER":"$USER" "$DB_PATH"

echo "export MEDIA_DB=$DB_PATH" | sudo tee /etc/profile.d/media_db.sh
sudo chmod +x /etc/profile.d/media_db.sh

echo_msg "✅ Database configuration written to $DB_PROPERTIES_FILE"
echo_msg "✅ MEDIA_DB exported for future shell sessions"

echo_msg "\nDatabase Setup Complete\n"