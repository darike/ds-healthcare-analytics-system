from pymongo import MongoClient
from datetime import datetime

client = MongoClient("mongodb://localhost:27017/")
db = client["HealthcareAnalyticsDB"]

# Collections
medical_records_collection = db["medical_records"]
communications_collection = db["communications"]
doctor_notes_collection = db["doctor_notes"]


# MEDICAL RECORDS MANAGEMENT

def upload_medical_record(
    patient_id,
    document_type,
    file_name,
    file_path,
    uploaded_by
):
    """
    Store lab reports, prescriptions,
    diagnostic reports, etc.
    """

    record = {
        "patient_id": patient_id,
        "document_type": document_type,
        "file_name": file_name,
        "file_path": file_path,
        "uploaded_by": uploaded_by,
        "uploaded_at": datetime.now()
    }

    result = medical_records_collection.insert_one(record)
    return result.inserted_id


def get_patient_records(patient_id):
    """
    Retrieve all records for a patient.
    """

    records = list(
        medical_records_collection.find(
            {"patient_id": patient_id},
            {"_id": 0}
        )
    )

    return records


def delete_medical_record(file_name):
    """
    Delete a specific medical record.
    """

    result = medical_records_collection.delete_one(
        {"file_name": file_name}
    )

    return result.deleted_count


# FEEDBACK & COMMUNICATION MODULE

def raise_patient_query(
    patient_id,
    doctor_id,
    message
):
    """
    Patient sends a query to doctor.
    """

    query = {
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "sender": "Patient",
        "message": message,
        "timestamp": datetime.now()
    }

    result = communications_collection.insert_one(query)
    return result.inserted_id


def doctor_reply(
    patient_id,
    doctor_id,
    message
):
    """
    Doctor replies to patient.
    """

    reply = {
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "sender": "Doctor",
        "message": message,
        "timestamp": datetime.now()
    }

    result = communications_collection.insert_one(reply)
    return result.inserted_id


def get_communication_history(
    patient_id,
    doctor_id
):
    """
    Retrieve complete chat history
    between patient and doctor.
    """

    history = list(
        communications_collection.find(
            {
                "patient_id": patient_id,
                "doctor_id": doctor_id
            },
            {"_id": 0}
        ).sort("timestamp", 1)
    )

    return history


# DOCTOR NOTES SYSTEM

def add_doctor_note(
    patient_id,
    doctor_id,
    note
):
    """
    Doctor adds clinical notes.
    """

    note_data = {
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "note": note,
        "created_at": datetime.now()
    }

    result = doctor_notes_collection.insert_one(note_data)
    return result.inserted_id


def get_doctor_notes(patient_id):
    """
    Retrieve all notes for a patient.
    """

    notes = list(
        doctor_notes_collection.find(
            {"patient_id": patient_id},
            {"_id": 0}
        ).sort("created_at", -1)
    )

    return notes


def delete_doctor_note(note_text):
    """
    Delete a specific doctor note.
    """

    result = doctor_notes_collection.delete_one(
        {"note": note_text}
    )

    return result.deleted_count


# TESTING

if __name__ == "__main__":

    print("MongoDB Connected Successfully!")


