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
    
    # NY TABEL: Gentagne opgaver (Årshjulet)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recurring_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            location TEXT,
            assigned_janitor TEXT,
            frequency TEXT,
            period_start TEXT,
            period_end TEXT,
            last_generated TEXT,
            created_at TEXT
        )
    ''')
    
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


# --- FUNKTIONER TIL GENTAGNE OPGAVER (ÅRSHJULET) ---
def get_all_recurring_tasks():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recurring_tasks ORDER BY created_at DESC")
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tasks

def insert_recurring_task(title, description, location, assigned_janitor, frequency, period_start, period_end):
    conn = get_db()
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute('''
        INSERT INTO recurring_tasks (title, description, location, assigned_janitor, frequency, period_start, period_end, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (title, description, location, assigned_janitor, frequency, period_start, period_end, created_at))
    conn.commit()
    conn.close()

def update_recurring_task(task_id, title, description, location, assigned_janitor, frequency, period_start, period_end):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE recurring_tasks 
        SET title = ?, description = ?, location = ?, assigned_janitor = ?, frequency = ?, period_start = ?, period_end = ?
        WHERE id = ?
    ''', (title, description, location, assigned_janitor, frequency, period_start, period_end, task_id))
    conn.commit()
    conn.close()

def delete_recurring_task(task_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM recurring_tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

def update_recurring_task_last_generated(task_id, last_generated):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE recurring_tasks SET last_generated = ? WHERE id = ?", (last_generated, task_id))
    conn.commit()
    conn.close()