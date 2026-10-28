#!/bin/bash

##########################
# --- Get Script Dir --- #

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
export PYTHONPATH="$SCRIPT_DIR:$SCRIPT_DIR/src:$SCRIPT_DIR/src/handlers:$SCRIPT_DIR/src/core${PYTHONPATH:+:$PYTHONPATH}"

APP_INSTALL_ROOT="${MEDIA_MANAGEMENT_ROOT:-/etc/media_management}"
APP_CONFIG_PATH="${MEDIA_MANAGEMENT_CONFIG_PATH:-${APP_INSTALL_ROOT}/app.yaml}"
APP_VENV_PATH="${MEDIA_MANAGEMENT_VENV_PATH:-${APP_INSTALL_ROOT}/.venv}"
APP_SCRIPT_PATH="$SCRIPT_PATH"

if [[ ! -f "$APP_CONFIG_PATH" && -f "$SCRIPT_DIR/config/app.yaml" ]]; then
  APP_CONFIG_PATH="$SCRIPT_DIR/config/app.yaml"
fi

media() {
  "$APP_SCRIPT_PATH" "$@"
}

if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
  return 0 2>/dev/null || exit 0
fi

if [[ "$SCRIPT_DIR" == "$APP_INSTALL_ROOT" && ! -d "$SCRIPT_DIR/src" ]]; then
  echo -e "${RED}Error: This script must be run from the repository checkout, not from the runtime directory.${RESET}" >&2
  echo -e "${YELLOW}Do not copy app.sh into /etc/media_management.${RESET}" >&2
  echo -e "${YELLOW}Source the repo version instead: . \"$SCRIPT_DIR/app.sh\"${RESET}" >&2
  exit 1
fi

