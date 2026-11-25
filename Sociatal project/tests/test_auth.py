"""Authentication and session isolation tests for Sahaaya supporters and admins."""

from tests.conftest import extract_csrf


def test_supporter_registration_duplicate_and_validation(client):
    reg_page = client.get("/register")
    token = extract_csrf(reg_page.data)

    # Weak password rejected
    weak_resp = client.post(
        "/register",
        data={
            "csrf_token": token,
            "full_name": "Meera Nair",
            "email": "meera@example.org",
            "password": "short",
            "confirm_password": "short",
        },
    )
    assert weak_resp.status_code == 400

    # Valid registration succeeds
    ok_resp = client.post(
        "/register",
        data={
            "csrf_token": token,
            "full_name": "Meera Nair",
            "email": "meera@example.org",
            "password": "StrongPass123",
            "confirm_password": "StrongPass123",
        },
        follow_redirects=True,
    )
    assert ok_resp.status_code == 200
    assert b"Registration successful" in ok_resp.data

    # Duplicate email rejected
    reg_page2 = client.get("/register")
    token2 = extract_csrf(reg_page2.data)
    dup_resp = client.post(
        "/register",
        data={
            "csrf_token": token2,
            "full_name": "Meera Clone",
            "email": "meera@example.org",
            "password": "StrongPass123",
            "confirm_password": "StrongPass123",
        },
    )
    assert dup_resp.status_code == 409
    assert b"already exists" in dup_resp.data


def test_supporter_login_invalid_and_logout(client):
    login_page = client.get("/login")
    token = extract_csrf(login_page.data)

    bad_resp = client.post(
        "/login",
        data={
            "csrf_token": token,
            "email": "ananya.demo@sahaaya.example.org",
            "password": "WrongPassword99",
        },
    )
    assert bad_resp.status_code == 401
    assert b"Invalid email or password" in bad_resp.data

    good_resp = client.post(
        "/login",
        data={
            "csrf_token": token,
            "email": "ananya.demo@sahaaya.example.org",
            "password": "Supporter@2026",
        },
        follow_redirects=True,
    )
    assert good_resp.status_code == 200
    assert b"Ananya Rao" in good_resp.data

    dash_token = extract_csrf(good_resp.data)
    logout_resp = client.post(
        "/logout",
        data={"csrf_token": dash_token},
        follow_redirects=True,
    )
    assert logout_resp.status_code == 200
    assert b"logged out securely" in logout_resp.data

    # Dashboard requires login again
    protected = client.get("/dashboard", follow_redirects=False)
    assert protected.status_code == 302
    assert "/login" in protected.headers["Location"]


def test_user_inquiry_isolation(user_client):
    resp = user_client.get("/dashboard")
    assert resp.status_code == 200
    # Ananya's inquiry is visible, Karthik's inquiry is NOT visible
    assert b"20 sets of notebooks" in resp.data
    assert b"sugar-free nutrition tins" not in resp.data


def test_no_public_admin_registration_and_invalid_admin_login(client):
    assert client.get("/admin/register").status_code == 404

    admin_login_page = client.get("/admin/login")
    token = extract_csrf(admin_login_page.data)
    bad = client.post(
        "/admin/login",
        data={
            "csrf_token": token,
            "identifier": "testadmin",
            "password": "WrongAdminPassword",
        },
    )
    assert bad.status_code == 401
    assert b"Invalid administrator credentials" in bad.data
