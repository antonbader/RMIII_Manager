import sqlite3
import os

DB_PATH = 'rm3_daten.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Tabellen für Klassenverwaltung
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Klassen (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        beschreibung TEXT
    )
    ''')

    # Tabellen für Schützenverwaltung
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Schuetzen (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )
    ''')

    # Tabellen für Turnierverwaltung
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Turniere (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        zeitraum TEXT
    )
    ''')

    # Mapping Turnier -> Klasse (mit Einstellungen)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Turnier_Klassen (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        turnier_id INTEGER,
        klasse_id INTEGER,
        edited BOOLEAN DEFAULT 0,
        sch TEXT DEFAULT 'LG10',
        ria TEXT DEFAULT 'ZR',
        tea TEXT DEFAULT 'KT',
        teg INTEGER DEFAULT 1000,
        ssc INTEGER DEFAULT 1,
        sge INTEGER DEFAULT 40,
        FOREIGN KEY(turnier_id) REFERENCES Turniere(id),
        FOREIGN KEY(klasse_id) REFERENCES Klassen(id)
    )
    ''')

    # Mapping Turnier -> Schütze -> Klasse (für die Auswertung)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Turnier_Schuetzen_Klassen (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        turnier_id INTEGER,
        schuetze_id INTEGER,
        klasse_id INTEGER,
        FOREIGN KEY(turnier_id) REFERENCES Turniere(id),
        FOREIGN KEY(schuetze_id) REFERENCES Schuetzen(id),
        FOREIGN KEY(klasse_id) REFERENCES Klassen(id)
    )
    ''')

    # Ergebnisse Tabelle
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Ergebnisse (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        turnier_schuetze_klasse_id INTEGER,
        schuss_nr INTEGER,
        ringzahl REAL,
        teiler REAL,
        winkel REAL,
        gueltigkeit TEXT,
        FOREIGN KEY(turnier_schuetze_klasse_id) REFERENCES Turnier_Schuetzen_Klassen(id)
    )
    ''')


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

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
