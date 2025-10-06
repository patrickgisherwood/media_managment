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


##########################
# ----- Functions  ----- # 

print_help_table(){
    # Prints DESCRIPTION: VALUE in a colored, table-like format
    ARGUMENT="$1"
    DESCRIPTION="$2"

    # Set colors
    COLOR_ARGUMENT="\033[36m"  # Magenta
    COLOR_DESCRIPTION="\033[0m"  # Rest            "\033[36m" # Cyan
    NC="\033[0m"           # Reset color

    # Print formatted table row
    printf "${COLOR_ARGUMENT}%-20s${NC}: ${COLOR_DESCRIPTION}%s${NC}\n" "$ARGUMENT" "$DESCRIPTION"
}

help() {
    echo -e "Media Managment help menu: /n"

    print_help_table "ARGUMENT" "DESCRIPTION" 
    print_help_table "get_config" "Prints app config"
    #print_help_table "setup" "sets up new database on local device"
    print_help_table "import" "Imports media to database"
    print_help_table "help" "Prints this help menu"
    echo " "
}

version(){
    echo -e "App Version: $APP_VERSION"
}


load_app_settings(){

    APP_CONFIG="$1"

    if [[ -f "$APP_CONFIG" ]]; then
        echo "Error - App config file doesn't exist $APP_CONFIG"
        echo "Ensure ./setup.sh script has been run to configure a database on this machine or point to an existing database."
    fi
    
    local APP_NAME DB_NAME DB_HOST DB_PORT DB_PATH

    # Extract app settings
    APP_NAME=$(yq '.app.name' "$APP_CONFIG")
    APP_VERSION=$(yq '.app.version' "$APP_CONFIG")
    DB_NAME=$(yq '.app.database.name' "$APP_CONFIG")
    DB_HOST=$(yq '.app.database.host' "$APP_CONFIG")
    DB_PORT=$(yq '.app.database.port' "$APP_CONFIG")
    DB_PATH=$(yq '.app.database.path' "$APP_CONFIG")


    if [[ $? -ne 0 ]]; then
        echo "Error loading app config file $APP_CONFIG"
        echo "Ensure ./setup.sh script has been run to configure a database on this machine or point to an existing database."
    fi
}

print_config(){
    # Prints DESCRIPTION: VALUE in a colored, table-like format
    DESCRIPTION="$1"
    VALUE="$2"

    # Set colors
    COLOR_DESC="\033[35m"  # Magenta
    COLOR_VALUE="\033[0m"  # Rest            "\033[36m" # Cyan
    NC="\033[0m"           # Reset color

    # Print formatted table row
    printf "${COLOR_DESC}%-20s${NC}: ${COLOR_VALUE}%s${NC}\n" "$DESCRIPTION" "$VALUE"
}

APP_CONFIG_PATH="$SCRIPT_DIR"/.app/app.yaml

load_app_settings "$APP_CONFIG_PATH"


###############################
# --- Source py container --- # 

source "$SCRIPT_PATH"/env/python

if [[ $? -ne 0 ]];
    echo -e "Error sourcing python environment"
fi

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
  case $1 in
    import)
        python3 import.py
        shift
        ;;
    create)
        "$SCRIPT_DIR"/setup.sh
        python3 "$SCRIPT_DIR"/initilize_database.py
        shift
        ;;
    get_app_config)
        shift

        print_config "App Name" $APP_Name
        print_config "App Versino" $APP_VERSION
        print_config "App config path" $APP_CONFIG_PATH
        print_config "Database Name" $DB_NAME
        print_config "Database Path" $DB_PATH
      ;;

    --help)
      help
      shift
      ;;
    *)
      echo "Error: Unknown option $1"
      help
      exit 1
      ;;
  esac
  shift
done

