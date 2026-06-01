import sqlite3
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
                completed_at TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS janitors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        
        cursor = conn.execute("SELECT COUNT(*) as count FROM janitors")
        if cursor.fetchone()["count"] == 0:
            conn.execute("INSERT INTO janitors (name) VALUES ('Pedel 1')")
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
        location = request.form.get("location")
        reporter_name = request.form.get("reporter_name")

        with get_db() as conn:
            conn.execute(
                "INSERT INTO tasks (title, description, location, reporter_name) VALUES (?, ?, ?, ?)",
                (title, description, location, reporter_name)
            )
            conn.commit()
        
        flash("Opgaven er oprettet succesfuldt!")
        return redirect("/")

    prefilled_location = request.args.get("location", "")
    return render_template("create_task.html", prefilled_location=prefilled_location)

@app.route("/admin")
def admin_panel():
    with get_db() as conn:
        tasks = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
        janitors = conn.execute("SELECT * FROM janitors ORDER BY name ASC").fetchall()
    return render_template("admin.html", tasks=tasks, janitors=janitors)

@app.route("/generate_qr")
def generate_qr():
    return render_template("generate_qr.html")

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

if __name__ == "__main__":
    app.run(debug=True, port=5001)