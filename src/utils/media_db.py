import os
import sqlite3


class FileHashDB():
    def __init__(self, db_name="media.db", algorithm="sha256"):
        self.db_name = db_name
        self.algorithm = algorithm
        self.conn = sqlite3.connect(self.db_name)
        self._init_db() 

    def _init_db(self):
        """Create table if it doesn’t exist"""
        c = self.conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS file_hashes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE,
                hash TEXT,
                mtime REAL
            )
        """)
        self.conn.commit()

    def add_file(self, path, file_hash):
        """Insert or update a file’s hash in the database"""
        if not os.path.isfile(path):
            raise FileNotFoundError(f"{path} not found")
        file_hash = FileHashDB.normalize_hash(file_hash)
        mtime = os.path.getmtime(path)
        c = self.conn.cursor()
        
        # Check if the path exists
        c.execute("SELECT 1 FROM file_hashes WHERE path = ? LIMIT 1", (path,))
        if c.fetchone():
            # Update existing row
            c.execute("UPDATE file_hashes SET hash=?, mtime=? WHERE path=?",
                    (file_hash, mtime, path))
        else:
            # Insert new row
            c.execute("INSERT INTO file_hashes (path, hash, mtime) VALUES (?, ?, ?)",
                    (path, file_hash, mtime))
        self.conn.commit()

    def get_hash(self, path):
        """Retrieve stored hash for a file"""
        c = self.conn.cursor()
        c.execute("SELECT hash FROM file_hashes WHERE path = ?", (path,))
        row = c.fetchone()
        return row[0] if row else None

    def has_changed(self, path, current_hash):
        """Check if file contents have changed since last stored or if they exist"""
        if not os.path.isfile(path):
            return True  # treat missing as changed
        stored_hash = self.get_hash(path)
        return current_hash != stored_hash

    def scan_directory(self, directory, recursive=True):
        """Update hashes for all files in a directory"""
        for root, _, files in os.walk(directory):
            for f in files:
                self.update_file(os.path.join(root, f))
            if not recursive:
                break

    def hash_exists(self, file_hash):
        """Check if a hash already exists in the database"""
        file_hash = FileHashDB.normalize_hash(file_hash)
        c = self.conn.cursor()
        c.execute("SELECT 1 FROM file_hashes WHERE hash = ? LIMIT 1", (file_hash,))
        return c.fetchone() is not None

    @staticmethod
    def normalize_hash(h):
        #return str(h).strip().lower()
        return h

    def close(self):
        """Close database connection"""
        self.conn.close()




if __name__ == "__main__":
    db = FileHashDB("my_files.db")

    # update a single file
    db.update_file("test.txt")

    # check if a file changed
    if db.has_changed("test.txt"):
        print("test.txt has changed!")
    else:
        print("test.txt is unchanged.")

    # scan a whole directory
    db.scan_directory("my_project")

    # show stored hashes
    for row in db.conn.execute("SELECT path, hash FROM file_hashes"):
        print(row)

    db.close()