"""Security tests for Sahaaya: hashing, SQLi, CSRF, RBAC, and headers."""

from database import db_session
from tests.conftest import extract_csrf, get_org_id_by_status


def test_passwords_are_hashed_in_sqlite(app):
    with db_session(app.config["DATABASE_PATH"]) as conn:
        user_row = conn.execute(
            "SELECT password_hash FROM users WHERE email = 'ananya.demo@sahaaya.example.org'"
        ).fetchone()
        admin_row = conn.execute(
            "SELECT password_hash FROM admins WHERE username = 'testadmin'"
        ).fetchone()

    assert user_row["password_hash"] != "Supporter@2026"
    assert ":" in user_row["password_hash"]
    assert admin_row["password_hash"] != "AdminPass@2026"
    assert ":" in admin_row["password_hash"]


def test_sql_injection_attempts_are_blocked(client):
    sqli_resp = client.get("/explore?q=%27%20OR%201%3D1%20--")
    assert sqli_resp.status_code == 200
    assert b"No Matching Verified Organizations Found" in sqli_resp.data

    login_page = client.get("/login")
    token = extract_csrf(login_page.data)
    sqli_login = client.post(
        "/login",
        data={
            "csrf_token": token,
            "email": "admin@sahaaya.example.org' OR '1'='1",
            "password": "' OR '1'='1",
        },
    )
    assert sqli_login.status_code == 401


def test_csrf_protection_enforced_on_post_routes(app, client, user_client):
    org_id = get_org_id_by_status(app.config["DATABASE_PATH"], "Approved")

    # Missing CSRF on report
    assert (
        client.post(
            f"/organization/{org_id}/report",
            data={"reason": "Incorrect address", "description": "Missing token test"},
        ).status_code
        == 403
    )

    # Wrong CSRF on user inquiry
    assert (
        user_client.post(
            "/dashboard/inquire",
            data={
                "csrf_token": "invalid-token-123",
                "organization_id": str(org_id),
                "message": "Invalid CSRF test message.",
            },
        ).status_code
        == 403
    )


def test_normal_supporter_cannot_access_admin_routes(user_client):
    protected_admin_gets = [
        "/admin/dashboard",
        "/admin/organizations",
        "/admin/organizations/add",
        "/admin/verification",
        "/admin/users",
        "/admin/requirements",
        "/admin/reports",
    ]
    for path in protected_admin_gets:
        resp = user_client.get(path, follow_redirects=False)
        assert resp.status_code == 302
        assert "/admin/login" in resp.headers["Location"]

    # Also test POST with valid supporter CSRF token against admin route
    dash_token = extract_csrf(user_client.get("/dashboard").data)
    post_resp = user_client.post(
        "/admin/organizations/1/delete",
        data={"csrf_token": dash_token},
        follow_redirects=False,
    )
    assert post_resp.status_code == 302
    assert "/admin/login" in post_resp.headers["Location"]


def test_security_headers_present(client):
    resp = client.get("/")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"
