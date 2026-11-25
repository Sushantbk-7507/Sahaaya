"""SQLite database management, schema initialization, and safe migrations."""

from contextlib import contextmanager
import os
import sqlite3
from typing import Iterator, Optional

from flask import current_app, g
from werkzeug.security import generate_password_hash

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version TEXT NOT NULL UNIQUE,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    account_status TEXT NOT NULL DEFAULT 'Active'
        CHECK(account_status IN ('Active', 'Suspended')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS organizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_name TEXT NOT NULL,
    category TEXT NOT NULL
        CHECK(category IN ('Orphanage', 'Old-Age Home', 'Shelter & Community')),
    description TEXT NOT NULL,
    address TEXT NOT NULL,
    area TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    pincode TEXT NOT NULL,
    contact_number TEXT NOT NULL,
    email TEXT NOT NULL,
    facilities TEXT NOT NULL DEFAULT '',
    image_filename TEXT NOT NULL DEFAULT '',
    verification_status TEXT NOT NULL DEFAULT 'Pending'
        CHECK(verification_status IN ('Pending', 'Approved', 'Rejected', 'Needs Correction')),
    verification_notes TEXT NOT NULL DEFAULT '',
    verified_by INTEGER REFERENCES admins(id) ON DELETE SET NULL,
    verification_date TEXT,
    data_source TEXT NOT NULL DEFAULT 'Admin Entry',
    last_checked_date TEXT NOT NULL DEFAULT '',
    is_sample_data INTEGER NOT NULL DEFAULT 0 CHECK(is_sample_data IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS assistance_requirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL
        REFERENCES organizations(id) ON DELETE CASCADE,
    requirement_category TEXT NOT NULL
        CHECK(requirement_category IN (
            'Food', 'Clothing', 'Educational Materials', 'Essential Supplies', 'Other'
        )),
    item_name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    quantity_or_details TEXT NOT NULL DEFAULT '',
    priority TEXT NOT NULL DEFAULT 'Medium'
        CHECK(priority IN ('High', 'Medium', 'Low')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL
        REFERENCES organizations(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    reported_by TEXT NOT NULL,
    reason TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Pending'
        CHECK(status IN ('Pending', 'Reviewed', 'Resolved')),
    admin_notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS contact_inquiries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id INTEGER NOT NULL
        REFERENCES organizations(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Sent'
        CHECK(status IN ('Sent', 'Acknowledged', 'Closed')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS verification_audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL
        REFERENCES organizations(id) ON DELETE CASCADE,
    admin_id INTEGER REFERENCES admins(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    previous_status TEXT NOT NULL DEFAULT '',
    new_status TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS general_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_name TEXT NOT NULL,
    sender_email TEXT NOT NULL,
    subject TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_org_status ON organizations(verification_status);
CREATE INDEX IF NOT EXISTS idx_org_category ON organizations(category);
CREATE INDEX IF NOT EXISTS idx_org_location ON organizations(city, area, pincode);
CREATE INDEX IF NOT EXISTS idx_req_org ON assistance_requirements(organization_id);
CREATE INDEX IF NOT EXISTS idx_reports_org_status ON reports(organization_id, status);
CREATE INDEX IF NOT EXISTS idx_inquiries_user ON contact_inquiries(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_org ON verification_audit_logs(organization_id);
"""


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Create a configured SQLite connection with foreign keys enabled."""
    target_path = db_path or current_app.config["DATABASE_PATH"]
    parent_dir = os.path.dirname(os.path.abspath(target_path))
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    conn = sqlite3.connect(target_path, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    if target_path != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def get_db() -> sqlite3.Connection:
    """Return the request-scoped SQLite connection."""
    if "db" not in g:
        g.db = get_db_connection()
    return g.db


def close_db(_exception: Optional[BaseException] = None) -> None:
    """Close the request-scoped SQLite connection on teardown."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


@contextmanager
def db_session(db_path: Optional[str] = None) -> Iterator[sqlite3.Connection]:
    """Context manager for standalone scripts and CLI database operations."""
    conn = get_db_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    """Check whether a column already exists in a table."""
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row["name"] == column_name for row in rows)


def _apply_safe_migrations(conn: sqlite3.Connection) -> None:
    """Apply additive, non-destructive schema updates while preserving data."""
    additive_columns = [
        ("organizations", "verification_notes", "TEXT NOT NULL DEFAULT ''"),
        ("organizations", "verified_by", "INTEGER REFERENCES admins(id) ON DELETE SET NULL"),
        ("organizations", "data_source", "TEXT NOT NULL DEFAULT 'Admin Entry'"),
        ("organizations", "last_checked_date", "TEXT NOT NULL DEFAULT ''"),
        ("organizations", "is_sample_data", "INTEGER NOT NULL DEFAULT 0"),
        ("reports", "user_id", "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
        ("reports", "admin_notes", "TEXT NOT NULL DEFAULT ''"),
    ]
    for table, col, definition in additive_columns:
        if not _column_exists(conn, table, col):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")

    conn.execute(
        "INSERT OR IGNORE INTO schema_migrations (version) VALUES (?)",
        ("2026_11_v1_initial",),
    )


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize all database tables, indexes, and safe migrations."""
    with db_session(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
        _apply_safe_migrations(conn)


def create_admin(
    username: str,
    email: str,
    password: str,
    db_path: Optional[str] = None,
) -> int:
    """Create an administrator account with secure password hashing."""
    clean_username = username.strip()
    clean_email = email.strip().lower()
    if len(clean_username) < 3:
        raise ValueError("Admin username must be at least 3 characters.")
    if "@" not in clean_email:
        raise ValueError("A valid admin email is required.")
    if len(password) < 8:
        raise ValueError("Admin password must be at least 8 characters.")

    password_hash = generate_password_hash(password)
    with db_session(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO admins (username, email, password_hash)
            VALUES (?, ?, ?)
            """,
            (clean_username, clean_email, password_hash),
        )
        return int(cursor.lastrowid)


def bootstrap_admin_from_env(db_path: Optional[str] = None) -> Optional[int]:
    """Create initial admin from environment variables if no admin exists yet."""
    username = os.environ.get("SAHAAYA_ADMIN_USERNAME", "").strip()
    email = os.environ.get("SAHAAYA_ADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("SAHAAYA_ADMIN_PASSWORD", "")

    if not (username and email and password):
        return None

    with db_session(db_path) as conn:
        existing = conn.execute("SELECT COUNT(*) AS cnt FROM admins").fetchone()["cnt"]
        if existing > 0:
            return None

    return create_admin(username, email, password, db_path=db_path)
