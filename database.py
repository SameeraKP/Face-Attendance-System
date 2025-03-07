import sqlite3

conn = sqlite3.connect("attendance.db")
cursor = conn.cursor()

# Create students table with 'is_verified' column
cursor.execute('''CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    roll_no TEXT NOT NULL UNIQUE,
                    email TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL,
                    is_verified INTEGER DEFAULT 0)''')

# Create an admin table (for login)
cursor.execute('''CREATE TABLE IF NOT EXISTS admin (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL)''')

conn.commit()
conn.close()
