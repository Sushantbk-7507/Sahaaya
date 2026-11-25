"""Pytest fixtures and helpers for Sahaaya functional and security tests."""

import os
import re
import tempfile

import pytest

from app import create_app
from database import create_admin, db_session
from seed_data import seed_demo_data

CSRF_PATTERN = re.compile(r'name="csrf_token"\s+value="([^"]+)"')


def extract_csrf(response_data: bytes) -> str:
    """Extract the CSRF token from an HTML response."""
    text = response_data.decode("utf-8", errors="ignore")
    match = CSRF_PATTERN.search(text)
    assert match is not None, "CSRF token input not found in rendered HTML."
    return match.group(1)


@pytest.fixture()
def app():
    """Create a fresh Flask app backed by a temporary SQLite database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_sahaaya.db")
        upload_dir = os.path.join(tmpdir, "uploads")
        os.makedirs(upload_dir, exist_ok=True)

        flask_app = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": db_path,
                "INSTANCE_DIR": tmpdir,
                "UPLOAD_FOLDER": upload_dir,
                "WTF_CSRF_ENABLED": True,
                "ORGANIZATIONS_PER_PAGE": 6,
            }
        )
        seed_demo_data(db_path=db_path)
        create_admin(
            username="testadmin",
            email="admin@sahaaya.example.org",
            password="AdminPass@2026",
            db_path=db_path,
        )
        yield flask_app


@pytest.fixture()
def client(app):
    """Return a Flask test client."""
    return app.test_client()


@pytest.fixture()
def admin_client(app):
    """Return an independent test client authenticated as the test administrator."""
    ac = app.test_client()
    login_page = ac.get("/admin/login")
    token = extract_csrf(login_page.data)
    resp = ac.post(
        "/admin/login",
        data={
            "csrf_token": token,
            "identifier": "testadmin",
            "password": "AdminPass@2026",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Administrator Dashboard" in resp.data
    return ac


@pytest.fixture()
def user_client(app):
    """Return an independent test client authenticated as a demo supporter user."""
    uc = app.test_client()
    login_page = uc.get("/login")
    token = extract_csrf(login_page.data)
    resp = uc.post(
        "/login",
        data={
            "csrf_token": token,
            "email": "ananya.demo@sahaaya.example.org",
            "password": "Supporter@2026",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Supporter Workspace" in resp.data
    return uc


def get_org_id_by_status(db_path: str, status: str) -> int:
    """Return the ID of the first organization matching a given verification status."""
    with db_session(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM organizations WHERE verification_status = ? ORDER BY id ASC LIMIT 1",
            (status,),
        ).fetchone()
        assert row is not None
        return int(row["id"])
