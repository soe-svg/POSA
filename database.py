import sqlite3
from datetime import datetime

DB_NAME = "posa.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Eksisterende tabel til opgaver (Nu med reporter_name)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            location TEXT,
            reporter_name TEXT,
            status TEXT DEFAULT 'Ny',
            assigned_janitor TEXT,
            created_at TEXT,
            completed_at TEXT
        )
    ''')
    
    # NY TABEL: Til faste, registrerede lokationer med QR-koder
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    ''')
    
    # LILLE DATABASEOPDATERING: Hvis databasen allerede findes på computeren fra tidligere sprints,
    # så tilføjer vi 'reporter_name' kolonnen automatisk, så programmet ikke dør.
    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN reporter_name TEXT")
    except sqlite3.OperationalError:
        # Kolonnen findes allerede i forvejen, alt er godt.
        pass
    
    conn.commit()
    conn.close()

# --- OPTERTSFUNKTIONER (TASKS) ---
def insert_task(title, description, location, reporter_name):
    conn = get_db()
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute('''
        INSERT INTO tasks (title, description, location, reporter_name, status, created_at)
        VALUES (?, ?, ?, ?, 'Ny', ?)
    ''', (title, description, location, reporter_name, created_at))
    conn.commit()
    conn.close()

def update_task(task_id, status, assigned_janitor):
    conn = get_db()
    cursor = conn.cursor()
    
    if status == 'Færdig':
        completed_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor.execute('''
            UPDATE tasks 
            SET status = ?, assigned_janitor = ?, completed_at = ?
            WHERE id = ?
        ''', (status, assigned_janitor, completed_at, task_id))
    else:
        cursor.execute('''
            UPDATE tasks 
            SET status = ?, assigned_janitor = ?, completed_at = NULL
            WHERE id = ?
        ''', (status, assigned_janitor, task_id))
        
    conn.commit()
    conn.close()

def delete_task(task_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()

def get_tasks_filtered(view):
    conn = get_db()
    cursor = conn.cursor()
    
    # Hent aktive opgaver (Ny, I gang) - Nyeste først
    if view == 'all':
        cursor.execute("SELECT * FROM tasks WHERE status != 'Færdig' ORDER BY id DESC")
    elif view == 'unassigned':
        cursor.execute("SELECT * FROM tasks WHERE status != 'Færdig' AND (assigned_janitor IS NULL OR assigned_janitor = '') ORDER BY id DESC")
    else:
        cursor.execute("SELECT * FROM tasks WHERE status != 'Færdig' AND assigned_janitor = ? ORDER BY id DESC", (view,))
    active_tasks = [dict(row) for row in cursor.fetchall()]
    
    # Hent færdigmeldte opgaver - Nyeste færdigmeldte først
    if view == 'all':
        cursor.execute("SELECT * FROM tasks WHERE status = 'Færdig' ORDER BY completed_at DESC")
    elif view == 'unassigned':
        cursor.execute("SELECT * FROM tasks WHERE status = 'Færdig' AND (assigned_janitor IS NULL OR assigned_janitor = '') ORDER BY completed_at DESC")
    else:
        cursor.execute("SELECT * FROM tasks WHERE status = 'Færdig' AND assigned_janitor = ? ORDER BY completed_at DESC", (view,))
    finished_tasks = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return active_tasks, finished_tasks


# --- FUNKTIONER TIL FASTE LOKATIONER ---
def get_all_locations():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM locations ORDER BY name ASC")
    locations = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return locations

def insert_location(name):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO locations (name) VALUES (?)", (name,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()

def delete_location(loc_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM locations WHERE id = ?", (loc_id,))
    conn.commit()
    conn.close()