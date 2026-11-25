"""Functional tests for public Sahaaya pages, directory search, and profiles."""

from tests.conftest import extract_csrf, get_org_id_by_status


def test_homepage_loads_and_shows_dynamic_stats(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Find Those Who Need Your Support." in resp.data
    assert b"Total Registered Organizations" in resp.data
    assert b"Verified Organizations" in resp.data
    # Pending/Rejected sample names must never appear on homepage
    assert b"Pending)" not in resp.data
    assert b"Rejected)" not in resp.data


def test_explore_shows_only_verified_organizations_and_paginates(client):
    resp_p1 = client.get("/explore")
    assert resp_p1.status_code == 200
    assert b"<strong>8</strong> verified organizations found" in resp_p1.data
    assert b"Pending)" not in resp_p1.data
    assert b"Rejected)" not in resp_p1.data
    assert b"Correction)" not in resp_p1.data

    # Page 2 should have the remaining 2 organizations (6 per page)
    resp_p2 = client.get("/explore?page=2")
    assert resp_p2.status_code == 200
    assert b"View Details" in resp_p2.data


def test_explore_search_by_name_area_pincode_and_category(client):
    # Search by area
    resp_area = client.get("/explore?q=Indiranagar")
    assert resp_area.status_code == 200
    assert b"Asha Kiran" in resp_area.data
    assert b"<strong>1</strong> verified organization found" in resp_area.data

    # Search by pincode
    resp_pin = client.get("/explore?q=560011")
    assert resp_pin.status_code == 200
    assert b"Belaku Senior Citizens Sanctuary" in resp_pin.data

    # Category filter
    resp_cat = client.get("/explore?category=Orphanage")
    assert resp_cat.status_code == 200
    assert b"<strong>3</strong> verified organizations found" in resp_cat.data

    # Combined search + category
    resp_combo = client.get("/explore?q=Malleswaram&category=Orphanage")
    assert resp_combo.status_code == 200
    assert b"Chiguru Vidya Bala Kendra" in resp_combo.data

    # No-results state
    resp_empty = client.get("/explore?q=NoSuchAreaXYZ999")
    assert resp_empty.status_code == 200
    assert b"No Matching Verified Organizations Found" in resp_empty.data


def test_api_search_returns_only_verified_json(client):
    resp = client.get("/api/organizations/search?q=Bengaluru")
    assert resp.status_code == 200
    items = resp.get_json()
    assert isinstance(items, list)
    assert len(items) > 0
    names = [item["organization_name"] for item in items]
    assert all("Pending)" not in n and "Rejected)" not in n for n in names)


def test_organization_details_verified_vs_unverified(app, client):
    approved_id = get_org_id_by_status(app.config["DATABASE_PATH"], "Approved")
    resp = client.get(f"/organization/{approved_id}")
    assert resp.status_code == 200
    assert b"CALL ORGANIZATION" in resp.data
    assert b"EMAIL ORGANIZATION" in resp.data
    assert b"VIEW LOCATION" in resp.data
    assert b"Assistance Requirements" in resp.data

    for hidden_status in ("Pending", "Needs Correction", "Rejected"):
        hidden_id = get_org_id_by_status(app.config["DATABASE_PATH"], hidden_status)
        hidden_resp = client.get(f"/organization/{hidden_id}")
        assert hidden_resp.status_code == 404

    missing_resp = client.get("/organization/999999")
    assert missing_resp.status_code == 404


def test_about_sdgs_and_contact_form_persistence(client):
    about_resp = client.get("/about")
    assert about_resp.status_code == 200
    for sdg in (b"SDG 1", b"SDG 2", b"SDG 4", b"SDG 10", b"SDG 17"):
        assert sdg in about_resp.data

    contact_page = client.get("/contact")
    assert contact_page.status_code == 200
    token = extract_csrf(contact_page.data)
    post_resp = client.post(
        "/contact",
        data={
            "csrf_token": token,
            "sender_name": "Rohan Kulkarni",
            "sender_email": "rohan@example.org",
            "subject": "Onboarding Question",
            "message": "How can our Bengaluru NGO submit verification documents?",
        },
        follow_redirects=True,
    )
    assert post_resp.status_code == 200
    assert b"received by the Sahaaya coordination team" in post_resp.data
