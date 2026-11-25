# Sahaaya – Functional & Security Testing Report

**Execution Tool:** `pytest 8.3.4` on Python `3.12.10` (`.\.venv\Scripts\python.exe -m pytest -v`)  
**Scope:** 20 automated end-to-end integration and security tests with isolated temporary SQLite databases and CSRF protection enabled (`WTF_CSRF_ENABLED=True`).  
**Overall Result:** **20 / 20 Passed** (0 failed, 0 skipped).

| ID | Test Case | Expected Result | Actual Result | Status | Fix Applied (During QA) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| TC-01 | Homepage load & dynamic SQLite statistics | HTTP 200; shows dynamic stats; hides Pending/Rejected records | HTTP 200; verified counts match DB; unverified records absent | **PASS** | — |
| TC-02 | Explore directory visibility & pagination | Lists only Approved orgs (8 total); paginates 6/page to page 2 | HTTP 200; `8 verified organizations found`; page 2 loads remaining 2 | **PASS** | Updated test assertion to match `<strong>8</strong>` markup |
| TC-03 | Explore search by area, pincode, category & combined filters | Accurate partial SQL `LIKE` matches; empty state on no match | All filter combinations and empty state matched expected counts | **PASS** | — |
| TC-04 | JSON live search API (`/api/organizations/search`) | Returns JSON array of Approved organizations only | HTTP 200; JSON contains only Approved entries | **PASS** | — |
| TC-05 | Organization details visibility & 404 handling | Approved org returns 200 with contact/map links; Pending/Rejected/missing return 404 | Approved=200; Pending/Correction/Rejected/999999=404 | **PASS** | — |
| TC-06 | About SDGs & Contact form SQLite persistence | About lists SDGs 1, 2, 4, 10, 17; Contact POST saves record | HTTP 200; SDGs verified and contact confirmation shown | **PASS** | — |
| TC-07 | Supporter registration validation & duplicate email prevention | Weak password=400; valid=200 redirect; duplicate email=409 | Weak=400, Valid=200, Duplicate=409 | **PASS** | — |
| TC-08 | Supporter login, invalid credentials & logout | Invalid=401; valid redirects to dashboard; POST logout clears session | Invalid=401, Valid=200, post-logout `/dashboard` redirects to `/login` | **PASS** | — |
| TC-09 | Supporter dashboard inquiry isolation | User sees only own inquiries, never other supporters' inquiries | Ananya sees only her inquiry; Karthik's inquiry is excluded | **PASS** | — |
| TC-10 | Admin portal access & no public admin registration | `/admin/register` returns 404; invalid admin login returns 401 | `/admin/register`=404; invalid credentials=401 | **PASS** | — |
| TC-11 | Admin Add Org -> Pending -> Approve -> Core Edit Re-verify -> Delete | New org starts Pending (404 publicly); Approve publishes (200); editing core address resets to Pending (404); Delete removes cleanly | Full lifecycle verified end-to-end with audit trail | **PASS** | — |
| TC-12 | File upload magic-byte validation | Non-PNG binary disguised as `.png` rejected with 400 | Rejected with 400 (`does not match a valid image header`) | **PASS** | — |
| TC-13 | Assistance requirements CRUD & public profile sync | Add/Edit/Delete requirement by Admin reflects immediately on `/organization/<id>` | Public profile reflected additions, edits, and deletions | **PASS** | — |
| TC-14 | Public report submission & admin review | Submitting report creates Pending report without auto-deleting org; admin can filter and resolve | Report saved; org remained live; admin updated status to Resolved | **PASS** | — |
| TC-15 | Supporter inquiry submission & admin user status toggle | Supporter submits inquiry from dashboard; admin toggles Active/Suspended | Inquiry persisted; user status toggled to Suspended | **PASS** | Separated `user_client` and `admin_client` fixtures to avoid shared cookie wipe |
| TC-16 | Password hashing verification | Passwords stored as Werkzeug salted hashes, never plain text | Verified `password_hash` differs from plaintext and uses salted format | **PASS** | — |
| TC-17 | SQL injection prevention | `' OR 1=1 --` in search/login is safely parameterized | Search returned empty-match message; login returned 401 | **PASS** | — |
| TC-18 | CSRF token enforcement | Missing or invalid `csrf_token` on POST returns 403 | All tested POST endpoints returned 403 without valid token | **PASS** | — |
| TC-19 | Role-based access control (RBAC) | Normal supporter attempting `/admin/*` GET or POST is blocked | Redirected (`302`) to `/admin/login` on all tested admin routes | **PASS** | — |
| TC-20 | HTTP security headers | `X-Content-Type-Options: nosniff` and `X-Frame-Options: SAMEORIGIN` present | Both security headers verified on response | **PASS** | — |

## Environment Note on Analytics Fallback
During testing on Windows with Application Control enabled, `scikit-learn`'s compiled Cython `.pyd` extensions were blocked by the OS policy (`os error 4551`). `analytics.py` catches `(ImportError, OSError)` cleanly and falls back to an exact pure-NumPy TF-IDF + cosine similarity implementation while preserving full `scikit-learn` compatibility on unrestricted environments.
