import sqlite3
import qrcode
import io
import base64
import urllib.parse
from flask import Flask, render_template, request, redirect, flash

app = Flask(__name__)
app.secret_key = "posa_hemmelig_noegle"

DATABASE = "posa.db"

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                location TEXT,
                reporter_name TEXT,
                status TEXT DEFAULT 'Ny',
                assigned_janitor TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                internal_notes TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS janitors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        
        cursor = conn.execute("SELECT COUNT(*) as count FROM janitors")
        if cursor.fetchone()["count"] == 0:
            conn.execute("INSERT INTO janitors (name) VALUES ('Pedel 1')")

        # Ensure old tasks without timestamps get a fallback creation time
        conn.execute("UPDATE tasks SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL OR created_at = ''")
        try:
            conn.execute("ALTER TABLE tasks ADD COLUMN internal_notes TEXT")
        except sqlite3.OperationalError:
            pass
        conn.commit()

init_db()

@app.route("/")
def index():
    view = request.args.get("view", "all")
    
    with get_db() as conn:
        janitors_list = [row["name"] for row in conn.execute("SELECT name FROM janitors ORDER BY name ASC").fetchall()]
        
        active_query = "SELECT * FROM tasks WHERE status != 'Færdig'"
        finished_query = "SELECT * FROM tasks WHERE status = 'Færdig'"
        params = []

        if view == "unassigned":
            active_query += " AND (assigned_janitor IS NULL OR assigned_janitor = '' OR assigned_janitor = 'None')"
        elif view in janitors_list:
            active_query += " AND assigned_janitor = ?"
            params.append(view)

        active_query += " ORDER BY created_at DESC"
        finished_query += " ORDER BY completed_at DESC LIMIT 10"

        active_tasks = conn.execute(active_query, params).fetchall()
        finished_tasks = conn.execute(finished_query).fetchall()

    return render_template(
        "index.html", 
        active_tasks=active_tasks, 
        finished_tasks=finished_tasks, 
        view=view,
        janitors=janitors_list
    )

@app.route("/create", methods=["GET", "POST"])
def create_task():
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        # Determine location from select or custom input
        location_select = request.form.get("location_select")
        location_custom = request.form.get("location_custom")
        if location_custom and location_custom.strip():
            location = location_custom.strip()
        elif location_select and location_select != "__custom__":
            location = location_select
        else:
            location = ""
        reporter_name = request.form.get("reporter_name")

        with get_db() as conn:
            conn.execute(
                "INSERT INTO tasks (title, description, location, reporter_name, created_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
                (title, description, location, reporter_name)
            )
            conn.commit()
        
        flash("Opgaven er oprettet succesfuldt!")
        return redirect("/")

    prefilled_location = request.args.get("location", "")
    # Fetch saved locations to populate dropdown
    with get_db() as conn:
        saved_locations = conn.execute("SELECT * FROM locations ORDER BY name ASC").fetchall()

    return render_template("create_task.html", prefilled_location=prefilled_location, saved_locations=saved_locations)

@app.route("/admin")
def admin_panel():
    with get_db() as conn:
        tasks = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
        janitors = conn.execute("SELECT * FROM janitors ORDER BY name ASC").fetchall()
    return render_template("admin.html", tasks=tasks, janitors=janitors)

@app.route("/admin/print_daily_tasks")
def print_daily_tasks():
    with get_db() as conn:
        janitors = [row["name"] for row in conn.execute("SELECT name FROM janitors ORDER BY name ASC").fetchall()]
        rows = conn.execute(
            "SELECT * FROM tasks WHERE status != 'Færdig' AND assigned_janitor IS NOT NULL AND assigned_janitor != '' ORDER BY assigned_janitor ASC, created_at DESC"
        ).fetchall()

    grouped_tasks = {name: [] for name in janitors}
    for row in rows:
        janitor_name = row["assigned_janitor"]
        if janitor_name not in grouped_tasks:
            grouped_tasks[janitor_name] = []
        grouped_tasks[janitor_name].append(row)

    return render_template("print_daily.html", grouped_tasks=grouped_tasks, janitors=janitors)

