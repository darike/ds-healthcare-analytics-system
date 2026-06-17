import pandas as pd

try:
    from core.auth import get_db_connection
except ImportError:
    from auth import get_db_connection


def initialize_appointment_table():
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        IF NOT EXISTS (
            SELECT * FROM sysobjects
            WHERE name='Appointments' AND xtype='U'
        )
        CREATE TABLE Appointments (
            Id               INT IDENTITY PRIMARY KEY,
            Patient_name     VARCHAR(255),
            Doctor_name      VARCHAR(255),
            Appointment_date DATE,
            Appointment_time VARCHAR(20),
            Reason           VARCHAR(255),
            Status           VARCHAR(20)
        )
    """)
    conn.commit()
    conn.close()


def get_doctors():
    """Returns list of dicts with doctor username and speciality."""
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Username, Speciality FROM Users WHERE Role = 'Doctor'")
    rows   = cursor.fetchall()
    conn.close()
    return [
        {
            'username':   row[0],
            'speciality': row[1] if row[1] else 'General Physician',
        }
        for row in rows
    ]


def get_patient_users():
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Username FROM Users WHERE Role = 'Patient'")
    patients = [row[0] for row in cursor.fetchall()]
    conn.close()
    return patients


def book_appointment(patient_name, doctor_name, date, time, reason):
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Appointments
        (Patient_name, Doctor_name, Appointment_date, Appointment_time, Reason, Status)
        VALUES (?, ?, ?, ?, ?, 'Booked')
    """, (patient_name, doctor_name, date, time, reason))
    conn.commit()
    conn.close()


def get_patient_appointments(patient_name):
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT Id, Doctor_name, Appointment_date, Appointment_time, Reason, Status
        FROM Appointments
        WHERE Patient_name = ?
        ORDER BY Appointment_date DESC
    """, (patient_name,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_doctor_appointments(doctor_name):
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT Id, Patient_name, Appointment_date, Appointment_time, Reason, Status
        FROM Appointments
        WHERE Doctor_name = ?
        ORDER BY Appointment_date DESC
    """, (doctor_name,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def cancel_appointment(appointment_id):
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Appointments SET Status = 'Cancelled' WHERE Id = ?", (appointment_id,))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    initialize_appointment_table()
    print("Doctors available:", get_doctors())