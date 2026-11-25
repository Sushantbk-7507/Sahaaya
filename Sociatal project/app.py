"""Main Flask application for Sahaaya - Connecting Social Welfare Organizations."""

import hmac
import os
import re
import secrets
from typing import Any, Dict, Optional
from urllib.parse import quote_plus
import uuid

import click
from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from analytics import compute_admin_analytics, find_similar_organizations
from config import Config
from database import (
    bootstrap_admin_from_env,
    close_db,
    create_admin,
    get_db,
    init_db,
)
from seed_data import seed_demo_data

EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PINCODE_REGEX = re.compile(r"^\d{6}$")
PHONE_REGEX = re.compile(r"^[+\d][\d\s\-()]{6,18}\d$")

DEFAULT_CATEGORY_IMAGES = {
    "Orphanage": "org-orphanage.svg",
    "Old-Age Home": "org-oldage.svg",
    "Shelter & Community": "org-shelter.svg",
}


def _escape_like(value: str) -> str:
    """Escape SQL LIKE wildcard characters for safe partial matching."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _is_valid_image_bytes(stream: Any, ext: str) -> bool:
    """Inspect magic bytes to ensure uploaded file matches an allowed image type."""
    pos = stream.tell()
    header = stream.read(16)
    stream.seek(pos)
    if ext == "png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    if ext in {"jpg", "jpeg"}:
        return header.startswith(b"\xff\xd8\xff")
    if ext == "webp":
        return header[:4] == b"RIFF" and header[8:12] == b"WEBP"
    return False


def _save_uploaded_image(file_storage: Any, app: Flask) -> Optional[str]:
    """Validate and store an uploaded organization image, returning its relative filename."""
    if not file_storage or not file_storage.filename:
        return None

    filename = secure_filename(file_storage.filename)
    if "." not in filename:
        raise ValueError("Uploaded image must have a valid file extension.")

    ext = filename.rsplit(".", 1)[1].lower()
    if ext not in app.config["ALLOWED_IMAGE_EXTENSIONS"]:
        raise ValueError("Unsupported image format. Allowed types: PNG, JPG, JPEG, WEBP.")

    if not _is_valid_image_bytes(file_storage.stream, ext):
        raise ValueError("Uploaded file content does not match a valid image header.")

    unique_name = f"uploads/{uuid.uuid4().hex}.{ext}"
    dest_path = os.path.join(app.config["BASE_DIR"], "static", "images", unique_name)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    file_storage.save(dest_path)
    return unique_name


def _remove_uploaded_image(image_filename: str, app: Flask) -> None:
    """Safely remove a user-uploaded image file while preserving default SVGs."""
    if image_filename and image_filename.startswith("uploads/"):
        path = os.path.join(app.config["BASE_DIR"], "static", "images", image_filename)
        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass


def _validate_org_form(form: Any, config: Any) -> Dict[str, Any]:
    """Validate and normalize organization submission/edit form fields."""
    data = {
        "organization_name": form.get("organization_name", "").strip(),
        "category": form.get("category", "").strip(),
        "description": form.get("description", "").strip(),
        "address": form.get("address", "").strip(),
        "area": form.get("area", "").strip(),
        "city": form.get("city", "").strip(),
        "state": form.get("state", "").strip(),
        "pincode": form.get("pincode", "").strip(),
        "contact_number": form.get("contact_number", "").strip(),
        "email": form.get("email", "").strip().lower(),
        "facilities": form.get("facilities", "").strip(),
        "data_source": form.get("data_source", "Admin Entry").strip() or "Admin Entry",
        "last_checked_date": form.get("last_checked_date", "").strip(),
        "is_sample_data": 1 if form.get("is_sample_data") == "1" else 0,
    }

    errors = []
    if len(data["organization_name"]) < 3 or len(data["organization_name"]) > 150:
        errors.append("Organization name must be between 3 and 150 characters.")
    if data["category"] not in config["ORGANIZATION_CATEGORIES"]:
        errors.append("Please select a valid organization category.")
    if len(data["description"]) < 20 or len(data["description"]) > 2000:
        errors.append("Description must be between 20 and 2000 characters.")
    if len(data["address"]) < 5:
        errors.append("Complete address is required.")
    if len(data["area"]) < 2:
        errors.append("Area / locality is required.")
    if len(data["city"]) < 2:
        errors.append("City is required.")
    if len(data["state"]) < 2:
        errors.append("State is required.")
    if not PINCODE_REGEX.match(data["pincode"]):
        errors.append("Pincode must be a valid 6-digit number.")
    if not PHONE_REGEX.match(data["contact_number"]):
        errors.append("Contact number format is invalid.")
    if not EMAIL_REGEX.match(data["email"]):
        errors.append("Organization email address is invalid.")
    if len(data["facilities"]) < 3:
        errors.append("Please list available facilities.")

    if errors:
        raise ValueError(" ".join(errors))
    return data


def _user_required(view_func):
    """Decorator requiring an authenticated, active supporter user."""
    from functools import wraps

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if session.get("role") != "user" or not session.get("user_id"):
            flash("Please log in as a supporter to access that page.", "warning")
            return redirect(url_for("login", next=request.path))

        db = get_db()
        user = db.execute(
            "SELECT id, full_name, email, account_status FROM users WHERE id = ?",
            (session["user_id"],),
        ).fetchone()
        if not user or user["account_status"] != "Active":
            session.clear()
            flash("Your supporter session is no longer active.", "danger")
            return redirect(url_for("login"))

        return view_func(*args, **kwargs)

    return wrapped


def _admin_required(view_func):
    """Decorator requiring an authenticated administrator session."""
    from functools import wraps

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if session.get("role") != "admin" or not session.get("admin_id"):
            flash("Administrator authentication is required.", "warning")
            return redirect(url_for("admin_login"))

        db = get_db()
        admin = db.execute(
            "SELECT id, username, email FROM admins WHERE id = ?",
            (session["admin_id"],),
        ).fetchone()
        if not admin:
            session.clear()
            flash("Administrator session expired or invalid.", "danger")
            return redirect(url_for("admin_login"))

        return view_func(*args, **kwargs)

    return wrapped


def create_app(test_config: Optional[Dict[str, Any]] = None) -> Flask:
    """Application factory creating and configuring the Sahaaya Flask app."""
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    os.makedirs(app.config["INSTANCE_DIR"], exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    init_db(app.config["DATABASE_PATH"])
    if not app.config.get("TESTING"):
        bootstrap_admin_from_env(app.config["DATABASE_PATH"])

    app.teardown_appcontext(close_db)

    # ------------------------------------------------------------------
    # CSRF Protection & Security Headers
    # ------------------------------------------------------------------
    def generate_csrf_token() -> str:
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_hex(32)
        return session["csrf_token"]

    @app.context_processor
    def inject_globals():
        return {
            "csrf_token": generate_csrf_token,
            "org_categories": app.config["ORGANIZATION_CATEGORIES"],
            "req_categories": app.config["REQUIREMENT_CATEGORIES"],
            "req_priorities": app.config["REQUIREMENT_PRIORITIES"],
            "report_reasons": app.config["REPORT_REASONS"],
            "verification_statuses": app.config["VERIFICATION_STATUSES"],
            "report_statuses": app.config["REPORT_STATUSES"],
            "inquiry_statuses": app.config["INQUIRY_STATUSES"],
        }

    @app.before_request
    def enforce_csrf():
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            if not app.config.get("WTF_CSRF_ENABLED", True):
                return
            session_token = session.get("csrf_token")
            submitted = request.form.get("csrf_token") or request.headers.get("X-CSRFToken")
            if not session_token or not submitted or not hmac.compare_digest(
                str(session_token), str(submitted)
            ):
                abort(403)

    @app.after_request
    def apply_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response

    # ------------------------------------------------------------------
    # CLI Commands
    # ------------------------------------------------------------------
    @app.cli.command("init-db")
    def cli_init_db():
        """Initialize the SQLite database schema."""
        init_db(app.config["DATABASE_PATH"])
        click.echo("Database initialized successfully.")

    @app.cli.command("seed-demo")
    def cli_seed_demo():
        """Seed clearly labelled Bengaluru demonstration records."""
        inserted = seed_demo_data(app.config["DATABASE_PATH"])
        if inserted:
            click.echo("Seeded Bengaluru demonstration data.")
        else:
            click.echo("Database already populated; skipping demo seed.")

    @app.cli.command("init-admin")
    @click.option("--username", prompt=True, help="Administrator username")
    @click.option("--email", prompt=True, help="Administrator email")
    @click.option(
        "--password",
        prompt=True,
        hide_input=True,
        confirmation_prompt=True,
        help="Administrator password (min 8 chars)",
    )
    def cli_init_admin(username: str, email: str, password: str):
        """Create a new administrator account securely."""
        try:
            admin_id = create_admin(
                username=username,
                email=email,
                password=password,
                db_path=app.config["DATABASE_PATH"],
            )
            click.echo(f"Administrator account created (ID: {admin_id}).")
        except Exception as exc:
            raise click.ClickException(str(exc)) from exc

    # ------------------------------------------------------------------
    # Public Routes
    # ------------------------------------------------------------------
    @app.route("/")
    def index():
        db = get_db()
        stats_row = db.execute(
            """
            SELECT
                COUNT(*) AS total_orgs,
                SUM(CASE WHEN verification_status = 'Approved' THEN 1 ELSE 0 END) AS verified_orgs,
                COUNT(DISTINCT CASE WHEN verification_status = 'Approved' THEN category END) AS active_categories
            FROM organizations
            """
        ).fetchone()

        req_stats_rows = db.execute(
            """
            SELECT ar.requirement_category, COUNT(*) AS cnt
            FROM assistance_requirements ar
            JOIN organizations o ON o.id = ar.organization_id
            WHERE o.verification_status = 'Approved'
            GROUP BY ar.requirement_category
            """
        ).fetchall()
        req_counts = {row["requirement_category"]: row["cnt"] for row in req_stats_rows}

        featured_orgs = db.execute(
            """
            SELECT o.*, COUNT(ar.id) AS req_count
            FROM organizations o
            LEFT JOIN assistance_requirements ar ON ar.organization_id = o.id
            WHERE o.verification_status = 'Approved'
            GROUP BY o.id
            ORDER BY o.verification_date DESC, o.id DESC
            LIMIT 6
            """
        ).fetchall()

        stats = {
            "total_orgs": stats_row["total_orgs"] or 0,
            "verified_orgs": stats_row["verified_orgs"] or 0,
            "category_count": len(app.config["ORGANIZATION_CATEGORIES"]),
            "active_categories": stats_row["active_categories"] or 0,
        }
        return render_template(
            "index.html",
            stats=stats,
            featured_orgs=featured_orgs,
            req_counts=req_counts,
        )

    @app.route("/explore")
    def explore():
        db = get_db()
        q = request.args.get("q", "").strip()[:100]
        category = request.args.get("category", "").strip()
        sort = request.args.get("sort", "name_asc").strip()
        page = request.args.get("page", 1, type=int)
        if page < 1:
            page = 1

        if category and category not in app.config["ORGANIZATION_CATEGORIES"]:
            category = ""

        where_clauses = ["o.verification_status = 'Approved'"]
        params = []

        if q:
            escaped = f"%{_escape_like(q)}%"
            where_clauses.append(
                "("
                "o.organization_name LIKE ? ESCAPE '\\' OR "
                "o.city LIKE ? ESCAPE '\\' OR "
                "o.area LIKE ? ESCAPE '\\' OR "
                "o.pincode LIKE ? ESCAPE '\\' OR "
                "o.address LIKE ? ESCAPE '\\'"
                ")"
            )
            params.extend([escaped, escaped, escaped, escaped, escaped])

        if category:
            where_clauses.append("o.category = ?")
            params.append(category)

        where_sql = " AND ".join(where_clauses)

        order_map = {
            "name_asc": "o.organization_name ASC",
            "name_desc": "o.organization_name DESC",
            "recent": "o.verification_date DESC, o.id DESC",
        }
        order_sql = order_map.get(sort, "o.organization_name ASC")
        if sort not in order_map:
            sort = "name_asc"

        total_count = db.execute(
            f"SELECT COUNT(*) AS cnt FROM organizations o WHERE {where_sql}",
            params,
        ).fetchone()["cnt"]

        per_page = app.config["ORGANIZATIONS_PER_PAGE"]
        total_pages = max(1, (total_count + per_page - 1) // per_page)
        if page > total_pages:
            page = total_pages
        offset = (page - 1) * per_page

        orgs = db.execute(
            f"""
            SELECT o.*, COUNT(ar.id) AS req_count
            FROM organizations o
            LEFT JOIN assistance_requirements ar ON ar.organization_id = o.id
            WHERE {where_sql}
            GROUP BY o.id
            ORDER BY {order_sql}
            LIMIT ? OFFSET ?
            """,
            [*params, per_page, offset],
        ).fetchall()

        return render_template(
            "explore.html",
            organizations=orgs,
            total_count=total_count,
            total_pages=total_pages,
            current_page=page,
            q=q,
            selected_category=category,
            sort=sort,
        )

    @app.route("/api/organizations/search")
    def api_search_organizations():
        """JSON search helper returning only verified organizations."""
        db = get_db()
        q = request.args.get("q", "").strip()[:100]
        category = request.args.get("category", "").strip()
        if category and category not in app.config["ORGANIZATION_CATEGORIES"]:
            category = ""

        where_clauses = ["verification_status = 'Approved'"]
        params = []
        if q:
            escaped = f"%{_escape_like(q)}%"
            where_clauses.append(
                "(organization_name LIKE ? ESCAPE '\\' OR city LIKE ? ESCAPE '\\' "
                "OR area LIKE ? ESCAPE '\\' OR pincode LIKE ? ESCAPE '\\')"
            )
            params.extend([escaped, escaped, escaped, escaped])
        if category:
            where_clauses.append("category = ?")
            params.append(category)

        rows = db.execute(
            f"""
            SELECT id, organization_name, category, area, city, pincode
            FROM organizations
            WHERE {' AND '.join(where_clauses)}
            ORDER BY organization_name ASC
            LIMIT 12
            """,
            params,
        ).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.route("/organization/<int:org_id>")
    def organization_details(org_id: int):
        db = get_db()
        org = db.execute(
            """
            SELECT * FROM organizations
            WHERE id = ? AND verification_status = 'Approved'
            """,
            (org_id,),
        ).fetchone()
        if not org:
            abort(404)

        req_rows = db.execute(
            """
            SELECT * FROM assistance_requirements
            WHERE organization_id = ?
            ORDER BY
                CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
                requirement_category ASC,
                id ASC
            """,
            (org_id,),
        ).fetchall()

        grouped_requirements: Dict[str, list] = {}
        for cat in app.config["REQUIREMENT_CATEGORIES"]:
            items = [r for r in req_rows if r["requirement_category"] == cat]
            if items:
                grouped_requirements[cat] = items

        facilities_list = [
            f.strip() for f in (org["facilities"] or "").split(",") if f.strip()
        ]
        full_address = f"{org['address']}, {org['area']}, {org['city']}, {org['state']} {org['pincode']}"
        maps_url = f"https://www.google.com/maps/search/?api=1&query={quote_plus(full_address)}"
        similar_orgs = find_similar_organizations(db, org_id, top_k=3)

        return render_template(
            "organization_details.html",
            org=org,
            grouped_requirements=grouped_requirements,
            total_requirements=len(req_rows),
            facilities_list=facilities_list,
            maps_url=maps_url,
            similar_orgs=similar_orgs,
        )

    @app.route("/organization/<int:org_id>/report", methods=["POST"])
    def submit_report(org_id: int):
        db = get_db()
        org = db.execute(
            "SELECT id, organization_name FROM organizations WHERE id = ? AND verification_status = 'Approved'",
            (org_id,),
        ).fetchone()
        if not org:
            abort(404)

        reason = request.form.get("reason", "").strip()
        description = request.form.get("description", "").strip()
        reported_by = request.form.get("reported_by", "").strip()

        if session.get("role") == "user" and session.get("user_email"):
            user_id = session.get("user_id")
            if not reported_by:
                reported_by = session.get("user_email")
        else:
            user_id = None
            if not reported_by:
                reported_by = "Anonymous Supporter"

        if reason not in app.config["REPORT_REASONS"]:
            flash("Please select a valid reason for reporting.", "danger")
            return redirect(url_for("organization_details", org_id=org_id))

        if len(description) < 10 or len(description) > 1000:
            flash("Report description must be between 10 and 1000 characters.", "danger")
            return redirect(url_for("organization_details", org_id=org_id))

        db.execute(
            """
            INSERT INTO reports (organization_id, user_id, reported_by, reason, description, status)
            VALUES (?, ?, ?, ?, ?, 'Pending')
            """,
            (org_id, user_id, reported_by[:120], reason, description),
        )
        db.commit()
        flash(
            "Thank you. Your report has been submitted for administrator verification review.",
            "success",
        )
        return redirect(url_for("organization_details", org_id=org_id))

    @app.route("/organization/<int:org_id>/inquire", methods=["POST"])
    @_user_required
    def submit_inquiry(org_id: int):
        db = get_db()
        org = db.execute(
            "SELECT id, organization_name FROM organizations WHERE id = ? AND verification_status = 'Approved'",
            (org_id,),
        ).fetchone()
        if not org:
            abort(404)

        message = request.form.get("message", "").strip()
        next_target = request.form.get("next", "")
        if len(message) < 10 or len(message) > 1500:
            flash("Inquiry message must be between 10 and 1500 characters.", "danger")
            if next_target == "dashboard":
                return redirect(url_for("user_dashboard"))
            return redirect(url_for("organization_details", org_id=org_id))

        db.execute(
            """
            INSERT INTO contact_inquiries (user_id, organization_id, message, status)
            VALUES (?, ?, ?, 'Sent')
            """,
            (session["user_id"], org_id, message),
        )
        db.commit()
        flash(
            f"Your inquiry to {org['organization_name']} has been saved and recorded.",
            "success",
        )
        if next_target == "dashboard":
            return redirect(url_for("user_dashboard"))
        return redirect(url_for("organization_details", org_id=org_id))

    @app.route("/about")
    def about():
        return render_template("about.html")

    @app.route("/contact", methods=["GET", "POST"])
    def contact():
        if request.method == "POST":
            sender_name = request.form.get("sender_name", "").strip()
            sender_email = request.form.get("sender_email", "").strip().lower()
            subject = request.form.get("subject", "").strip()
            message = request.form.get("message", "").strip()

            if (
                len(sender_name) < 2
                or not EMAIL_REGEX.match(sender_email)
                or len(subject) < 3
                or len(message) < 10
            ):
                flash("Please fill out all contact fields accurately (message min 10 chars).", "danger")
                return render_template("contact.html"), 400

            db = get_db()
            db.execute(
                """
                INSERT INTO general_messages (sender_name, sender_email, subject, message)
                VALUES (?, ?, ?, ?)
                """,
                (sender_name[:120], sender_email[:150], subject[:180], message[:2000]),
            )
            db.commit()
            flash("Your message has been received by the Sahaaya coordination team.", "success")
            return redirect(url_for("contact"))

        return render_template("contact.html")

    # ------------------------------------------------------------------
    # Supporter Authentication & Dashboard
    # ------------------------------------------------------------------
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if session.get("role") == "user":
            return redirect(url_for("user_dashboard"))

        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            confirm_password = request.form.get("confirm_password", "")

            errors = []
            if len(full_name) < 2 or len(full_name) > 100:
                errors.append("Full name must be between 2 and 100 characters.")
            if not EMAIL_REGEX.match(email):
                errors.append("Please enter a valid email address.")
            if len(password) < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
                errors.append("Password must be at least 8 characters and include letters and numbers.")
            if password != confirm_password:
                errors.append("Password and confirm password do not match.")

            if errors:
                for err in errors:
                    flash(err, "danger")
                return render_template("register.html", full_name=full_name, email=email), 400

            db = get_db()
            existing = db.execute(
                "SELECT id FROM users WHERE email = ?", (email,)
            ).fetchone()
            if existing:
                flash("An account with this email address already exists.", "danger")
                return render_template("register.html", full_name=full_name, email=email), 409

            db.execute(
                """
                INSERT INTO users (full_name, email, password_hash, account_status)
                VALUES (?, ?, ?, 'Active')
                """,
                (full_name, email, generate_password_hash(password)),
            )
            db.commit()
            flash("Registration successful! Please log in with your credentials.", "success")
            return redirect(url_for("login"))

        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if session.get("role") == "user":
            return redirect(url_for("user_dashboard"))

        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            if not email or not password:
                flash("Email and password are required.", "danger")
                return render_template("login.html", email=email), 400

            db = get_db()
            user = db.execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            ).fetchone()

            if not user or not check_password_hash(user["password_hash"], password):
                flash("Invalid email or password.", "danger")
                return render_template("login.html", email=email), 401

            if user["account_status"] != "Active":
                flash("This account is currently suspended. Please contact an administrator.", "danger")
                return render_template("login.html", email=email), 403

            session.clear()
            session.permanent = True
            session["role"] = "user"
            session["user_id"] = user["id"]
            session["user_name"] = user["full_name"]
            session["user_email"] = user["email"]
            session["csrf_token"] = secrets.token_hex(32)

            flash(f"Welcome back, {user['full_name']}!", "success")
            next_url = request.args.get("next", "")
            if next_url.startswith("/") and not next_url.startswith("//") and not next_url.startswith("/admin"):
                return redirect(next_url)
            return redirect(url_for("user_dashboard"))

        return render_template("login.html")

    @app.route("/logout", methods=["POST"])
    def logout():
        role = session.get("role")
        session.clear()
        flash("You have been logged out securely.", "info")
        if role == "admin":
            return redirect(url_for("admin_login"))
        return redirect(url_for("index"))

    @app.route("/dashboard")
    @_user_required
    def user_dashboard():
        db = get_db()
        user = db.execute(
            "SELECT id, full_name, email, account_status, created_at FROM users WHERE id = ?",
            (session["user_id"],),
        ).fetchone()

        inquiries = db.execute(
            """
            SELECT ci.id, ci.message, ci.status, ci.created_at,
                   o.id AS org_id, o.organization_name, o.category, o.area, o.city,
                   o.contact_number, o.email AS org_email
            FROM contact_inquiries ci
            JOIN organizations o ON o.id = ci.organization_id
            WHERE ci.user_id = ?
            ORDER BY ci.created_at DESC, ci.id DESC
            """,
            (session["user_id"],),
        ).fetchall()

        verified_orgs = db.execute(
            """
            SELECT id, organization_name, category, area, city
            FROM organizations
            WHERE verification_status = 'Approved'
            ORDER BY organization_name ASC
            """
        ).fetchall()

        return render_template(
            "user_dashboard.html",
            user=user,
            inquiries=inquiries,
            verified_orgs=verified_orgs,
        )

    @app.route("/dashboard/inquire", methods=["POST"])
    @_user_required
    def dashboard_inquiry():
        org_id = request.form.get("organization_id", type=int)
        if not org_id:
            flash("Please select a verified organization.", "danger")
            return redirect(url_for("user_dashboard"))

        db = get_db()
        org = db.execute(
            "SELECT id, organization_name FROM organizations WHERE id = ? AND verification_status = 'Approved'",
            (org_id,),
        ).fetchone()
        if not org:
            flash("Selected organization is unavailable or not verified.", "danger")
            return redirect(url_for("user_dashboard"))

        message = request.form.get("message", "").strip()
        if len(message) < 10 or len(message) > 1500:
            flash("Inquiry message must be between 10 and 1500 characters.", "danger")
            return redirect(url_for("user_dashboard"))

        db.execute(
            """
            INSERT INTO contact_inquiries (user_id, organization_id, message, status)
            VALUES (?, ?, ?, 'Sent')
            """,
            (session["user_id"], org_id, message),
        )
        db.commit()
        flash(f"Inquiry sent to {org['organization_name']}.", "success")
        return redirect(url_for("user_dashboard"))

    # ------------------------------------------------------------------
    # Administrator Authentication & Dashboard
    # ------------------------------------------------------------------
    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))

        if request.method == "POST":
            identifier = request.form.get("identifier", "").strip()
            password = request.form.get("password", "")

            if not identifier or not password:
                flash("Username/email and password are required.", "danger")
                return render_template("admin_login.html", identifier=identifier), 400

            db = get_db()
            admin = db.execute(
                "SELECT * FROM admins WHERE username = ? OR email = ?",
                (identifier, identifier.lower()),
            ).fetchone()

            if not admin or not check_password_hash(admin["password_hash"], password):
                flash("Invalid administrator credentials.", "danger")
                return render_template("admin_login.html", identifier=identifier), 401

            session.clear()
            session.permanent = True
            session["role"] = "admin"
            session["admin_id"] = admin["id"]
            session["admin_username"] = admin["username"]
            session["csrf_token"] = secrets.token_hex(32)

            flash(f"Signed in as Administrator ({admin['username']}).", "success")
            return redirect(url_for("admin_dashboard"))

        return render_template("admin_login.html")

    @app.route("/admin/dashboard")
    @_admin_required
    def admin_dashboard():
        db = get_db()
        counts = {
            "total_users": db.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"],
            "total_orgs": db.execute("SELECT COUNT(*) AS c FROM organizations").fetchone()["c"],
            "verified_orgs": db.execute(
                "SELECT COUNT(*) AS c FROM organizations WHERE verification_status = 'Approved'"
            ).fetchone()["c"],
            "pending_orgs": db.execute(
                "SELECT COUNT(*) AS c FROM organizations WHERE verification_status = 'Pending'"
            ).fetchone()["c"],
            "correction_orgs": db.execute(
                "SELECT COUNT(*) AS c FROM organizations WHERE verification_status = 'Needs Correction'"
            ).fetchone()["c"],
            "rejected_orgs": db.execute(
                "SELECT COUNT(*) AS c FROM organizations WHERE verification_status = 'Rejected'"
            ).fetchone()["c"],
            "total_reports": db.execute("SELECT COUNT(*) AS c FROM reports").fetchone()["c"],
            "pending_reports": db.execute(
                "SELECT COUNT(*) AS c FROM reports WHERE status = 'Pending'"
            ).fetchone()["c"],
            "total_inquiries": db.execute("SELECT COUNT(*) AS c FROM contact_inquiries").fetchone()["c"],
        }

        recent_orgs = db.execute(
            """
            SELECT id, organization_name, category, area, city, verification_status, created_at
            FROM organizations
            ORDER BY id DESC
            LIMIT 5
            """
        ).fetchall()

        recent_reports = db.execute(
            """
            SELECT r.id, r.reason, r.status, r.reported_by, r.created_at,
                   o.id AS org_id, o.organization_name
            FROM reports r
            JOIN organizations o ON o.id = r.organization_id
            ORDER BY r.id DESC
            LIMIT 5
            """
        ).fetchall()

        analytics = compute_admin_analytics(db)
        return render_template(
            "admin_dashboard.html",
            counts=counts,
            recent_orgs=recent_orgs,
            recent_reports=recent_reports,
            analytics=analytics,
        )

    # ------------------------------------------------------------------
    # Admin Organization CRUD
    # ------------------------------------------------------------------
    @app.route("/admin/organizations")
    @_admin_required
    def manage_organizations():
        db = get_db()
        q = request.args.get("q", "").strip()[:100]
        status_filter = request.args.get("status", "").strip()
        category_filter = request.args.get("category", "").strip()

        where = ["1=1"]
        params = []
        if q:
            escaped = f"%{_escape_like(q)}%"
            where.append(
                "(o.organization_name LIKE ? ESCAPE '\\' OR o.area LIKE ? ESCAPE '\\' "
                "OR o.city LIKE ? ESCAPE '\\' OR o.pincode LIKE ? ESCAPE '\\')"
            )
            params.extend([escaped, escaped, escaped, escaped])
        if status_filter in app.config["VERIFICATION_STATUSES"]:
            where.append("o.verification_status = ?")
            params.append(status_filter)
        if category_filter in app.config["ORGANIZATION_CATEGORIES"]:
            where.append("o.category = ?")
            params.append(category_filter)

        orgs = db.execute(
            f"""
            SELECT o.*, COUNT(ar.id) AS req_count
            FROM organizations o
            LEFT JOIN assistance_requirements ar ON ar.organization_id = o.id
            WHERE {' AND '.join(where)}
            GROUP BY o.id
            ORDER BY o.updated_at DESC, o.id DESC
            """,
            params,
        ).fetchall()

        return render_template(
            "manage_organizations.html",
            organizations=orgs,
            q=q,
            status_filter=status_filter,
            category_filter=category_filter,
        )

    @app.route("/admin/organizations/add", methods=["GET", "POST"])
    @_admin_required
    def add_organization():
        if request.method == "POST":
            try:
                data = _validate_org_form(request.form, app.config)
                uploaded_name = _save_uploaded_image(request.files.get("image"), app)
            except ValueError as exc:
                flash(str(exc), "danger")
                return render_template("add_organization.html", form_data=request.form), 400

            image_filename = uploaded_name or DEFAULT_CATEGORY_IMAGES.get(
                data["category"], "org-shelter.svg"
            )

            db = get_db()
            cur = db.execute(
                """
                INSERT INTO organizations (
                    organization_name, category, description, address, area, city,
                    state, pincode, contact_number, email, facilities, image_filename,
                    verification_status, data_source, last_checked_date, is_sample_data
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?, ?, ?)
                """,
                (
                    data["organization_name"],
                    data["category"],
                    data["description"],
                    data["address"],
                    data["area"],
                    data["city"],
                    data["state"],
                    data["pincode"],
                    data["contact_number"],
                    data["email"],
                    data["facilities"],
                    image_filename,
                    data["data_source"],
                    data["last_checked_date"],
                    data["is_sample_data"],
                ),
            )
            org_id = int(cur.lastrowid)

            # Optional inline assistance requirements submitted with new organization
            req_cats = request.form.getlist("req_category[]")
            req_items = request.form.getlist("req_item_name[]")
            req_descs = request.form.getlist("req_description[]")
            req_qtys = request.form.getlist("req_quantity[]")
            req_prios = request.form.getlist("req_priority[]")

            for idx, item_name in enumerate(req_items):
                clean_item = item_name.strip()
                if not clean_item:
                    continue
                cat = req_cats[idx].strip() if idx < len(req_cats) else "Other"
                if cat not in app.config["REQUIREMENT_CATEGORIES"]:
                    cat = "Other"
                prio = req_prios[idx].strip() if idx < len(req_prios) else "Medium"
                if prio not in app.config["REQUIREMENT_PRIORITIES"]:
                    prio = "Medium"
                desc = req_descs[idx].strip() if idx < len(req_descs) else ""
                qty = req_qtys[idx].strip() if idx < len(req_qtys) else ""

                db.execute(
                    """
                    INSERT INTO assistance_requirements (
                        organization_id, requirement_category, item_name,
                        description, quantity_or_details, priority
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (org_id, cat, clean_item[:150], desc[:400], qty[:120], prio),
                )

            db.execute(
                """
                INSERT INTO verification_audit_logs (
                    organization_id, admin_id, action, previous_status, new_status, notes
                )
                VALUES (?, ?, 'Created Organization', '', 'Pending', 'Initial onboarding submission')
                """,
                (org_id, session["admin_id"]),
            )
            db.commit()
            flash(
                f"Organization '{data['organization_name']}' added with Pending verification status.",
                "success",
            )
            return redirect(url_for("verification_queue"))

        return render_template("add_organization.html", form_data={})

    @app.route("/admin/organizations/<int:org_id>/edit", methods=["GET", "POST"])
    @_admin_required
    def edit_organization(org_id: int):
        db = get_db()
        org = db.execute("SELECT * FROM organizations WHERE id = ?", (org_id,)).fetchone()
        if not org:
            abort(404)

        requirements = db.execute(
            "SELECT * FROM assistance_requirements WHERE organization_id = ? ORDER BY id ASC",
            (org_id,),
        ).fetchall()

        if request.method == "POST":
            try:
                data = _validate_org_form(request.form, app.config)
                uploaded_name = _save_uploaded_image(request.files.get("image"), app)
            except ValueError as exc:
                flash(str(exc), "danger")
                return render_template(
                    "edit_organization.html", org=org, requirements=requirements
                ), 400

            image_filename = org["image_filename"]
            if uploaded_name:
                _remove_uploaded_image(org["image_filename"], app)
                image_filename = uploaded_name
            elif not image_filename:
                image_filename = DEFAULT_CATEGORY_IMAGES.get(data["category"], "org-shelter.svg")

            core_changed = any(
                str(org[field]).strip() != str(data[field]).strip()
                for field in app.config["CORE_ORG_FIELDS"]
            )

            new_status = org["verification_status"]
            new_ver_date = org["verification_date"]
            reverify_triggered = False

            if org["verification_status"] == "Approved" and core_changed:
                new_status = "Pending"
                new_ver_date = None
                reverify_triggered = True

            db.execute(
                """
                UPDATE organizations
                SET organization_name = ?, category = ?, description = ?, address = ?,
                    area = ?, city = ?, state = ?, pincode = ?, contact_number = ?,
                    email = ?, facilities = ?, image_filename = ?,
                    verification_status = ?, verification_date = ?,
                    data_source = ?, last_checked_date = ?, is_sample_data = ?,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (
                    data["organization_name"],
                    data["category"],
                    data["description"],
                    data["address"],
                    data["area"],
                    data["city"],
                    data["state"],
                    data["pincode"],
                    data["contact_number"],
                    data["email"],
                    data["facilities"],
                    image_filename,
                    new_status,
                    new_ver_date,
                    data["data_source"],
                    data["last_checked_date"],
                    data["is_sample_data"],
                    org_id,
                ),
            )

            if reverify_triggered:
                db.execute(
                    """
                    INSERT INTO verification_audit_logs (
                        organization_id, admin_id, action, previous_status, new_status, notes
                    )
                    VALUES (?, ?, 'Edited Verified Core Details', 'Approved', 'Pending',
                            'Automatic re-verification triggered after core profile edit')
                    """,
                    (org_id, session["admin_id"]),
                )

            db.commit()
            if reverify_triggered:
                flash(
                    "Organization updated. Core verified details changed, so status was reset to Pending for re-verification.",
                    "warning",
                )
            else:
                flash("Organization details updated successfully.", "success")
            return redirect(url_for("manage_organizations"))

        return render_template("edit_organization.html", org=org, requirements=requirements)

    @app.route("/admin/organizations/<int:org_id>/delete", methods=["POST"])
    @_admin_required
    def delete_organization(org_id: int):
        db = get_db()
        org = db.execute("SELECT id, organization_name, image_filename FROM organizations WHERE id = ?", (org_id,)).fetchone()
        if not org:
            abort(404)

        _remove_uploaded_image(org["image_filename"], app)
        db.execute("DELETE FROM organizations WHERE id = ?", (org_id,))
        db.commit()
        flash(f"Organization '{org['organization_name']}' and its linked records were deleted.", "info")
        return redirect(url_for("manage_organizations"))

    # ------------------------------------------------------------------
    # Mandatory Organization Verification Workflow
    # ------------------------------------------------------------------
    @app.route("/admin/verification")
    @_admin_required
    def verification_queue():
        db = get_db()
        status_filter = request.args.get("status", "Pending").strip()
        if status_filter not in app.config["VERIFICATION_STATUSES"] and status_filter != "All":
            status_filter = "Pending"

        where_sql = "1=1" if status_filter == "All" else "o.verification_status = ?"
        params = [] if status_filter == "All" else [status_filter]

        orgs = db.execute(
            f"""
            SELECT o.*, a.username AS verified_by_name
            FROM organizations o
            LEFT JOIN admins a ON a.id = o.verified_by
            WHERE {where_sql}
            ORDER BY
                CASE o.verification_status
                    WHEN 'Pending' THEN 1
                    WHEN 'Needs Correction' THEN 2
                    WHEN 'Rejected' THEN 3
                    ELSE 4
                END,
                o.created_at DESC
            """,
            params,
        ).fetchall()

        req_rows = db.execute("SELECT * FROM assistance_requirements ORDER BY id ASC").fetchall()
        reqs_by_org: Dict[int, list] = {}
        for r in req_rows:
            reqs_by_org.setdefault(r["organization_id"], []).append(r)

        audit_rows = db.execute(
            """
            SELECT l.*, a.username AS admin_username
            FROM verification_audit_logs l
            LEFT JOIN admins a ON a.id = l.admin_id
            ORDER BY l.created_at DESC, l.id DESC
            LIMIT 20
            """
        ).fetchall()

        return render_template(
            "verification.html",
            organizations=orgs,
            reqs_by_org=reqs_by_org,
            audit_logs=audit_rows,
            status_filter=status_filter,
        )

    @app.route("/admin/verification/<int:org_id>", methods=["POST"])
    @_admin_required
    def process_verification(org_id: int):
        db = get_db()
        org = db.execute("SELECT * FROM organizations WHERE id = ?", (org_id,)).fetchone()
        if not org:
            abort(404)

        action = request.form.get("action", "").strip()
        notes = request.form.get("verification_notes", "").strip()[:500]

        action_map = {
            "approve": ("Approved", "Approved Organization"),
            "reject": ("Rejected", "Rejected Organization"),
            "correction": ("Needs Correction", "Returned for Correction"),
            "pending": ("Pending", "Moved to Pending Review"),
        }
        if action not in action_map:
            flash("Invalid verification action.", "danger")
            return redirect(url_for("verification_queue"))

        new_status, action_label = action_map[action]
        prev_status = org["verification_status"]

        if action in {"reject", "correction"} and len(notes) < 5:
            flash("Please provide verification notes (min 5 characters) when rejecting or returning for correction.", "warning")
            return redirect(url_for("verification_queue", status=prev_status))

        if new_status == "Approved":
            db.execute(
                """
                UPDATE organizations
                SET verification_status = 'Approved',
                    verification_notes = ?,
                    verified_by = ?,
                    verification_date = datetime('now'),
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (notes or "Verified by administrator.", session["admin_id"], org_id),
            )
        else:
            db.execute(
                """
                UPDATE organizations
                SET verification_status = ?,
                    verification_notes = ?,
                    verified_by = ?,
                    verification_date = NULL,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (new_status, notes, session["admin_id"], org_id),
            )

        db.execute(
            """
            INSERT INTO verification_audit_logs (
                organization_id, admin_id, action, previous_status, new_status, notes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (org_id, session["admin_id"], action_label, prev_status, new_status, notes),
        )
        db.commit()
        flash(f"{org['organization_name']} marked as '{new_status}'.", "success")
        return redirect(url_for("verification_queue", status=new_status))

    # ------------------------------------------------------------------
    # Manage Supporter Users
    # ------------------------------------------------------------------
    @app.route("/admin/users", methods=["GET"])
    @_admin_required
    def manage_users():
        db = get_db()
        q = request.args.get("q", "").strip()[:100]
        where_sql = "1=1"
        params = []
        if q:
            escaped = f"%{_escape_like(q)}%"
            where_sql = "(u.full_name LIKE ? ESCAPE '\\' OR u.email LIKE ? ESCAPE '\\')"
            params.extend([escaped, escaped])

        users = db.execute(
            f"""
            SELECT u.id, u.full_name, u.email, u.account_status, u.created_at,
                   COUNT(ci.id) AS inquiry_count
            FROM users u
            LEFT JOIN contact_inquiries ci ON ci.user_id = u.id
            WHERE {where_sql}
            GROUP BY u.id
            ORDER BY u.created_at DESC
            """,
            params,
        ).fetchall()

        inquiries = db.execute(
            """
            SELECT ci.id, ci.message, ci.status, ci.created_at,
                   u.full_name, u.email, o.organization_name
            FROM contact_inquiries ci
            JOIN users u ON u.id = ci.user_id
            JOIN organizations o ON o.id = ci.organization_id
            ORDER BY ci.created_at DESC
            LIMIT 20
            """
        ).fetchall()

        return render_template("manage_users.html", users=users, inquiries=inquiries, q=q)

    @app.route("/admin/users/<int:user_id>/toggle-status", methods=["POST"])
    @_admin_required
    def toggle_user_status(user_id: int):
        db = get_db()
        user = db.execute("SELECT id, full_name, account_status FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            abort(404)

        new_status = "Suspended" if user["account_status"] == "Active" else "Active"
        db.execute("UPDATE users SET account_status = ? WHERE id = ?", (new_status, user_id))
        db.commit()
        flash(f"User '{user['full_name']}' status changed to {new_status}.", "info")
        return redirect(url_for("manage_users"))

    @app.route("/admin/inquiries/<int:inquiry_id>/update", methods=["POST"])
    @_admin_required
    def update_inquiry_status(inquiry_id: int):
        db = get_db()
        inq = db.execute("SELECT id FROM contact_inquiries WHERE id = ?", (inquiry_id,)).fetchone()
        if not inq:
            abort(404)
        status = request.form.get("status", "").strip()
        if status not in app.config["INQUIRY_STATUSES"]:
            flash("Invalid inquiry status.", "danger")
            return redirect(url_for("manage_users"))
        db.execute("UPDATE contact_inquiries SET status = ? WHERE id = ?", (status, inquiry_id))
        db.commit()
        flash("Inquiry status updated.", "success")
        return redirect(url_for("manage_users"))

    # ------------------------------------------------------------------
    # Assistance Requirements Management
    # ------------------------------------------------------------------
    @app.route("/admin/requirements")
    @_admin_required
    def manage_requirements():
        db = get_db()
        org_filter = request.args.get("org_id", type=int)
        cat_filter = request.args.get("category", "").strip()
        prio_filter = request.args.get("priority", "").strip()

        where = ["1=1"]
        params = []
        if org_filter:
            where.append("ar.organization_id = ?")
            params.append(org_filter)
        if cat_filter in app.config["REQUIREMENT_CATEGORIES"]:
            where.append("ar.requirement_category = ?")
            params.append(cat_filter)
        if prio_filter in app.config["REQUIREMENT_PRIORITIES"]:
            where.append("ar.priority = ?")
            params.append(prio_filter)

        requirements = db.execute(
            f"""
            SELECT ar.*, o.organization_name, o.verification_status
            FROM assistance_requirements ar
            JOIN organizations o ON o.id = ar.organization_id
            WHERE {' AND '.join(where)}
            ORDER BY
                CASE ar.priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
                ar.updated_at DESC, ar.id DESC
            """,
            params,
        ).fetchall()

        organizations = db.execute(
            "SELECT id, organization_name, verification_status FROM organizations ORDER BY organization_name ASC"
        ).fetchall()

        return render_template(
            "manage_requirements.html",
            requirements=requirements,
            organizations=organizations,
            org_filter=org_filter,
            cat_filter=cat_filter,
            prio_filter=prio_filter,
        )

    @app.route("/admin/requirements/add", methods=["POST"])
    @_admin_required
    def add_requirement():
        org_id = request.form.get("organization_id", type=int)
        cat = request.form.get("requirement_category", "").strip()
        item_name = request.form.get("item_name", "").strip()
        description = request.form.get("description", "").strip()
        quantity = request.form.get("quantity_or_details", "").strip()
        priority = request.form.get("priority", "Medium").strip()
        redirect_to = request.form.get("redirect_to", "requirements")

        db = get_db()
        org = db.execute("SELECT id FROM organizations WHERE id = ?", (org_id,)).fetchone()
        if not org:
            flash("Selected organization does not exist.", "danger")
            return redirect(url_for("manage_requirements"))

        if (
            cat not in app.config["REQUIREMENT_CATEGORIES"]
            or priority not in app.config["REQUIREMENT_PRIORITIES"]
            or len(item_name) < 2
        ):
            flash("Valid category, priority, and item name (min 2 chars) are required.", "danger")
            if redirect_to == "edit_org":
                return redirect(url_for("edit_organization", org_id=org_id))
            return redirect(url_for("manage_requirements"))

        db.execute(
            """
            INSERT INTO assistance_requirements (
                organization_id, requirement_category, item_name,
                description, quantity_or_details, priority
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (org_id, cat, item_name[:150], description[:500], quantity[:150], priority),
        )
        db.commit()
        flash(f"Requirement '{item_name}' added.", "success")
        if redirect_to == "edit_org":
            return redirect(url_for("edit_organization", org_id=org_id))
        return redirect(url_for("manage_requirements"))

    @app.route("/admin/requirements/<int:req_id>/edit", methods=["POST"])
    @_admin_required
    def edit_requirement(req_id: int):
        db = get_db()
        req_row = db.execute(
            "SELECT * FROM assistance_requirements WHERE id = ?", (req_id,)
        ).fetchone()
        if not req_row:
            abort(404)

        cat = request.form.get("requirement_category", "").strip()
        item_name = request.form.get("item_name", "").strip()
        description = request.form.get("description", "").strip()
        quantity = request.form.get("quantity_or_details", "").strip()
        priority = request.form.get("priority", "").strip()
        redirect_to = request.form.get("redirect_to", "requirements")

        if (
            cat not in app.config["REQUIREMENT_CATEGORIES"]
            or priority not in app.config["REQUIREMENT_PRIORITIES"]
            or len(item_name) < 2
        ):
            flash("Invalid assistance requirement input.", "danger")
            return redirect(url_for("manage_requirements"))

        db.execute(
            """
            UPDATE assistance_requirements
            SET requirement_category = ?, item_name = ?, description = ?,
                quantity_or_details = ?, priority = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (cat, item_name[:150], description[:500], quantity[:150], priority, req_id),
        )
        db.commit()
        flash(f"Requirement '{item_name}' updated.", "success")
        if redirect_to == "edit_org":
            return redirect(url_for("edit_organization", org_id=req_row["organization_id"]))
        return redirect(url_for("manage_requirements"))

    @app.route("/admin/requirements/<int:req_id>/delete", methods=["POST"])
    @_admin_required
    def delete_requirement(req_id: int):
        db = get_db()
        req_row = db.execute(
            "SELECT id, organization_id, item_name FROM assistance_requirements WHERE id = ?",
            (req_id,),
        ).fetchone()
        if not req_row:
            abort(404)

        redirect_to = request.form.get("redirect_to", "requirements")
        db.execute("DELETE FROM assistance_requirements WHERE id = ?", (req_id,))
        db.commit()
        flash(f"Removed requirement '{req_row['item_name']}'.", "info")
        if redirect_to == "edit_org":
            return redirect(url_for("edit_organization", org_id=req_row["organization_id"]))
        return redirect(url_for("manage_requirements"))

    # ------------------------------------------------------------------
    # Report Management
    # ------------------------------------------------------------------
    @app.route("/admin/reports")
    @_admin_required
    def manage_reports():
        db = get_db()
        q = request.args.get("q", "").strip()[:100]
        status_filter = request.args.get("status", "").strip()

        where = ["1=1"]
        params = []
        if q:
            escaped = f"%{_escape_like(q)}%"
            where.append(
                "(o.organization_name LIKE ? ESCAPE '\\' OR r.reason LIKE ? ESCAPE '\\' "
                "OR r.description LIKE ? ESCAPE '\\' OR r.reported_by LIKE ? ESCAPE '\\')"
            )
            params.extend([escaped, escaped, escaped, escaped])
        if status_filter in app.config["REPORT_STATUSES"]:
            where.append("r.status = ?")
            params.append(status_filter)

        reports = db.execute(
            f"""
            SELECT r.*, o.organization_name, o.verification_status, o.area, o.city
            FROM reports r
            JOIN organizations o ON o.id = r.organization_id
            WHERE {' AND '.join(where)}
            ORDER BY
                CASE r.status WHEN 'Pending' THEN 1 WHEN 'Reviewed' THEN 2 ELSE 3 END,
                r.created_at DESC
            """,
            params,
        ).fetchall()

        return render_template(
            "manage_reports.html",
            reports=reports,
            q=q,
            status_filter=status_filter,
        )

    @app.route("/admin/reports/<int:report_id>/update", methods=["POST"])
    @_admin_required
    def update_report(report_id: int):
        db = get_db()
        report = db.execute(
            """
            SELECT r.*, o.organization_name, o.verification_status
            FROM reports r
            JOIN organizations o ON o.id = r.organization_id
            WHERE r.id = ?
            """,
            (report_id,),
        ).fetchone()
        if not report:
            abort(404)

        new_status = request.form.get("status", "").strip()
        admin_notes = request.form.get("admin_notes", "").strip()[:500]
        trigger_reverify = request.form.get("trigger_reverification") == "1"

        if new_status not in app.config["REPORT_STATUSES"]:
            flash("Invalid report status selected.", "danger")
            return redirect(url_for("manage_reports"))

        db.execute(
            """
            UPDATE reports
            SET status = ?, admin_notes = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (new_status, admin_notes, report_id),
        )

        if trigger_reverify and report["verification_status"] == "Approved":
            db.execute(
                """
                UPDATE organizations
                SET verification_status = 'Needs Correction',
                    verification_notes = ?,
                    verification_date = NULL,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (
                    f"Flagged for re-verification from Report #{report_id}: {admin_notes or report['reason']}",
                    report["organization_id"],
                ),
            )
            db.execute(
                """
                INSERT INTO verification_audit_logs (
                    organization_id, admin_id, action, previous_status, new_status, notes
                )
                VALUES (?, ?, 'Report Triggered Re-verification', 'Approved', 'Needs Correction', ?)
                """,
                (
                    report["organization_id"],
                    session["admin_id"],
                    admin_notes or report["reason"],
                ),
            )

        db.commit()
        flash("Report status updated successfully.", "success")
        return redirect(url_for("manage_reports"))

    # ------------------------------------------------------------------
    # Error Handlers
    # ------------------------------------------------------------------
    @app.errorhandler(403)
    def forbidden_error(_error):
        return render_template("403.html"), 403

    @app.errorhandler(404)
    def not_found_error(_error):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(_error):
        return render_template("500.html"), 500

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(
        host="127.0.0.1",
        port=int(os.environ.get("PORT", 5000)),
        debug=os.environ.get("FLASK_ENV", "development") == "development",
    )
