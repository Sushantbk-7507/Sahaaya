"""Configuration module for the Sahaaya web platform."""

from datetime import timedelta
import os
import secrets

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def _get_or_create_secret_key(instance_dir: str) -> str:
    """Return SECRET_KEY from environment or a persisted local dev key."""
    env_key = os.environ.get("SECRET_KEY", "").strip()
    if env_key and env_key != "replace-with-a-long-random-secret-key":
        return env_key

    os.makedirs(instance_dir, exist_ok=True)
    key_file = os.path.join(instance_dir, ".secret_key")
    if os.path.exists(key_file):
        with open(key_file, "r", encoding="utf-8") as fh:
            stored = fh.read().strip()
            if stored:
                return stored

    generated = secrets.token_hex(32)
    with open(key_file, "w", encoding="utf-8") as fh:
        fh.write(generated)
    return generated


class Config:
    """Base application configuration."""

    BASE_DIR = BASE_DIR
    INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
    SECRET_KEY = _get_or_create_secret_key(INSTANCE_DIR)

    DATABASE_PATH = os.environ.get(
        "DATABASE_PATH",
        os.path.join(INSTANCE_DIR, "sahaaya.db"),
    )
    if not os.path.isabs(DATABASE_PATH):
        DATABASE_PATH = os.path.join(BASE_DIR, DATABASE_PATH)

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "images", "uploads")
    MAX_CONTENT_LENGTH = 3 * 1024 * 1024  # 3 MB
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

    # Session & Cookie Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("FLASK_ENV") == "production"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=4)

    # Pagination
    ORGANIZATIONS_PER_PAGE = 6

    # Domain Vocabularies
    ORGANIZATION_CATEGORIES = (
        "Orphanage",
        "Old-Age Home",
        "Shelter & Community",
    )

    REQUIREMENT_CATEGORIES = (
        "Food",
        "Clothing",
        "Educational Materials",
        "Essential Supplies",
        "Other",
    )

    REQUIREMENT_PRIORITIES = ("High", "Medium", "Low")

    VERIFICATION_STATUSES = (
        "Pending",
        "Approved",
        "Rejected",
        "Needs Correction",
    )

    REPORT_STATUSES = ("Pending", "Reviewed", "Resolved")

    REPORT_REASONS = (
        "Incorrect address",
        "Incorrect phone number",
        "Outdated assistance requirements",
        "Incorrect organization details",
        "Other issue",
    )

    INQUIRY_STATUSES = ("Sent", "Acknowledged", "Closed")

    CORE_ORG_FIELDS = (
        "organization_name",
        "category",
        "address",
        "area",
        "city",
        "state",
        "pincode",
        "contact_number",
        "email",
        "facilities",
    )


class TestingConfig(Config):
    """Configuration used by automated pytest suite."""

    TESTING = True
    SECRET_KEY = "test-suite-secret-key-do-not-use-in-prod"
    SESSION_COOKIE_SECURE = False
