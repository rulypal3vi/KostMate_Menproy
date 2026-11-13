
import sqlite3

DB_NAME = "kostmate.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    conn = get_connection()
    cursor = conn.cursor()

    # Tabel kamar
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number TEXT UNIQUE NOT NULL,
            price INTEGER NOT NULL,
            status TEXT DEFAULT 'Kosong'
        )
    """)

    # Tabel penghuni
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tenants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            room_id INTEGER,
            start_date TEXT,
            end_date TEXT,
            FOREIGN KEY (room_id) REFERENCES rooms(id)
        )
    """)

    # Tabel pembayaran
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            due_date TEXT NOT NULL,
            payment_date TEXT,
            status TEXT DEFAULT 'Belum Lunas',
            FOREIGN KEY (tenant_id) REFERENCES tenants(id)
        )
    """)

    # Tabel keluhan
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            report_date TEXT NOT NULL,
            status TEXT DEFAULT 'Baru',
            FOREIGN KEY (tenant_id) REFERENCES tenants(id)
        )
    """)

    # Tabel pengeluaran
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount INTEGER NOT NULL,
            expense_date TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()
