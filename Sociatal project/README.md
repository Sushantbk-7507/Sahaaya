# SAHAAYA – A Web-Based Platform for Connecting Social Welfare Organizations

**Tagline:** *Connecting Communities. Empowering Lives.*  
**Academic Institution:** BMS Institute of Technology and Management (BMSIT&M), Bengaluru  
**Department:** Artificial Intelligence and Machine Learning  
**Project Type:** Societal Project  

---

## 1. Project Introduction

**Sahaaya** is a centralized, full-stack web platform designed to connect individuals willing to provide assistance with verified social welfare organizations—specifically **Orphanages**, **Old-Age Homes**, and **Shelters & Underprivileged Communities**. Rather than operating as an online payment gateway, Sahaaya emphasizes transparency, administrator-verified listings, itemized assistance needs, and direct supporter-to-organization contact.

## 2. Problem Statement

Citizens wishing to support local orphanages, senior care centers, and community shelters frequently encounter:
- Scattered, unverified, or outdated listings across blogs and maps.
- Incorrect street addresses, disconnected telephone numbers, or unmaintained contact details.
- Lack of clarity on available facilities and **actual current requirements** (e.g., food grains, educational stationery, winter blankets).
- Difficulty discovering nearby organizations in specific neighborhoods or pincodes.

## 3. Project Objectives

1. Centralize social welfare organization information in a clean, searchable web directory.
2. Enforce **mandatory administrator verification** before any organization becomes publicly visible.
3. Provide location-based (city, area, pincode) and category-based discovery.
4. Publish transparent, itemized assistance requirements categorized by priority.
5. Enable direct support via click-to-call (`tel:`), email (`mailto:`), Google Maps navigation, and tracked contact inquiries.
6. Maintain data accuracy continuously through community inaccuracy reporting and admin re-verification workflows.

## 4. Proposed System & Architecture

Sahaaya follows a modular three-tier Flask MVC-style architecture:
- **Presentation Layer:** Responsive HTML5, CSS3, Bootstrap 5, Font Awesome 6, and vanilla JavaScript (`templates/`, `static/`).
- **Application Layer:** Python Flask (`app.py`, `config.py`, `analytics.py`) implementing role-based session authentication (`user` vs. `admin`), CSRF protection, file upload validation, server-side input validation, and Pandas/NumPy/Scikit-learn analytics.
- **Persistence Layer:** Normalized relational SQLite database (`database.py`, `instance/sahaaya.db`) with foreign-key enforcement, parameterized SQL queries, audit logging, and safe additive schema migrations.

## 5. Key Features

- **Public Portal:** Impact statistics retrieved live from SQLite, featured verified organizations, 5-stage workflow overview, and assistance categories.
- **Search & Discovery (`/explore`):** Server-side parameterized partial search by organization name, city, area, or 6-digit pincode; category filters; alphabetical/recency sorting; live JSON suggestions; and pagination.
- **Organization Profiles (`/organization/<id>`):** Verified status badge, facilities, itemized needs grouped by category with priorities, click-to-call, click-to-email, Google Maps link, inaccuracy reporting form, and Scikit-learn TF-IDF cosine-similarity recommendations for similar verified organizations.
- **Supporter Authentication & Dashboard:** Secure registration (duplicate email prevention, password hashing), login, protected `/dashboard`, and private contact inquiry history.
- **Administrator Governance (`/admin/*`):** Separate secure admin login (no public admin registration), analytics dashboard (Pandas/NumPy), Organization CRUD with image magic-byte validation, Mandatory Verification Queue with audit logs, Assistance Requirements CRUD, Supporter Account management, and Report Review workflow.

## 6. UN Sustainable Development Goals (SDGs) Alignment

- **SDG 1 – No Poverty:** Connects resources directly with vulnerable communities and shelters.
- **SDG 2 – Zero Hunger:** Helps supporters identify organizations requiring staple food and nutrition assistance.
- **SDG 4 – Quality Education:** Supports access to notebooks, textbooks, school bags, and educational materials.
- **SDG 10 – Reduced Inequalities:** Improves visibility and resource access for disadvantaged children, elders, and displaced individuals.
- **SDG 17 – Partnerships for the Goals:** Bridges supporters, volunteers, academic institutions, and welfare centers.

## 7. Technology Stack

