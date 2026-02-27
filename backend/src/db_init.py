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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS pending_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL,
    admin_wallet TEXT NOT NULL,
    cid TEXT NOT NULL,
    ch TEXT NOT NULL,
    record_id TEXT NOT NULL,
    tx_data TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at INTEGER
);
    """)

    conn.commit()
    conn.close()
