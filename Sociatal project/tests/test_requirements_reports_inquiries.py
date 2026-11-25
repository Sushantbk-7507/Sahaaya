"""Tests for assistance requirements, public reporting, and user inquiries."""

from database import db_session
from tests.conftest import extract_csrf, get_org_id_by_status


def test_admin_requirements_crud_reflects_on_public_profile(app, admin_client):
    org_id = get_org_id_by_status(app.config["DATABASE_PATH"], "Approved")
    req_page = admin_client.get("/admin/requirements")
    token = extract_csrf(req_page.data)

    add_resp = admin_client.post(
        "/admin/requirements/add",
        data={
            "csrf_token": token,
            "organization_id": str(org_id),
            "requirement_category": "Essential Supplies",
            "item_name": "Solar Emergency Lanterns",
            "quantity_or_details": "10 rechargeable units",
            "priority": "High",
            "description": "Backup lighting for evening study hours.",
        },
        follow_redirects=True,
    )
    assert add_resp.status_code == 200
    assert b"Solar Emergency Lanterns" in add_resp.data

    # Reflected on public profile
    pub_resp = admin_client.get(f"/organization/{org_id}")
    assert b"Solar Emergency Lanterns" in pub_resp.data

    with db_session(app.config["DATABASE_PATH"]) as conn:
        req_row = conn.execute(
            "SELECT id FROM assistance_requirements WHERE item_name = 'Solar Emergency Lanterns'"
        ).fetchone()
        req_id = int(req_row["id"])

    # Edit requirement
    edit_resp = admin_client.post(
        f"/admin/requirements/{req_id}/edit",
        data={
            "csrf_token": token,
            "requirement_category": "Essential Supplies",
            "item_name": "Solar LED Study Lamps",
            "quantity_or_details": "15 units",
            "priority": "Medium",
            "description": "Updated specification.",
        },
        follow_redirects=True,
    )
    assert edit_resp.status_code == 200
    assert b"Solar LED Study Lamps" in admin_client.get(f"/organization/{org_id}").data

    # Delete requirement
    del_resp = admin_client.post(
        f"/admin/requirements/{req_id}/delete",
        data={"csrf_token": token},
        follow_redirects=True,
    )
    assert del_resp.status_code == 200
    assert b"Solar LED Study Lamps" not in admin_client.get(f"/organization/{org_id}").data


def test_public_report_and_admin_report_review(app, client, admin_client):
    org_id = get_org_id_by_status(app.config["DATABASE_PATH"], "Approved")
    org_page = client.get(f"/organization/{org_id}")
    token = extract_csrf(org_page.data)

    rep_resp = client.post(
        f"/organization/{org_id}/report",
        data={
            "csrf_token": token,
            "reason": "Incorrect phone number",
            "reported_by": "citizen@example.org",
            "description": "The landline number rang unanswered during morning office hours.",
        },
        follow_redirects=True,
    )
    assert rep_resp.status_code == 200
    assert b"submitted for administrator verification review" in rep_resp.data

    # Organization must NOT be auto-deleted or hidden immediately by a user report
    assert client.get(f"/organization/{org_id}").status_code == 200

    # Admin filters and resolves report
    reports_page = admin_client.get("/admin/reports?q=landline")
    assert reports_page.status_code == 200
    assert b"Incorrect phone number" in reports_page.data
    admin_token = extract_csrf(reports_page.data)

    with db_session(app.config["DATABASE_PATH"]) as conn:
        rep_id = int(
            conn.execute("SELECT id FROM reports ORDER BY id DESC LIMIT 1").fetchone()["id"]
        )

    upd_resp = admin_client.post(
        f"/admin/reports/{rep_id}/update",
        data={
            "csrf_token": admin_token,
            "status": "Resolved",
            "admin_notes": "Confirmed working alternate extension.",
        },
        follow_redirects=True,
    )
    assert upd_resp.status_code == 200
    assert b"Report status updated" in upd_resp.data


def test_supporter_inquiry_submission_and_admin_user_toggle(app, user_client, admin_client):
    org_id = get_org_id_by_status(app.config["DATABASE_PATH"], "Approved")
    dash = user_client.get("/dashboard")
    token = extract_csrf(dash.data)

    inq_resp = user_client.post(
        "/dashboard/inquire",
        data={
            "csrf_token": token,
            "organization_id": str(org_id),
            "message": "We would like to donate 30 kg of rice and pulses next Sunday.",
        },
        follow_redirects=True,
    )
    assert inq_resp.status_code == 200
    assert b"30 kg of rice and pulses" in inq_resp.data

    # Admin views users and toggles supporter status
    users_page = admin_client.get("/admin/users")
    assert users_page.status_code == 200
    assert b"ananya.demo@sahaaya.example.org" in users_page.data
    admin_token = extract_csrf(users_page.data)

    with db_session(app.config["DATABASE_PATH"]) as conn:
        uid = int(
            conn.execute(
                "SELECT id FROM users WHERE email = 'ananya.demo@sahaaya.example.org'"
            ).fetchone()["id"]
        )

    toggle_resp = admin_client.post(
        f"/admin/users/{uid}/toggle-status",
        data={"csrf_token": admin_token},
        follow_redirects=True,
    )
    assert toggle_resp.status_code == 200
    assert b"Suspended" in toggle_resp.data
