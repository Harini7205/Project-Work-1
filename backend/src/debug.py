import sqlite3
conn = sqlite3.connect("auth.db")
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print(cur.fetchall())
cur.execute("SELECT *FROM users")
print(cur.fetchall())
cur.execute("SELECT *FROM otp")
print(cur.fetchall())
