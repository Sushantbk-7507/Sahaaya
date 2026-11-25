# Sahaaya – Final Examiner Evaluation Report

**Project Title:** SAHAAYA – A Web-Based Platform for Connecting Social Welfare Organizations  
**Institution:** BMS Institute of Technology and Management, Bengaluru  
**Department:** Artificial Intelligence and Machine Learning  

---

## 1. Requirement-by-Requirement Evaluation

| # | Requirement | Implementation Status | Testing Result | Missing Functionality | Recommended Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | Centralized welfare directory | Implemented (`app.py`, `database.py`, `templates/`) | Verified via pytest & live HTTP probe | None | Maintain regular onboarding cycles |
| 2 | Verified organization profiles | Implemented (`verification_status = 'Approved'` filter on all public queries) | Verified (Pending/Rejected return 404) | None | Keep audit reviews periodic |
| 3 | Orphanage listings | Implemented (`category = 'Orphanage'`) | Verified via category filter & demo data | None | Expand verified Bengaluru records |
| 4 | Old-age home listings | Implemented (`category = 'Old-Age Home'`) | Verified via category filter & demo data | None | Expand verified Bengaluru records |
| 5 | Community & shelter listings | Implemented (`category = 'Shelter & Community'`) | Verified via category filter & demo data | None | Expand verified Bengaluru records |
| 6 | Location-based search | Implemented (city, area, pincode, address partial SQL `LIKE`) | Verified (Indiranagar, 560011, empty state) | GPS distance sorting (out of scope for lightweight SQLite) | Optional lat/lon radius in future v2 |
| 7 | Category-based filtering | Implemented (server-side filter + sort + pagination) | Verified (`Orphanage`, combined filters, pagination) | None | None |
| 8 | Contact details | Implemented (`contact_number`, `email`, `address`, `area`, `city`, `state`, `pincode`) | Verified on `organization_details.html` | None | Validate phone numbers during verification |
| 9 | Available facilities | Implemented (comma-separated chips on public profile) | Verified on public profile | None | Standardize facility tags if needed |
| 10 | Itemized assistance requirements | Implemented (`assistance_requirements` table, grouped by 5 categories + priority) | Verified (Admin CRUD reflects on public profile) | None | Prompt orgs monthly for updates |
| 11 | Direct contact functionality | Implemented (`tel:`, `mailto:`, Google Maps link, tracked contact inquiry) | Verified in HTML and inquiry tests | None | None |
| 12 | User authentication | Implemented (`/register`, `/login`, `/logout`, `/dashboard`, hashed passwords, CSRF) | Verified (dup email, weak pwd, session isolation) | Email verification link (requires SMTP) | Optional SMTP verification in deployment |
| 13 | Administrator dashboard | Implemented (`/admin/login`, `/admin/dashboard` with Pandas/NumPy KPIs & sidebar) | Verified (KPIs, RBAC, analytics) | None | Add CSV export if examiners request |
| 14 | Organization CRUD | Implemented (Add, View, Edit, Delete + image magic-byte validation) | Verified (upload validation, cascade delete) | None | None |
| 15 | Mandatory verification workflow | Implemented (New=Pending, Approve/Reject/Needs Correction, core-edit re-verification, audit log) | Verified end-to-end | None | None |
| 16 | Report management | Implemented (Public report modal + Admin filter/review/status/re-verification trigger) | Verified end-to-end | None | None |
| 17 | SQLite integration | Implemented (8 normalized tables, FKs enabled, safe migrations, parameterized queries) | Verified across 20 tests & live DB | None | Schedule periodic DB backups |
| 18 | Responsive interface | Implemented (Bootstrap 5 + `style.css`, `dashboard.css`, `responsive.css`) | Verified CSS breakpoints & mobile sidebar toggle | None | Cross-check on physical mobile during viva |
| 19 | Security | Implemented (PBKDF2/scrypt hashing, CSRF, RBAC, SQLi protection, security headers) | Verified in `tests/test_security.py` | Rate limiting (optional production extension) | Add reverse-proxy rate limit in prod |
| 20 | Societal relevance | Implemented (Bengaluru demo workflow + UN SDGs 1, 2, 4, 10, 17 on About & README) | Verified on `/about` and documentation | None | Replace sample records with verified consent-based NGO listings before public launch |

---

## 2. Live Demonstration Sequence (Recommended for Viva)

1. **Homepage (`/`):** Show dynamic statistics pulled from SQLite, featured verified Bengaluru sample organizations, 5-stage workflow, and 5 assistance categories.
2. **Explore & Search (`/explore`):** Search by area (`Indiranagar`), pincode (`560011`), combine with category filter (`Orphanage`), show pagination and clean empty-state handling.
3. **Organization Profile (`/organization/<id>`):** Show Verified badge, facilities, itemized needs grouped by priority, `CALL ORGANIZATION`, `EMAIL ORGANIZATION`, `VIEW LOCATION`, Similar Verified Organizations (TF-IDF cosine similarity), and submit an inaccuracy report.
4. **Supporter Registration & Dashboard (`/register` -> `/login` -> `/dashboard`):** Register a supporter, submit a direct inquiry, and show inquiry history isolation.
5. **Administrator Portal (`/admin/login` -> `/admin/dashboard`):** Show role separation, Pandas/NumPy analytics breakdown, add a new organization (prove it starts `Pending` and returns `404` publicly), approve it in `Pending Verification`, confirm it appears in `/explore`, edit a core field to trigger automatic re-verification, and resolve the submitted report in `Reported Information`.

