"""Tests for Admin Organization CRUD, file uploads, and mandatory verification."""

import io

from database import db_session
from tests.conftest import extract_csrf


def test_add_organization_starts_pending_and_verification_controls_visibility(app, admin_client):
    add_page = admin_client.get("/admin/organizations/add")
    assert add_page.status_code == 200
    token = extract_csrf(add_page.data)

    # Minimal valid 1x1 PNG header
    valid_png = io.BytesIO(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    )

    resp = admin_client.post(
        "/admin/organizations/add",
        data={
            "csrf_token": token,
            "organization_name": "Jeevan Jyothi Welfare Trust (Test)",
            "category": "Orphanage",
            "description": "Newly submitted Bengaluru children support home for verification testing.",
            "address": "No. 10, 4th Cross, RT Nagar",
            "area": "RT Nagar",
            "city": "Bengaluru",
            "state": "Karnataka",
            "pincode": "560032",
            "contact_number": "+91-80-0000-2222",
            "email": "jeevan.test@sahaaya.example.org",
            "facilities": "Study Room, Dormitory, Kitchen",
            "data_source": "Pytest Onboarding",
            "last_checked_date": "2026-11-25",
            "is_sample_data": "1",
            "req_category[]": ["Food"],
            "req_item_name[]": ["Wheat Flour"],
            "req_quantity[]": ["25 kg"],
            "req_priority[]": ["High"],
            "req_description[]": ["Monthly pantry supply"],
            "image": (valid_png, "test_org.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Pending verification status" in resp.data

    with db_session(app.config["DATABASE_PATH"]) as conn:
        org = conn.execute(
            "SELECT * FROM organizations WHERE email = 'jeevan.test@sahaaya.example.org'"
        ).fetchone()
        assert org is not None
        assert org["verification_status"] == "Pending"
        assert org["image_filename"].startswith("uploads/")
        org_id = int(org["id"])

    # While Pending, public access MUST return 404 and not appear in /explore
    assert admin_client.get(f"/organization/{org_id}").status_code == 404
    assert b"Jeevan Jyothi Welfare Trust" not in admin_client.get("/explore?q=RT+Nagar").data

    # Approve via verification queue
    ver_page = admin_client.get("/admin/verification?status=Pending")
    ver_token = extract_csrf(ver_page.data)
    approve_resp = admin_client.post(
        f"/admin/verification/{org_id}",
        data={
            "csrf_token": ver_token,
            "action": "approve",
            "verification_notes": "Verified contact and address details.",
        },
        follow_redirects=True,
    )
    assert approve_resp.status_code == 200

    # Now publicly visible!
    pub_resp = admin_client.get(f"/organization/{org_id}")
    assert pub_resp.status_code == 200
    assert b"Wheat Flour" in pub_resp.data

    # Editing core verified details triggers automatic re-verification (back to Pending)
    edit_page = admin_client.get(f"/admin/organizations/{org_id}/edit")
    edit_token = extract_csrf(edit_page.data)
    edit_resp = admin_client.post(
        f"/admin/organizations/{org_id}/edit",
        data={
            "csrf_token": edit_token,
            "organization_name": "Jeevan Jyothi Welfare Trust (Test)",
            "category": "Orphanage",
            "description": "Newly submitted Bengaluru children support home for verification testing.",
            "address": "No. 11, Updated Cross, RT Nagar",
            "area": "RT Nagar",
            "city": "Bengaluru",
            "state": "Karnataka",
            "pincode": "560032",
            "contact_number": "+91-80-0000-2222",
            "email": "jeevan.test@sahaaya.example.org",
            "facilities": "Study Room, Dormitory, Kitchen",
            "data_source": "Pytest Onboarding",
            "last_checked_date": "2026-11-25",
            "is_sample_data": "1",
        },
        follow_redirects=True,
    )
    assert edit_resp.status_code == 200
    assert b"reset to Pending for re-verification" in edit_resp.data
    assert admin_client.get(f"/organization/{org_id}").status_code == 404

    # Delete organization cleanly
    manage_page = admin_client.get("/admin/organizations")
    del_token = extract_csrf(manage_page.data)
    del_resp = admin_client.post(
        f"/admin/organizations/{org_id}/delete",
        data={"csrf_token": del_token},
        follow_redirects=True,
    )
    assert del_resp.status_code == 200
    assert b"were deleted" in del_resp.data


def test_reject_invalid_image_upload(admin_client):
    add_page = admin_client.get("/admin/organizations/add")
    token = extract_csrf(add_page.data)
    fake_png = io.BytesIO(b"MZ_THIS_IS_NOT_A_PNG_FILE")

    resp = admin_client.post(
        "/admin/organizations/add",
        data={
            "csrf_token": token,
            "organization_name": "Bad Upload Org",
            "category": "Orphanage",
            "description": "Testing invalid image magic byte validation on upload.",
            "address": "No. 22, MG Road",
            "area": "MG Road",
            "city": "Bengaluru",
            "state": "Karnataka",
            "pincode": "560001",
            "contact_number": "+91-80-0000-3333",
            "email": "badupload@sahaaya.example.org",
            "facilities": "Study Hall",
            "image": (fake_png, "malicious.png"),
        },
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert b"does not match a valid image header" in resp.data
