"""Bengaluru demonstration data onboarding and idempotent seeding for Sahaaya.

All records seeded by this module are clearly labelled as fictional demonstration
data (`is_sample_data = 1`) with placeholder `.example.org` emails and `+91-80-0000-XXXX`
numbers so no real welfare organization's details are fabricated.
"""

from typing import Optional

from werkzeug.security import generate_password_hash

from database import db_session, init_db

SAMPLE_ORGANIZATIONS = [
    {
        "organization_name": "Asha Kiran Children's Home (Sample Demo)",
        "category": "Orphanage",
        "description": (
            "A residential care and learning center in Indiranagar supporting 42 school-going "
            "children with shelter, nutritious meals, after-school tutoring, and creative workshops."
        ),
        "address": "No. 14, 12th Main Road, HAL 2nd Stage, Indiranagar",
        "area": "Indiranagar",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560008",
        "contact_number": "+91-80-0000-1001",
        "email": "ashakiran.demo@sahaaya.example.org",
        "facilities": "Dormitories, Study Hall, Community Kitchen, Computer Lab, First-Aid Room",
        "image_filename": "org-orphanage.svg",
        "verification_status": "Approved",
        "verification_notes": "Verified sample record for Bengaluru demonstration.",
        "verification_date": "2026-11-10 10:30:00",
        "data_source": "Sample Demonstration Dataset (BMSIT&M Academic Demo)",
        "last_checked_date": "2026-11-10",
        "is_sample_data": 1,
        "requirements": [
            ("Food", "Sona Masoori Rice & Toor Dal", "Monthly staple grain requirement for 42 children.", "100 kg rice, 30 kg dal", "High"),
            ("Educational Materials", "Notebooks, Geometry Boxes & School Bags", "Needed for students in Grades 4 to 9.", "45 sets", "High"),
            ("Clothing", "Winter Sweaters & School Uniforms", "Sizes suitable for ages 7 to 15.", "40 pairs", "Medium"),
        ],
    },
    {
        "organization_name": "Belaku Senior Citizens Sanctuary (Sample Demo)",
        "category": "Old-Age Home",
        "description": (
            "Assisted living home in Jayanagar providing dignified residential care, "
            "daily physiotherapy sessions, balanced geriatric meals, and regular health checkups."
        ),
        "address": "No. 28, 4th Block, 11th Main, Jayanagar",
        "area": "Jayanagar",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560011",
        "contact_number": "+91-80-0000-1002",
        "email": "belaku.seniors.demo@sahaaya.example.org",
        "facilities": "Wheelchair-Accessible Rooms, Physiotherapy Unit, Dining Hall, 24/7 Caregiver Support",
        "image_filename": "org-oldage.svg",
        "verification_status": "Approved",
        "verification_notes": "Verified sample record for Bengaluru demonstration.",
        "verification_date": "2026-11-11 11:15:00",
        "data_source": "Sample Demonstration Dataset (BMSIT&M Academic Demo)",
        "last_checked_date": "2026-11-11",
        "is_sample_data": 1,
        "requirements": [
            ("Essential Supplies", "Adult Diapers & Orthopaedic Cushions", "Daily comfort and mobility supplies for 26 elders.", "20 packs monthly", "High"),
            ("Food", "Sugar-Free Nutrition Supplements & Oats", "For diabetic and senior residents.", "25 tins", "High"),
            ("Other", "Blood Pressure Monitors & Walkers", "Shared medical aid equipment.", "4 units", "Medium"),
        ],
    },
    {
        "organization_name": "Namma Neralu Night Shelter & Welfare Hub (Sample Demo)",
        "category": "Shelter & Community",
        "description": (
            "Community support shelter near Yelahanka New Town offering safe overnight accommodation, "
            "evening community meals, hygiene kits, and vocational referrals for migrant families."
        ),
        "address": "Plot 9, Sector B, Yelahanka New Town",
        "area": "Yelahanka",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560064",
        "contact_number": "+91-80-0000-1003",
        "email": "nammameralu.demo@sahaaya.example.org",
        "facilities": "Separate Male & Female Dorms, Clean Drinking Water, Community Kitchen, Locker Facility",
        "image_filename": "org-shelter.svg",
        "verification_status": "Approved",
        "verification_notes": "Verified sample record for Bengaluru demonstration.",
        "verification_date": "2026-11-12 09:45:00",
        "data_source": "Sample Demonstration Dataset (BMSIT&M Academic Demo)",
        "last_checked_date": "2026-11-12",
        "is_sample_data": 1,
        "requirements": [
            ("Essential Supplies", "Woollen Blankets & Sleeping Mats", "Urgent requirement for winter nights.", "50 blankets, 30 mats", "High"),
            ("Food", "Dry Rations & Evening Meal Ingredients", "Cooking oil, atta, pulses, and vegetables.", "Weekly supply for 60 people", "High"),
            ("Clothing", "Adult Hygiene Kits & Rainwear", "Soaps, towels, toothbrushes, and ponchos.", "60 kits", "Medium"),
        ],
    },
    {
        "organization_name": "Chiguru Vidya Bala Kendra (Sample Demo)",
        "category": "Orphanage",
        "description": (
            "Child welfare and bridge-school residential home in Malleswaram empowering orphaned and "
            "semi-orphaned children through holistic mentorship, arts, and STEM literacy."
        ),
        "address": "No. 45, 8th Cross, Sampige Road, Malleswaram",
        "area": "Malleswaram",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560003",
        "contact_number": "+91-80-0000-1004",
        "email": "chiguru.demo@sahaaya.example.org",
        "facilities": "Library, Smart Classroom, Indoor Play Area, Hostel Rooms, Dining Area",
        "image_filename": "org-orphanage.svg",
        "verification_status": "Approved",
        "verification_notes": "Verified sample record for Bengaluru demonstration.",
        "verification_date": "2026-11-13 14:20:00",
        "data_source": "Sample Demonstration Dataset (BMSIT&M Academic Demo)",
        "last_checked_date": "2026-11-13",
        "is_sample_data": 1,
        "requirements": [
            ("Educational Materials", "Kannada & English Storybooks + Science Kits", "For ages 6 to 14 library upgrade.", "60 books, 10 kits", "High"),
            ("Food", "Milk Powder, Ragi Flour & Fresh Fruits", "Daily breakfast nutrition for 34 children.", "Monthly contribution", "Medium"),
            ("Essential Supplies", "LED Study Lamps & Desk Chairs", "For evening study hall.", "12 lamps", "Low"),
        ],
    },
    {
        "organization_name": "Sandhya Deepa Elder Care Foundation (Sample Demo)",
        "category": "Old-Age Home",
        "description": (
            "Peaceful retirement and care facility in Koramangala supporting abandoned and low-income "
            "senior citizens with medical coordination, recreation rooms, and compassionate care."
        ),
        "address": "No. 72, 6th Block, 80 Feet Road, Koramangala",
        "area": "Koramangala",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560095",
        "contact_number": "+91-80-0000-1005",
        "email": "sandhyadeepa.demo@sahaaya.example.org",
        "facilities": "Garden Courtyard, Nurse Station, Prayer & Reading Room, Diet Kitchen",
        "image_filename": "org-oldage.svg",
        "verification_status": "Approved",
        "verification_notes": "Verified sample record for Bengaluru demonstration.",
        "verification_date": "2026-11-14 16:00:00",
        "data_source": "Sample Demonstration Dataset (BMSIT&M Academic Demo)",
        "last_checked_date": "2026-11-14",
        "is_sample_data": 1,
        "requirements": [
            ("Essential Supplies", "Cotton Bedsheets, Pillow Covers & Towels", "Fresh linen for 30 beds.", "35 sets", "Medium"),
            ("Clothing", "Comfortable Cotton Kurtas & Shawls", "Lightweight daily wear for seniors.", "30 pieces", "Medium"),
            ("Other", "Volunteer Medical Camp & Reading Visits", "Weekend geriatric checkups or companionship.", "Bi-weekly", "Low"),
        ],
    },
    {
        "organization_name": "Spandana Community Empowerment Center (Sample Demo)",
        "category": "Shelter & Community",
        "description": (
            "Urban community welfare center in Whitefield supporting daily-wage households with "
            "community nutrition, women's tailoring skill labs, and children's day-care."
        ),
        "address": "No. 19, ITPL Main Road, Brookefield, Whitefield",
        "area": "Whitefield",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560066",
        "contact_number": "+91-80-0000-1006",
        "email": "spandana.demo@sahaaya.example.org",
        "facilities": "Day-Care Crèche, Skill Training Hall, Community Pantry, Clean Restrooms",
        "image_filename": "org-shelter.svg",
        "verification_status": "Approved",
        "verification_notes": "Verified sample record for Bengaluru demonstration.",
        "verification_date": "2026-11-15 10:10:00",
        "data_source": "Sample Demonstration Dataset (BMSIT&M Academic Demo)",
        "last_checked_date": "2026-11-15",
        "is_sample_data": 1,
        "requirements": [
            ("Food", "Mid-Day Meal Staples & Pulses", "For 50 community children and mothers.", "80 kg monthly", "High"),
            ("Educational Materials", "Early Childhood Learning Toys & Slates", "For day-care children aged 3-6.", "25 kits", "Medium"),
            ("Other", "Pedal Sewing Machine Maintenance & Fabrics", "For women's livelihood training batch.", "15 meters fabric", "Medium"),
        ],
    },
    {
        "organization_name": "Navachethana Nest Orphanage (Sample Demo)",
        "category": "Orphanage",
        "description": (
            "Youth and children's residential home in Hebbal dedicated to academic continuity, "
            "sports activities, and life-skills mentorship for 28 children."
        ),
        "address": "No. 5, Kempapura Main Road, Hebbal",
        "area": "Hebbal",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560024",
        "contact_number": "+91-80-0000-1007",
        "email": "navachethana.demo@sahaaya.example.org",
        "facilities": "Playground, Study Hall, Kitchen & Dining, Solar Water Heater",
        "image_filename": "org-orphanage.svg",
        "verification_status": "Approved",
        "verification_notes": "Verified sample record for Bengaluru demonstration.",
        "verification_date": "2026-11-16 12:05:00",
        "data_source": "Sample Demonstration Dataset (BMSIT&M Academic Demo)",
        "last_checked_date": "2026-11-16",
        "is_sample_data": 1,
        "requirements": [
            ("Clothing", "Sports Shoes & Socks", "For morning athletics and school PT.", "28 pairs (UK 3-8)", "Medium"),
            ("Educational Materials", "Refurbished Desktops or Study Tablets", "To support high-school coding lessons.", "3 units", "High"),
        ],
    },
    {
        "organization_name": "Aasare Rehabilitation & Shelter Home (Sample Demo)",
        "category": "Shelter & Community",
        "description": (
            "Transitional shelter in Rajajinagar offering temporary housing, medical referrals, "
            "and warm meals for individuals experiencing sudden displacement."
        ),
        "address": "No. 88, 3rd Block, Dr. Rajkumar Road, Rajajinagar",
        "area": "Rajajinagar",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560010",
        "contact_number": "+91-80-0000-1008",
        "email": "aasare.demo@sahaaya.example.org",
        "facilities": "20-Bed Transitional Ward, Counseling Room, Community Dining, Laundry Area",
        "image_filename": "org-shelter.svg",
        "verification_status": "Approved",
        "verification_notes": "Verified sample record for Bengaluru demonstration.",
        "verification_date": "2026-11-17 15:40:00",
        "data_source": "Sample Demonstration Dataset (BMSIT&M Academic Demo)",
        "last_checked_date": "2026-11-17",
        "is_sample_data": 1,
        "requirements": [
            ("Essential Supplies", "First-Aid Kits, Sanitizers & Mosquito Nets", "Health protection for shelter beds.", "20 nets, 5 first-aid boxes", "High"),
            ("Food", "Cooking Oil, Spices & Tea Powder", "Monthly pantry replenishment.", "15 liters oil", "Medium"),
        ],
    },
    {
        "organization_name": "Vatsalya Senior Residence (Sample Demo - Pending)",
        "category": "Old-Age Home",
        "description": (
            "Newly onboarded senior residential center in Basavanagudi awaiting administrator "
            "verification of address documents and contact telephone line."
        ),
        "address": "No. 31, Bull Temple Road, Basavanagudi",
        "area": "Basavanagudi",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560004",
        "contact_number": "+91-80-0000-1009",
        "email": "vatsalya.pending.demo@sahaaya.example.org",
        "facilities": "15 Rooms, Dining Hall, Visiting Doctor Room",
        "image_filename": "org-oldage.svg",
        "verification_status": "Pending",
        "verification_notes": "Awaiting phone and site verification.",
        "verification_date": None,
        "data_source": "Sample Demonstration Dataset (Pending Onboarding)",
        "last_checked_date": "2026-11-19",
        "is_sample_data": 1,
        "requirements": [
            ("Food", "Dry Groceries & Milk", "Initial monthly estimate.", "40 kg rice", "Medium"),
        ],
    },
    {
        "organization_name": "Kaveri Hope Children's Shelter (Sample Demo - Pending)",
        "category": "Orphanage",
        "description": (
            "Community children's care initiative in BTM Layout submitted for onboarding review."
        ),
        "address": "No. 64, 2nd Stage, 16th Main, BTM Layout",
        "area": "BTM Layout",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560076",
        "contact_number": "+91-80-0000-1010",
        "email": "kaverihope.pending.demo@sahaaya.example.org",
        "facilities": "Study Room, Kitchen, Dormitory",
        "image_filename": "org-orphanage.svg",
        "verification_status": "Pending",
        "verification_notes": "Submitted for initial verification review.",
        "verification_date": None,
        "data_source": "Sample Demonstration Dataset (Pending Onboarding)",
        "last_checked_date": "2026-11-20",
        "is_sample_data": 1,
        "requirements": [
            ("Educational Materials", "School Stationery Packs", "Pens, pencils, notebooks.", "30 packs", "High"),
        ],
    },
    {
        "organization_name": "Pragathi Welfare Drop-In Center (Sample Demo - Correction)",
        "category": "Shelter & Community",
        "description": (
            "Day-care and community assistance center in HSR Layout returned for updated landmark details."
        ),
        "address": "Sector 2, HSR Layout (Landmark confirmation pending)",
        "area": "HSR Layout",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560102",
        "contact_number": "+91-80-0000-1011",
        "email": "pragathi.correction.demo@sahaaya.example.org",
        "facilities": "Community Hall, Drinking Water Station",
        "image_filename": "org-shelter.svg",
        "verification_status": "Needs Correction",
        "verification_notes": "Please provide complete door number and cross road.",
        "verification_date": None,
        "data_source": "Sample Demonstration Dataset (Needs Correction)",
        "last_checked_date": "2026-11-18",
        "is_sample_data": 1,
        "requirements": [
            ("Essential Supplies", "Reusable Steel Plates & Tumblers", "For community meals.", "40 sets", "Low"),
        ],
    },
    {
        "organization_name": "Unverified Test Listing (Sample Demo - Rejected)",
        "category": "Shelter & Community",
        "description": "Duplicate/incomplete demonstration entry rejected during verification.",
        "address": "Electronic City Phase 1",
        "area": "Electronic City",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560100",
        "contact_number": "+91-80-0000-1012",
        "email": "rejected.demo@sahaaya.example.org",
        "facilities": "N/A",
        "image_filename": "org-shelter.svg",
        "verification_status": "Rejected",
        "verification_notes": "Insufficient verification details; kept hidden from public portal.",
        "verification_date": "2026-11-18 17:00:00",
        "data_source": "Sample Demonstration Dataset (Rejected)",
        "last_checked_date": "2026-11-18",
        "is_sample_data": 1,
        "requirements": [],
    },
]


