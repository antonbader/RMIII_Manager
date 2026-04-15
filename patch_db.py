import sqlite3

with open('db_manager.py', 'r') as f:
    content = f.read()

new_tables = """
    # Tabellen für Shootcup
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Shootcup_Presets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        sch TEXT DEFAULT 'LG10',
        ria TEXT DEFAULT 'ZR',
        tea TEXT DEFAULT 'KT',
        teg INTEGER DEFAULT 1000,
        ssc INTEGER DEFAULT 1,
        sge INTEGER DEFAULT 40
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Shootcup_Ergebnisse (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        schuss_nr INTEGER,
        ringzahl REAL,
        teiler REAL,
        winkel REAL,
        gueltigkeit TEXT
    )
    ''')
"""

if 'Shootcup_Presets' not in content:
    content = content.replace('conn.commit()', new_tables + '\n    conn.commit()')
    with open('db_manager.py', 'w') as f:
        f.write(content)