- **Frontend:** HTML5, CSS3, JavaScript (ES6), Bootstrap 5.3, Font Awesome 6.5
- **Backend:** Python 3.12, Flask 3.1, Werkzeug 3.1
- **Database:** SQLite 3 (`PRAGMA foreign_keys = ON`)
- **Data Processing & Analytics:** Pandas 2.2, NumPy 2.2, Scikit-learn 1.6
- **Testing:** Pytest 8.3

## 8. Database Structure

- `admins`: `id`, `username`, `email`, `password_hash`, `created_at`
- `users`: `id`, `full_name`, `email`, `password_hash`, `account_status`, `created_at`
- `organizations`: `id`, `organization_name`, `category`, `description`, `address`, `area`, `city`, `state`, `pincode`, `contact_number`, `email`, `facilities`, `image_filename`, `verification_status`, `verification_notes`, `verified_by`, `verification_date`, `data_source`, `last_checked_date`, `is_sample_data`, `created_at`, `updated_at`
- `assistance_requirements`: `id`, `organization_id` (FK), `requirement_category`, `item_name`, `description`, `quantity_or_details`, `priority`, `created_at`, `updated_at`
- `reports`: `id`, `organization_id` (FK), `user_id` (FK), `reported_by`, `reason`, `description`, `status`, `admin_notes`, `created_at`, `updated_at`
- `contact_inquiries`: `id`, `user_id` (FK), `organization_id` (FK), `message`, `status`, `created_at`
- `verification_audit_logs`: `id`, `organization_id` (FK), `admin_id` (FK), `action`, `previous_status`, `new_status`, `notes`, `created_at`
- `general_messages`: `id`, `sender_name`, `sender_email`, `subject`, `message`, `created_at`

## 9. Folder Structure

```text
Sociatal project/
├── app.py
├── config.py
├── database.py
├── analytics.py
├── seed_data.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── instance/
│   └── sahaaya.db
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── explore.html
│   ├── organization_details.html
│   ├── about.html
│   ├── contact.html
│   ├── login.html
│   ├── register.html
│   ├── user_dashboard.html
│   ├── admin_login.html
│   ├── admin_base.html
│   ├── admin_dashboard.html
│   ├── manage_organizations.html
│   ├── add_organization.html
│   ├── edit_organization.html
│   ├── verification.html
│   ├── manage_users.html
│   ├── manage_requirements.html
│   ├── manage_reports.html
│   ├── 403.html
│   ├── 404.html
│   └── 500.html
├── static/
│   ├── css/
│   │   ├── style.css
│   │   ├── dashboard.css
│   │   └── responsive.css
│   ├── js/
│   │   ├── main.js
│   │   ├── search.js
│   │   └── validation.js
│   └── images/
├── docs/
│   ├── TESTING_REPORT.md
│   └── EVALUATION_REPORT.md
└── tests/
    ├── conftest.py
    ├── test_public.py
    ├── test_auth.py
    ├── test_admin_crud_verification.py
    ├── test_requirements_reports_inquiries.py
    └── test_security.py
```

## 10. Setup, Initialization, Running & Testing Commands

### 1. Create the Virtual Environment
```powershell
python -m venv .venv
```

### 2. Activate the Virtual Environment
**Windows (PowerShell):**
```powershell
.\.venv\Scripts\Activate.ps1
```
**macOS / Linux:**
```bash
source .venv/bin/activate
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Configure Environment & Initialize Database
Copy `.env.example` to `.env` and update `SECRET_KEY` and administrator credentials, or initialize interactively:
```powershell
flask --app app init-db
flask --app app seed-demo
flask --app app init-admin
```
> **Note on Demonstration Data:** `seed-demo` populates clearly labelled fictional Bengaluru sample records (`is_sample_data = 1`, `.example.org` emails, `+91-80-0000-XXXX` placeholder numbers) so no real organization contact details are fabricated.

### 5. Run the Flask Application
```powershell
python app.py
```
Open `http://127.0.0.1:5000` in your browser.

### 6. Execute Automated Tests
```powershell
pytest -v
```

## 11. Deployment Instructions

For production or college server deployment:
1. Set `FLASK_ENV=production` and a strong random `SECRET_KEY` in `.env` (never commit `.env` or `instance/*.db`).
2. Serve the WSGI entry point (`app:create_app()`) behind a production WSGI server such as **Waitress** (Windows) or **Gunicorn** (Linux) with HTTPS termination via Nginx/Caddy so `SESSION_COOKIE_SECURE=True` is enforced.
3. Back up `instance/sahaaya.db` and `static/images/uploads/` regularly.
