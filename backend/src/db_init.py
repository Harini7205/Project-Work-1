import sqlite3

def init_db():
    conn = sqlite3.connect("auth.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    email TEXT UNIQUE NOT NULL,
    wallet TEXT UNIQUE NOT NULL,

    role TEXT CHECK(role IN ('patient','doctor','admin')) NOT NULL,

    patient_id TEXT UNIQUE,     -- only for patients
    verified INTEGER DEFAULT 0,

    created_at INTEGER
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
