import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from dotenv import load_dotenv
import core.auth as auth
import core.appointments as appointments
import core.dashboard_data as dashboard_data
import core.mongodb as mongo

from core.mail import send_doctor_credentials

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "academic-fallback-key")

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ── Initialize all tables once on startup ──
try:
    auth.initialize_database()
    appointments.initialize_appointment_table()
    dashboard_data.initialize_patient_table()
except Exception as e:
    print(f"[CRITICAL] Startup failed: {e}")


# ── Notifications ──────────────────────────────────────────────────────────────

@app.context_processor
def inject_notifications():
    role  = session.get('user_role')
    user  = session.get('user_name')
    notes = []
    try:
        if role == 'Patient':
            for a in appointments.get_patient_appointments(user):
                if a[5] == 'Booked':
                    notes.append(f"Appointment with Dr. {a[1]} on {a[2]}")
        elif role == 'Doctor':
            for a in appointments.get_doctor_appointments(user):
                if a[5] == 'Booked':
                    notes.append(f"{a[1]} booked an appointment on {a[2]}")
    except Exception:
        notes = []
    return {'notifications': notes[:5], 'notif_count': len(notes)}


# ── Auth ───────────────────────────────────────────────────────────────────────

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        success, result = auth.verify_user(username, password)
        if success:
            session['user_name'] = username
            session['user_role'] = result
            return redirect(url_for(f'{result.lower()}_dashboard'))
        flash(result, 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ── Admin ──────────────────────────────────────────────────────────────────────

@app.route('/dashboard/admin')
def admin_dashboard():
    if session.get('user_role') != 'Admin':
        return redirect(url_for('login'))
    stats = auth.get_system_statistics()
    return render_template('admin_dashboard.html',
                           user_name=session.get('user_name'),
                           stats=stats,
                           active_page='overview')


from core.mail import send_doctor_credentials

@app.route('/dashboard/admin/users', methods=['GET', 'POST'])
def admin_users():

    if session.get('user_role') != 'Admin':
        return redirect(url_for('login'))

    if request.method == 'POST':

        success, message = auth.create_user_profile(
            request.form.get('new_username'),
            request.form.get('new_password'),
            request.form.get('assigned_role'),
            email=request.form.get('email'),
            speciality=request.form.get('speciality')
        )

        if success:
            send_doctor_credentials(
                request.form.get('email'),
                request.form.get('new_username'),
                request.form.get('new_password')
            )

        flash(message, 'success' if success else 'error')

    return render_template(
        'admin_users.html',
        user_name=session.get('user_name'),
        active_page='users'
    )

@app.route('/dashboard/admin/analytics')
def admin_analytics():
    if session.get('user_role') != 'Admin':
        return redirect(url_for('login'))
    data = dashboard_data.get_analytics_data(doctor_name=None)
    return render_template('analytics.html',
                           user_name=session.get('user_name'),
                           active_page='admin_analytics',
                           role='Admin',
                           **data)


# ── Doctor ─────────────────────────────────────────────────────────────────────

@app.route('/dashboard/doctor')
def doctor_dashboard():
    if session.get('user_role') != 'Doctor':
        return redirect(url_for('login'))
    doctor   = session.get('user_name')
    stats    = dashboard_data.get_overview_stats(doctor_name=doctor)
    patients = dashboard_data.get_patients(100, doctor_name=doctor)
    return render_template('doctor.html',
                           view='dashboard',
                           user_name=doctor,
                           active_page='doctor_overview',
                           stats=stats,
                           patients=patients)


@app.route('/dashboard/doctor/patients', methods=['GET', 'POST'])
def doctor_patients():
    if session.get('user_role') != 'Doctor':
        return redirect(url_for('login'))
    doctor = session.get('user_name')
    if request.method == 'POST':
        success, message = auth.create_user_profile(
            request.form.get('new_username'),
            request.form.get('new_password'),
            'Patient',
            doctor_name=doctor
        )
        flash(message, 'success' if success else 'error')
        return redirect(url_for('doctor_patients'))
    patient_accounts = dashboard_data.get_patient_accounts(doctor_name=doctor)
    stats            = dashboard_data.get_overview_stats(doctor_name=doctor)
    return render_template('doctor.html',
                           view='patients',
                           user_name=doctor,
                           active_page='doctor_patients',
                           stats=stats,
                           patients=patient_accounts)


@app.route('/dashboard/doctor/patient/<username>', methods=['GET', 'POST'])
def doctor_patient_record(username):
    if session.get('user_role') != 'Doctor':
        return redirect(url_for('login'))
    if request.method == 'POST':
        try:
            dashboard_data.save_patient_record(request.form)
            flash(f'Clinical data saved for {username}.', 'success')
            return redirect(url_for('doctor_patients'))
        except Exception as e:
            flash(f'Could not save record: {e}', 'error')
    record = dashboard_data.get_patient_clinical(username)
    return render_template('doctor_patient_form.html',
                           user_name=session.get('user_name'),
                           active_page='doctor_patients',
                           patient_name=username,
                           record=record)


@app.route('/dashboard/doctor/delete-patient', methods=['POST'])
def doctor_delete_patient():
    if session.get('user_role') != 'Doctor':
        return redirect(url_for('login'))
    doctor   = session.get('user_name')
    username = request.form.get('username')
    ok, msg  = dashboard_data.delete_patient(username, doctor_name=doctor)
    flash(msg, 'success' if ok else 'error')
    return redirect(url_for('doctor_patients'))


@app.route('/dashboard/doctor/appointments')
def doctor_appointments():
    if session.get('user_role') != 'Doctor':
        return redirect(url_for('login'))
    my_list = appointments.get_doctor_appointments(session.get('user_name'))
    return render_template('doctor.html',
                           view='appointments',
                           user_name=session.get('user_name'),
                           active_page='doctor_appointments',
                           appointments=my_list)


@app.route('/dashboard/doctor/notes', methods=['GET', 'POST'])
def doctor_notes():
    if session.get('user_role') != 'Doctor':
        return redirect(url_for('login'))
    doctor = session.get('user_name')
    if request.method == 'POST':
        mongo.add_doctor_note(request.form.get('patient'),
                              doctor,
                              request.form.get('note'))
        flash('Note saved.', 'success')
        return redirect(url_for('doctor_notes', patient=request.form.get('patient')))
    selected         = request.values.get('patient')
    notes            = mongo.get_doctor_notes(selected) if selected else []
    patient_accounts = dashboard_data.get_patient_accounts(doctor_name=doctor)
    patients_tuples  = [(p['name'], p['age']) for p in patient_accounts]
    return render_template('doctor.html',
                           view='notes',
                           user_name=doctor,
                           active_page='doctor_notes',
                           notes=notes,
                           selected=selected,
                           patients=patients_tuples)


@app.route('/dashboard/doctor/records', methods=['GET', 'POST'])
def doctor_records():
    if session.get('user_role') != 'Doctor':
        return redirect(url_for('login'))
    doctor = session.get('user_name')
    if request.method == 'POST':
        patient       = request.form.get('patient')
        document_type = request.form.get('document_type')
        file          = request.files.get('document')
        if file and file.filename:
            filename = file.filename
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            mongo.upload_medical_record(patient, document_type, filename,
                                        filename, doctor)
            flash('Medical record uploaded.', 'success')
        else:
            flash('Please choose a file.', 'error')
        return redirect(url_for('doctor_records', patient=patient))
    selected         = request.values.get('patient')
    records          = mongo.get_patient_records(selected) if selected else []
    patient_accounts = dashboard_data.get_patient_accounts(doctor_name=doctor)
    patients_tuples  = [(p['name'], p['age']) for p in patient_accounts]
    return render_template('doctor.html',
                           view='records',
                           user_name=doctor,
                           active_page='doctor_records',
                           records=records,
                           selected=selected,
                           patients=patients_tuples)


@app.route('/dashboard/doctor/messages', methods=['GET', 'POST'])
def doctor_messages():
    if session.get('user_role') != 'Doctor':
        return redirect(url_for('login'))
    doctor = session.get('user_name')
    if request.method == 'POST':
        mongo.doctor_reply(request.form.get('patient'),
                           doctor,
                           request.form.get('message'))
        return redirect(url_for('doctor_messages', patient=request.form.get('patient')))
    selected         = request.values.get('patient')
    chat             = mongo.get_communication_history(selected, doctor) if selected else []
    patient_accounts = dashboard_data.get_patient_accounts(doctor_name=doctor)
    patients_tuples  = [(p['name'], p['age']) for p in patient_accounts]
    return render_template('doctor.html',
                           view='messages',
                           user_name=doctor,
                           active_page='doctor_messages',
                           chat=chat,
                           selected=selected,
                           patients=patients_tuples)


@app.route('/dashboard/doctor/analytics')
def doctor_analytics():
    if session.get('user_role') != 'Doctor':
        return redirect(url_for('login'))
    doctor = session.get('user_name')
    data   = dashboard_data.get_analytics_data(doctor_name=doctor)
    return render_template('analytics.html',
                           user_name=doctor,
                           active_page='doctor_analytics',
                           role='Doctor',
                           **data)


# ── Patient ────────────────────────────────────────────────────────────────────

@app.route('/dashboard/patient')
def patient_dashboard():
    if session.get('user_role') != 'Patient':
        return redirect(url_for('login'))
    my_appointments = appointments.get_patient_appointments(session.get('user_name'))
    record          = dashboard_data.get_patient_record(session.get('user_name'))
    doctors         = appointments.get_doctors()
    return render_template('patient.html',
                           view='dashboard',
                           user_name=session.get('user_name'),
                           active_page='patient_overview',
                           appointments=my_appointments,
                           record=record,
                           doctors=doctors)


@app.route('/dashboard/patient/appointments', methods=['GET', 'POST'])
def patient_appointments():
    if session.get('user_role') != 'Patient':
        return redirect(url_for('login'))
    if request.method == 'POST':
        appointments.book_appointment(
            session.get('user_name'),
            request.form.get('doctor'),
            request.form.get('date'),
            request.form.get('time'),
            request.form.get('reason')
        )
        flash('Appointment booked.', 'success')
        return redirect(url_for('patient_appointments'))
    my_list = appointments.get_patient_appointments(session.get('user_name'))
    doctors = appointments.get_doctors()
    return render_template('patient.html',
                           view='appointments',
                           user_name=session.get('user_name'),
                           active_page='patient_appointments',
                           appointments=my_list,
                           doctors=doctors)


@app.route('/dashboard/patient/appointments/cancel/<int:appt_id>')
def cancel_appointment(appt_id):
    if session.get('user_role') != 'Patient':
        return redirect(url_for('login'))
    appointments.cancel_appointment(appt_id)
    flash('Appointment cancelled.', 'success')
    return redirect(url_for('patient_appointments'))


@app.route('/dashboard/patient/messages', methods=['GET', 'POST'])
def patient_messages():
    if session.get('user_role') != 'Patient':
        return redirect(url_for('login'))
    if request.method == 'POST':
        mongo.raise_patient_query(session.get('user_name'),
                                  request.form.get('doctor'),
                                  request.form.get('message'))
        return redirect(url_for('patient_messages', doctor=request.form.get('doctor')))
    selected = request.values.get('doctor')
    chat     = mongo.get_communication_history(session.get('user_name'), selected) if selected else []
    doctors  = appointments.get_doctors()
    return render_template('patient.html',
                           view='messages',
                           user_name=session.get('user_name'),
                           active_page='patient_messages',
                           doctors=doctors,
                           chat=chat,
                           selected=selected)


@app.route('/dashboard/patient/records')
def patient_records():
    if session.get('user_role') != 'Patient':
        return redirect(url_for('login'))
    records = mongo.get_patient_records(session.get('user_name'))
    return render_template('patient.html',
                           view='records',
                           user_name=session.get('user_name'),
                           active_page='patient_records',
                           records=records)


@app.route('/uploads/<path:filename>')
def download_file(filename):
    if not session.get('user_role'):
        return redirect(url_for('login'))
    return send_from_directory(UPLOAD_FOLDER, filename)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)