##########################
# ---- Define Colors ---- #
RED="\033[0;31m"
CYAN="\033[0;36m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RESET="\033[0m"

##########################
# ----- Functions  ----- #
print_help_table(){
    ARGUMENT="$1"
    DESCRIPTION="$2"

    COLOR_ARGUMENT="\033[36m"
    COLOR_DESCRIPTION="\033[0m"
    NC="\033[0m"
    INDENT="    "
    printf "${INDENT}${COLOR_ARGUMENT}%-20s${NC}: ${COLOR_DESCRIPTION}%s${NC}\n" "$ARGUMENT" "$DESCRIPTION"
}

help() {
    echo -e "Media Management help menu: \n"
    print_help_table "ARGUMENT" "DESCRIPTION"
    print_help_table "setup" "Installs runtime config, Python environment, and creates a database if requested"
    print_help_table "setup_db" "Sets up the application database"
    print_help_table "config" "Edits database settings for the active MEDIA_DB"
    print_help_table "get_config" "Prints app config"
    print_help_table "import" "Imports media to the active database"
    print_help_table "scan_database" "Rebuilds image hashes; may take multiple hours"
    print_help_table "help" "Prints this help menu"
    echo " "
}

version(){
    echo -e "App Version: $APP_VERSION"
}

load_app_settings(){
    APP_CONFIG="$1"

    if [[ ! -f "$APP_CONFIG" ]]; then
        echo "Error - App config file doesn't exist: $APP_CONFIG" >&2
        echo "Ensure setup has created the runtime config under /etc/media_management or set MEDIA_MANAGEMENT_CONFIG_PATH." >&2
        return 1
    fi

    APP_NAME=$(yq -r '.app.name' < "$APP_CONFIG" 2>/dev/null || echo "")
    APP_VERSION=$(yq -r '.app.version' < "$APP_CONFIG" 2>/dev/null || echo "")
    DB_NAME=$(yq -r '.app.database.name' < "$APP_CONFIG" 2>/dev/null || echo "")
    DB_HOST=$(yq -r '.app.database.host' < "$APP_CONFIG" 2>/dev/null || echo "")
    DB_PATH=$(yq -r '.app.database.path' < "$APP_CONFIG" 2>/dev/null || echo "")

    if [[ -z "$APP_NAME" || -z "$APP_VERSION" ]]; then
        echo "Error loading app config file $APP_CONFIG" >&2
        return 1
    fi

    return 0
}

print_config(){
    DESCRIPTION="$1"
    VALUE="$2"

    COLOR_DESC="\033[35m"
    COLOR_VALUE="\033[0m"
    NC="\033[0m"

    printf "${COLOR_DESC}%-20s${NC}: ${COLOR_VALUE}%s${NC}\n" "$DESCRIPTION" "$VALUE"
}

load_app_settings "$APP_CONFIG_PATH"
if [[ $? -ne 0 ]]; then
  echo -e "${YELLOW}Warning: app config not loaded from $APP_CONFIG_PATH${RESET}"
  echo -e "${YELLOW}The repo can still be used from a dev checkout; runtime config lives in the selected system path.${RESET}"
fi

###############################
# --- Source py container --- #

source_env(){
  local candidate
  for candidate in "$APP_VENV_PATH/bin/activate" "$SCRIPT_DIR/.venv/bin/activate"; do
    if [[ -f "$candidate" ]]; then
      # shellcheck disable=SC1090
      source "$candidate"
      return 0
    fi
  done

  echo -e "${YELLOW}Error sourcing python environment${RESET}"
  echo -e "${RED}No virtual environment found under ${APP_VENV_PATH} or ${SCRIPT_DIR}/.venv${RESET}"
  return 1
}


# If no arguments were passed
if [[ $# -eq 0 ]]; then
  echo "No argument passed.  Printing help menu"
  help
  exit 1
fi

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
  case $1 in
    import)
        source_env
        python3 "$SCRIPT_DIR/scripts/import_media.py"
        shift
        ;;
    scan_database|scan-database)
        if [[ -z "${MEDIA_DB:-}" ]]; then
            echo -e "${RED}MEDIA_DB is not set. Source /etc/profile.d/media_db.sh or export MEDIA_DB first.${RESET}" >&2
            exit 1
        fi
        source_env || exit 1
        python3 "$SCRIPT_DIR/scripts/scan_database.py"
        if [[ $? -ne 0 ]]; then
            echo -e "${RED}Error: Database scan failed${RESET}" >&2
            exit 1
        fi
        ;;
    setup|--setup)
        shift
        "$SCRIPT_DIR/scripts/setup_app.sh" "$@"
        if [[ $? -ne 0 ]]; then
            echo -e "${RED}Error: App setup failed${RESET}"
            exit 1
        fi

        echo -e "\n${CYAN}Would you like to create a database now?${RESET}"
        read -p "Create a new database now? [Y/n]: " CREATE_DB
        if [[ "$CREATE_DB" =~ ^[Nn]$ ]]; then
            echo -e "${GREEN}App runtime setup complete.${RESET}"
            echo "Set MEDIA_DB later or run './app.sh setup' again to create a database."
            exit 0
        fi

        "$SCRIPT_DIR/scripts/setup_db.sh"
        if [[ $? -ne 0 ]]; then
            echo -e "${RED}Error: App database setup failed${RESET}"
            exit 1
        fi
        shift
        ;;

    setup_db|--setup_db)
        "$SCRIPT_DIR/scripts/setup_db.sh"
        if [[ $? -ne 0 ]]; then
            echo -e "${RED}Error: App database setup failed${RESET}"
            exit 1
        fi
        shift
        ;;

    config|db-config|database-config|edit-config)
        if [[ -z "${MEDIA_DB:-}" ]]; then
            echo -e "${RED}MEDIA_DB is not set. Source /etc/profile.d/media_db.sh or export MEDIA_DB first.${RESET}"
            exit 1
        fi
        source_env
        python3 "$SCRIPT_DIR/scripts/manage_db_config.py" "$@"
        shift
        ;;

    source_env)
        source_env
        shift
        ;;

    get_config)
        shift

        source_env

        print_config "App Name" "$APP_NAME"
        print_config "App Version" "$APP_VERSION"
        print_config "App config path" "$APP_CONFIG_PATH"
        print_config "Database Name" "$DB_NAME"
        print_config "Database Path" "$DB_PATH"
      ;;

    help|-help|--help)
      help
      ;;
    *)
      echo "Error: Unknown option $1"
      help
      exit 1
      ;;
  esac
  shift
done