def seed_demo_data(db_path: Optional[str] = None) -> bool:
    """Insert Bengaluru demonstration organizations, requirements, users, and reports if empty."""
    init_db(db_path)

    with db_session(db_path) as conn:
        org_count = conn.execute("SELECT COUNT(*) AS cnt FROM organizations").fetchone()["cnt"]
        if org_count > 0:
            return False

        org_ids = []
        for entry in SAMPLE_ORGANIZATIONS:
            cur = conn.execute(
                """
                INSERT INTO organizations (
                    organization_name, category, description, address, area, city,
                    state, pincode, contact_number, email, facilities, image_filename,
                    verification_status, verification_notes, verification_date,
                    data_source, last_checked_date, is_sample_data
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry["organization_name"],
                    entry["category"],
                    entry["description"],
                    entry["address"],
                    entry["area"],
                    entry["city"],
                    entry["state"],
                    entry["pincode"],
                    entry["contact_number"],
                    entry["email"],
                    entry["facilities"],
                    entry["image_filename"],
                    entry["verification_status"],
                    entry["verification_notes"],
                    entry["verification_date"],
                    entry["data_source"],
                    entry["last_checked_date"],
                    entry["is_sample_data"],
                ),
            )
            oid = int(cur.lastrowid)
            org_ids.append(oid)

            for req in entry["requirements"]:
                conn.execute(
                    """
                    INSERT INTO assistance_requirements (
                        organization_id, requirement_category, item_name,
                        description, quantity_or_details, priority
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (oid, req[0], req[1], req[2], req[3], req[4]),
                )

            conn.execute(
                """
                INSERT INTO verification_audit_logs (
                    organization_id, admin_id, action, previous_status, new_status, notes
                )
                VALUES (?, NULL, ?, '', ?, ?)
                """,
                (
                    oid,
                    f"Seeded ({entry['verification_status']})",
                    entry["verification_status"],
                    entry["verification_notes"],
                ),
            )

        # Sample demonstration supporter accounts (safe demo passwords)
        demo_users = [
            ("Ananya Rao (Demo Supporter)", "ananya.demo@sahaaya.example.org", "Supporter@2026"),
            ("Karthik Gowda (Demo Supporter)", "karthik.demo@sahaaya.example.org", "Supporter@2026"),
        ]
        user_ids = []
        for full_name, email, pwd in demo_users:
            cur = conn.execute(
                """
                INSERT INTO users (full_name, email, password_hash, account_status)
                VALUES (?, ?, ?, 'Active')
                """,
                (full_name, email, generate_password_hash(pwd)),
            )
            user_ids.append(int(cur.lastrowid))

        # Sample contact inquiries
        if user_ids and len(org_ids) >= 2:
            conn.execute(
                """
                INSERT INTO contact_inquiries (user_id, organization_id, message, status)
                VALUES (?, ?, ?, 'Sent')
                """,
                (
                    user_ids[0],
                    org_ids[0],
                    "Hello, our student group would like to drop off 20 sets of notebooks and school bags this Saturday morning. Please confirm a suitable visiting time.",
                ),
            )
            conn.execute(
                """
                INSERT INTO contact_inquiries (user_id, organization_id, message, status)
                VALUES (?, ?, ?, 'Acknowledged')
                """,
                (
                    user_ids[1],
                    org_ids[1],
                    "We would like to donate sugar-free nutrition tins and volunteer for weekend reading sessions.",
                ),
            )

        # Sample inaccuracy reports for Admin Report Management demonstration
        if len(org_ids) >= 3:
            conn.execute(
                """
                INSERT INTO reports (organization_id, user_id, reported_by, reason, description, status)
                VALUES (?, ?, ?, ?, ?, 'Pending')
                """,
                (
                    org_ids[0],
                    user_ids[0],
                    "ananya.demo@sahaaya.example.org",
                    "Outdated assistance requirements",
                    "Sample report: Confirm whether winter sweaters are still required in full quantity.",
                ),
            )
            conn.execute(
                """
                INSERT INTO reports (organization_id, user_id, reported_by, reason, description, status, admin_notes)
                VALUES (?, NULL, ?, ?, ?, 'Reviewed', ?)
                """,
                (
                    org_ids[2],
                    "Anonymous Supporter",
                    "Incorrect address",
                    "Sample report: Suggested adding nearest Yelahanka bus stand landmark for easier navigation.",
                    "Landmark verification scheduled with coordinator.",
                ),
            )

    return True


if __name__ == "__main__":
    created = seed_demo_data()
    print("Seeded Bengaluru demonstration records." if created else "Database already contains organizations; skipped seeding.")
