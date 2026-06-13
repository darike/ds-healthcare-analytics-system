import os
import pyodbc
import hashlib
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={os.getenv('SQL_SERVER')};"
        f"DATABASE={os.getenv('SQL_DATABASE')};"
        f"TrustServerCertificate=yes;"
        f"Trusted_Connection=yes;"
    )
    return pyodbc.connect(conn_str)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def initialize_database():
    conn   = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Users' AND xtype='U')
        CREATE TABLE Users (
            Id           INT IDENTITY(1,1) PRIMARY KEY,
            Username     VARCHAR(50)  NOT NULL UNIQUE,
            PasswordHash VARCHAR(64)  NOT NULL,
            Role         VARCHAR(20)  NOT NULL,
            Doctor_name  VARCHAR(50)  NULL,
            Speciality   VARCHAR(100) NULL
        )
    """)
    conn.commit()

    # Safe to run on existing DBs — skips if column already exists
    cursor.execute("""
        IF NOT EXISTS (
            SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'Users' AND COLUMN_NAME = 'Doctor_name'
        )
        ALTER TABLE Users ADD Doctor_name VARCHAR(50) NULL
    """)
    conn.commit()

    cursor.execute("""
        IF NOT EXISTS (
            SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'Users' AND COLUMN_NAME = 'Speciality'
        )
        ALTER TABLE Users ADD Speciality VARCHAR(100) NULL
    """)
    conn.commit()

    cursor.execute("SELECT Username FROM Users WHERE Role = 'Admin'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO Users (Username, PasswordHash, Role) VALUES ('admin', ?, 'Admin')",
            (hash_password("admin123"),)
        )
        conn.commit()
    conn.close()

def get_system_statistics():
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT Role, COUNT(*) FROM Users GROUP BY Role")
        rows   = cursor.fetchall()
        conn.close()
        stats  = {'Doctor': 0, 'Patient': 0}
        for row in rows:
            if row[0] in stats:
                stats[row[0]] = row[1]
        return stats
    except Exception:
        return {'Doctor': 0, 'Patient': 0}

def create_user_profile(username, password, role, doctor_name=None, speciality=None):
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()

        if role == 'Admin':
            conn.close()
            return False, "System restriction: Additional Admin allocation unauthorized."

        cursor.execute("SELECT Username FROM Users WHERE Username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return False, "Identifier already exists in database index."

        cursor.execute(
            "INSERT INTO Users (Username, PasswordHash, Role, Doctor_name, Speciality) VALUES (?, ?, ?, ?, ?)",
            (username, hash_password(password), role, doctor_name, speciality)
        )
        conn.commit()
        conn.close()
        return True, f"Successfully created {role} profile."
    except Exception as e:
        return False, f"Database write error: {str(e)}"

def verify_user(username, password):
    try:
        conn     = get_db_connection()
        cursor   = conn.cursor()
        pwd_hash = hash_password(password)
        cursor.execute(
            "SELECT Role FROM Users WHERE Username = ? AND PasswordHash = ?",
            (username, pwd_hash)
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return True, row[0]
        return False, "Invalid username or password credentials."
    except Exception as e:
        return False, f"Database connection failure: {str(e)}"