---

## 3. 15 Likely Project Viva Questions and Answers

1. **Q: What real-world problem does Sahaaya solve?**  
   **A:** Information about orphanages, old-age homes, and shelters is scattered and frequently outdated. Sahaaya centralizes administrator-verified profiles, exact addresses, facilities, and itemized assistance needs so supporters can help directly without middlemen.
2. **Q: Why didn't you include an online payment gateway?**  
   **A:** By design, Sahaaya is an information-and-connection platform rather than a payment processor. Direct contact (`tel:`, `mailto:`, location map, and inquiry tracking) eliminates intermediary fees and builds direct community trust.
3. **Q: How do you prevent fake or unverified organizations from appearing publicly?**  
   **A:** Every newly added organization starts with `verification_status = 'Pending'`, and all public queries strictly filter `WHERE verification_status = 'Approved'`. Pending, Needs Correction, and Rejected records return `404` on public profile URLs.
4. **Q: What happens if an administrator edits a verified organization's phone number or address?**  
   **A:** Editing any core verified field (`organization_name`, `category`, `address`, `area`, `city`, `state`, `pincode`, `contact_number`, `email`, `facilities`) automatically resets `verification_status` back to `Pending` and logs an audit entry requiring re-verification.
5. **Q: How are user and administrator passwords secured?**  
   **A:** Passwords are never stored in plain text. They are hashed using Werkzeug's salted `generate_password_hash` and verified via `check_password_hash`.
6. **Q: How is SQL injection prevented across search and authentication routes?**  
   **A:** Every SQLite query uses parameterized `?` placeholders, and `LIKE` wildcards (`%`, `_`, `\`) in search queries are explicitly escaped.
7. **Q: How does CSRF protection work in Sahaaya?**  
   **A:** Every session generates a cryptographically random `csrf_token` (`secrets.token_hex(32)`), embedded in all POST forms and verified server-side in `before_request` using constant-time `hmac.compare_digest`. Missing or invalid tokens return HTTP `403`.
8. **Q: Can a normal registered supporter access `/admin/dashboard`?**  
   **A:** No. Admin routes enforce `@admin_required` server-side by checking `session.get("role") == "admin"` and verifying the `admin_id` exists in the `admins` table on every request.
9. **Q: Why is there no `/admin/register` route?**  
   **A:** Public administrator registration would allow anyone to gain verification privileges. Admin accounts are provisioned strictly through a secure CLI command (`flask --app app init-admin`) or protected environment bootstrap.
10. **Q: How are Pandas, NumPy, and Scikit-learn used meaningfully in this project?**  
    **A:** Pandas and NumPy compute real-time SQLite dashboard aggregations (category counts, locality concentration, average needs per verified organization), while TF-IDF + cosine similarity (`scikit-learn` with a NumPy fallback) powers "Similar Verified Organizations" recommendations on profile pages.
11. **Q: How does Sahaaya handle uploaded organization images safely?**  
    **A:** Uploads are capped at 3 MB, restricted to `.png/.jpg/.jpeg/.webp`, renamed with UUIDs via `secure_filename`, and validated by inspecting raw file magic bytes so executable files disguised as images are rejected.
12. **Q: What happens when a user submits an inaccuracy report?**  
    **A:** The report is stored in the `reports` table with status `Pending`. Organizations are never auto-deleted by unverified reports; instead, an administrator reviews the report and can optionally flag the organization for re-verification (`Needs Correction`).
13. **Q: How are foreign keys and cascading deletes handled in SQLite?**  
    **A:** Every connection executes `PRAGMA foreign_keys = ON;`, and child tables (`assistance_requirements`, `reports`, `contact_inquiries`, `verification_audit_logs`) define `ON DELETE CASCADE` or `ON DELETE SET NULL`.
14. **Q: Why are the Bengaluru records marked as Sample Demo Data?**  
    **A:** To demonstrate realistic Bengaluru locality search and verification workflows without fabricating phone numbers or emails of real-world centers before obtaining verified consent.
15. **Q: Which UN Sustainable Development Goals does Sahaaya support?**  
    **A:** SDG 1 (No Poverty), SDG 2 (Zero Hunger), SDG 4 (Quality Education), SDG 10 (Reduced Inequalities), and SDG 17 (Partnerships for the Goals).

---

## 4. Technical Limitations & Future Enhancements

- **Current Limitations:** Single-node SQLite file storage (ideal for academic/regional scale, not high-concurrency multi-region writes), no automated email/SMS notifications on inquiry submission, and manual phone/field verification by administrators.
- **Future Enhancements:**
  1. Email/SMS OTP notifications when organizations acknowledge supporter inquiries.
  2. Verified organization self-service portal (with mandatory admin approval for edits).
  3. Geospatial Haversine "Near Me" sorting using verified latitude/longitude coordinates.
  4. Migration path from SQLite to PostgreSQL for statewide deployment.

---

## 5. Final Project Presentation Guidance

- Keep slides focused on: (1) Societal Problem & Gap, (2) System Architecture & Verification Gate, (3) Database ER Diagram, (4) Live Demo of Search + Verification + Reporting, (5) Security Controls & Pytest Results, and (6) SDG Impact.
- Emphasize that **every card, statistic, and requirement shown in the demo comes live from `instance/sahaaya.db`**.
