from database import get_db, init_db

init_db()  # make sure the table exists first

dummy_tasks = [
    {
        'title': 'Skift lyspære',
        'description': 'Lyspære er gået i gang 3 på 1. sal.',
        'location': 'Bygning A, 1. sal, Gang 3',
        'status': 'Ny',
        'assigned_janitor': None
    },
    {
        'title': 'Reparér vindue',
        'description': 'Vinduesgrebet er løst og skal strammes.',
        'location': 'Bygning B, Klasseværelse 12',
        'status': 'I gang',
        'assigned_janitor': 'Henrik'
    },
    {
        'title': 'Rengøring af kælder',
        'description': 'Kælderrummet trænger til en grundig rengøring.',
        'location': 'Kælderen under Bygning A',
        'status': 'Ny',
        'assigned_janitor': None
    },
]

conn = get_db()
cursor = conn.cursor()

cursor.executemany('''
    INSERT INTO tasks (title, description, location, status, assigned_janitor)
    VALUES (:title, :description, :location, :status, :assigned_janitor)
''', dummy_tasks)

conn.commit()
conn.close()

print("✅ Dummy opgaver indsat i databasen.")