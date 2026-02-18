import sqlite3
from datetime import datetime


class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    action TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    session_id TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    total_files INTEGER NOT NULL,
                    total_errors INTEGER NOT NULL,
                    last_run TEXT NOT NULL,
                    session_id TEXT NOT NULL
                )
                """
            )
            # Project management tables
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    project_name TEXT NOT NULL,
                    project_path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    is_monitoring BOOLEAN DEFAULT 0,
                    total_files INTEGER DEFAULT 0
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS project_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    source_path TEXT,
                    destination_path TEXT NOT NULL,
                    file_size INTEGER,
                    duplicates_removed INTEGER DEFAULT 0,
                    moved_at TEXT NOT NULL,
                    file_hash TEXT,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
                """
            )
            self._ensure_column(conn, "logs", "username", "TEXT")
            self._ensure_column(conn, "stats", "username", "TEXT")
            conn.commit()

    def _ensure_column(self, conn, table_name, column_name, column_type):
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        existing_columns = {row[1] for row in cursor.fetchall()}
        if column_name not in existing_columns:
            cursor.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            )

    def create_user(self, username, password_hash):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password_hash),
            )
            conn.commit()

    def get_user_by_username(self, username):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def add_log(self, username, action, filename, status, message, session_id):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO logs (username, action, filename, status, message, timestamp, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    username,
                    action,
                    filename,
                    status,
                    message,
                    datetime.utcnow().isoformat(),
                    session_id,
                ),
            )
            conn.commit()

    def get_recent_logs(self, username, limit=20):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM logs WHERE username = ? ORDER BY id DESC LIMIT ?",
                (username, limit),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_logs_by_action(self, username, action, limit=20):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM logs
                WHERE username = ? AND action = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (username, action, limit),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_pending_uploads(self, username, limit=20):
        """Get pending uploads waiting for user confirmation."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM logs
                WHERE username = ? AND action = 'upload_pending'
                ORDER BY id DESC
                LIMIT ?
                """,
                (username, limit),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_monitoring_logs(self, username, limit=20):
        """Get all file monitoring logs (created, deleted, modified, renamed) for both files and folders."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM logs
                WHERE username = ? 
                AND action IN ('file_created', 'file_deleted', 'file_modified', 'file_renamed',
                               'folder_created', 'folder_deleted', 'folder_renamed')
                ORDER BY id DESC
                LIMIT ?
                """,
                (username, limit),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def update_stats(self, username, total_files, total_errors, session_id):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO stats (username, total_files, total_errors, last_run, session_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (username, total_files, total_errors, datetime.utcnow().isoformat(), session_id),
            )
            conn.commit()

    def get_latest_stats(self, username):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM stats
                WHERE username = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (username,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    # Project Management Methods

    def create_project(self, username, project_name, project_path):
        """Create a new project in the database."""
        with self._connect() as conn:
            cursor = conn.cursor()
            now = datetime.utcnow().isoformat()
            cursor.execute(
                """
                INSERT INTO projects (username, project_name, project_path, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (username, project_name, project_path, now, now),
            )
            conn.commit()
            return cursor.lastrowid

    def get_user_projects(self, username):
        """Get all projects for a user."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM projects
                WHERE username = ?
                ORDER BY updated_at DESC
                """,
                (username,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_project_by_id(self, project_id):
        """Get a specific project by ID."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM projects WHERE id = ?",
                (project_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_project_monitoring(self, project_id, is_monitoring):
        """Update project monitoring status."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE projects
                SET is_monitoring = ?, updated_at = ?
                WHERE id = ?
                """,
                (is_monitoring, datetime.utcnow().isoformat(), project_id),
            )
            conn.commit()

    def add_project_file(self, project_id, filename, file_type, source_path,
                         destination_path, file_size, duplicates_removed=0, file_hash=None):
        """Add a file to project tracking."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO project_files 
                (project_id, filename, file_type, source_path, destination_path,
                 file_size, duplicates_removed, moved_at, file_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (project_id, filename, file_type, source_path, destination_path,
                 file_size, duplicates_removed, datetime.utcnow().isoformat(), file_hash),
            )
            conn.commit()
            return cursor.lastrowid

    def get_project_files(self, project_id, limit=100):
        """Get all files in a project."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM project_files
                WHERE project_id = ?
                ORDER BY moved_at DESC
                LIMIT ?
                """,
                (project_id, limit),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_project_file_statistics(self, project_id):
        """Get statistics about files in a project."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 
                    file_type,
                    COUNT(*) as count,
                    SUM(file_size) as total_size,
                    SUM(duplicates_removed) as duplicates_cleaned
                FROM project_files
                WHERE project_id = ?
                GROUP BY file_type
                """,
                (project_id,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def update_project_file_count(self, project_id):
        """Update the total file count for a project."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE projects
                SET total_files = (SELECT COUNT(*) FROM project_files WHERE project_id = ?),
                    updated_at = ?
                WHERE id = ?
                """,
                (project_id, datetime.utcnow().isoformat(), project_id),
            )
            conn.commit()