import sqlite3

def init_db():
    conn = sqlite3.connect("auth.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT UNIQUE,
        email TEXT UNIQUE,
        wallet TEXT UNIQUE,
        role TEXT,
        verified INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS otp (
        email TEXT,
        code TEXT,
        expires INTEGER
    )
    """)

    conn.commit()
    conn.close()
