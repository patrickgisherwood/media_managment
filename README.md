# media_management

Repo for managing images and videos as a database. Prevents duplicates on media imports.

## Features

- **Duplicate Detection**: Automatically identifies and prevents duplicate media files during import
- **Database Management**: Organize and manage your media library efficiently
- **Image & Video Support**: Handle both image and video file formats

## Getting Started

### Prerequisites
- Python 3.x
- `yq` installed on the system
- A Linux/macOS shell with `bash`

### Installation

1. Clone the repository
```bash
git clone https://github.com/patrickgisherwood/media_managment.git
cd media_managment
```

2. Run the system setup from the app entry point
```bash
./app.sh setup
```

This creates the runtime config under `/etc/media_management`, sets up the Python virtual environment there, and then creates a database. The repo itself remains in your normal development checkout.

If the app is already configured, rerunning setup will stop and ask whether to keep the current runtime setup instead of overwriting it. Existing custom runtime config files are preserved unless you explicitly confirm an overwrite.

### Runtime layout

The codebase stays in the repo, while the runtime config and database data live under a system path such as:

```bash
/etc/media_management
```

The active database is selected with `MEDIA_DB`:

```bash
export MEDIA_DB=/etc/media_management/databases/my-media-db
```

### Setup a database

A database is created as part of `./app.sh setup`, so you do not run the database setup script directly in normal use.

If you need to rerun just the DB setup flow manually, it lives under `scripts/setup_db.sh` and is still invoked through the app launcher whenever possible.

The script will:
- create a database directory under `/etc/media_management/databases` by default
- write the active database root to `/etc/profile.d/media_db.sh`
- generate the database-specific `.config/properties.yaml` file

### Import media

After the database is created, run:

```bash
source /etc/profile.d/media_db.sh
./app.sh import
```

or, if you already have the environment loaded:

```bash
./app.sh import
```

### Rescan database image hashes

Database hash rescans are intentional and are not run during media imports. Run
one explicitly when needed:

```bash
./app.sh scan_database
```

The scan asks for confirmation because it may take multiple hours, depending on
the number and size of images and the Raspberry Pi's CPU and storage. Its
progress display shows elapsed time, with additional elapsed-time updates
written every minute to `database_scan.log` in the active database directory.

### Command line usage

```bash
./app.sh import          # import media into the active database
./app.sh scan_database   # intentionally rescan image hashes; may take hours
./app.sh setup           # run the full system install + database setup flow
./app.sh --help           # show help
```

### Configuration

The runtime config lives under `/etc/media_management/app.yaml` and each database gets its own `.config/properties.yaml` file rooted at the selected database directory.

The most important runtime variable is:

```bash
MEDIA_DB=/etc/media_management/databases/my-media-db
```

This points the importer at the currently active database root. It is a single active selection per shell session, which keeps the app simple and predictable.

## Project Structure

- `app.sh` — single runtime launcher and public entry point
- `scripts/setup_app.sh` — internal installer for the runtime config and virtual environment
- `scripts/setup_db.sh` — internal database creation flow
- `scripts/import_media.py` — media import pipeline
- `src/` — application code
- `config/` — repo defaults and templates

## Contributing

Feel free to submit issues and enhancement requests.

## Branch Information

- **Current Branch**: patrick/dev
- **Default Branch**: main