@app.route("/generate_qr", methods=["GET", "POST"])
def generate_qr():
    qr_base64 = None
    target_url = None
    location = None

    # Handle POST: create a new saved location then redirect to GET view for QR
    if request.method == "POST":
        location_name = request.form.get("location", "").strip()
        if location_name:
            try:
                with get_db() as conn:
                    conn.execute(
                        "INSERT INTO locations (name) VALUES (?)",
                        (location_name,)
                    )
                    conn.commit()
            except sqlite3.IntegrityError:
                pass
            return redirect(f"/generate_qr?location={urllib.parse.quote(location_name)}")
        else:
            flash("Indtast venligst en lokation.", "warning")

    # If a location is provided via GET (e.g., clicking 'Hent QR'), generate the QR
    get_location = request.args.get("location")
    if get_location:
        location = get_location
        # Build target URL that pre-fills the create-task form
        target_url = request.url_root.rstrip("/") + "/create?location=" + urllib.parse.quote(location)

        try:
            qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M)
            qr.add_data(target_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            img_buffer = io.BytesIO()
            img.save(img_buffer, format="PNG")
            qr_base64 = base64.b64encode(img_buffer.getvalue()).decode("utf-8")
        except Exception as e:
            flash(f"Kunne ikke generere QR-kode: {e}", "warning")

    # Fetch saved locations for display
    with get_db() as conn:
        saved_locations = conn.execute("SELECT * FROM locations ORDER BY name ASC").fetchall()

    return render_template("generate_qr.html", saved_locations=saved_locations, qr_base64=qr_base64, target_url=target_url, location=location)

@app.route("/admin/update_task/<int:task_id>", methods=["POST"])
def update_task(task_id):
    status = request.form.get("status")
    assigned_janitor = request.form.get("assigned_janitor")
    
    with get_db() as conn:
        if status == "Færdig":
            conn.execute(
                "UPDATE tasks SET status = ?, assigned_janitor = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, assigned_janitor, task_id)
            )
        else:
            conn.execute(
                "UPDATE tasks SET status = ?, assigned_janitor = ?, completed_at = NULL WHERE id = ?",
                (status, assigned_janitor, task_id)
            )
        conn.commit()
    
    flash("Opgaven blev opdateret!")
    return redirect("/admin")

@app.route("/admin/update_notes/<int:task_id>", methods=["POST"])
def update_notes(task_id):
    notes = request.form.get("internal_notes", "").strip()
    with get_db() as conn:
        conn.execute("UPDATE tasks SET internal_notes = ? WHERE id = ?", (notes, task_id))
        conn.commit()
    flash("Interne noter opdateret!")
    return redirect("/admin")

@app.route("/admin/delete_task/<int:task_id>", methods=["POST"])
def delete_task(task_id):
    with get_db() as conn:
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
    flash("Opgaven blev slettet succesfuldt.")
    return redirect("/admin")

@app.route("/admin/add_janitor", methods=["POST"])
def add_janitor():
    name = request.form.get("janitor_name").strip()
    if name:
        try:
            with get_db() as conn:
                conn.execute("INSERT INTO janitors (name) VALUES (?)", (name,))
                conn.commit()
            flash(f"'{name}' er nu oprettet som pedelmedhjælper!")
        except sqlite3.IntegrityError:
            flash("En pedelmedhjælper med det navn eksisterer allerede!", "warning")
    return redirect("/admin")

@app.route("/admin/delete_janitor/<int:janitor_id>", methods=["POST"])
def delete_janitor(janitor_id):
    with get_db() as conn:
        conn.execute("DELETE FROM janitors WHERE id = ?", (janitor_id,))
        conn.commit()
    flash("Pedelmedhjælperen blev slettet fra systemet.")
    return redirect("/admin")


@app.route("/delete_location/<int:loc_id>", methods=["POST"])
def delete_location_route(loc_id):
    with get_db() as conn:
        conn.execute("DELETE FROM locations WHERE id = ?", (loc_id,))
        conn.commit()
    flash("Lokation slettet.")
    return redirect("/generate_qr")


@app.route("/print_all_qr")
def print_all_qr():
    qr_list = []
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM locations ORDER BY name ASC").fetchall()

    for row in rows:
        name = row["name"] if isinstance(row, sqlite3.Row) else row["name"]
        target_url = request.url_root.rstrip("/") + "/create?location=" + urllib.parse.quote(name)
        try:
            qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M)
            qr.add_data(target_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            qr_list.append({"name": name, "qr_base64": b64})
        except Exception:
            # skip problematic rows but continue
            continue

    return render_template("print_all_qr.html", qr_list=qr_list)

if __name__ == "__main__":
    app.run(debug=True, port=5001)