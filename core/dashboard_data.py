from unittest import result

import pandas as pd
import pickle

try:
    from core.auth import get_db_connection
except ImportError:
    from auth import get_db_connection


# ── Table Initialization ──────────────────────────────────────────────────────

def initialize_patient_table():
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Patients' AND xtype='U')
        CREATE TABLE Patients (
            Id                               INT IDENTITY PRIMARY KEY,
            Patient_name                     VARCHAR(255),
            Age                              INT,
            Gender                           VARCHAR(20),
            Smoking_status                   VARCHAR(20),
            Sleep_hours_per_day              INT,
            Blood_pressure_systolic          INT,
            Blood_pressure_diastolic         INT,
            Heart_rate                       INT,
            Body_temperature                 FLOAT,
            Fasting_blood_glucose            INT,
            Cholesterol_level                INT,
            Insulin_level                    FLOAT,
            Family_History_Diabetes          VARCHAR(10),
            Family_history_Heart_disease     VARCHAR(10),
            Previous_heart_condition         VARCHAR(10),
            Stress_level                     VARCHAR(20),
            Diabetes_diagnosis               VARCHAR(10),
            Cardiovascular_disease_diagnosis VARCHAR(10),
            Health_Risk                      VARCHAR(20)
        )
    """)
    conn.commit()
    conn.close()


# ── Helpers ───────────────────────────────────────────────────────────────────

def num(value, cast, default=0):
    try:
        return cast(value)
    except (TypeError, ValueError):
        return default

def pick(value, allowed, default):
    value = (value or '').strip()
    return value if value in allowed else default


# ── Overview Stats (scoped to a doctor's own patients) ────────────────────────

def get_overview_stats(doctor_name=None):
    conn   = get_db_connection()
    cursor = conn.cursor()

    if doctor_name:
        scope     = "JOIN Users u ON u.Username = p.Patient_name WHERE u.Doctor_name = ?"
        scope_and = "JOIN Users u ON u.Username = p.Patient_name WHERE u.Doctor_name = ? AND"
        arg = (doctor_name,)
    else:
        scope     = "WHERE 1=1"
        scope_and = "WHERE"
        arg       = ()

    cursor.execute(f"SELECT COUNT(*) FROM Patients p {scope}", arg)
    total = cursor.fetchone()[0]

    cursor.execute(f"SELECT COUNT(*) FROM Patients p {scope_and} p.Diabetes_diagnosis = 'Yes'", arg)
    diabetic = cursor.fetchone()[0]

    cursor.execute(f"SELECT COUNT(*) FROM Patients p {scope_and} p.Cardiovascular_disease_diagnosis = 'Yes'", arg)
    cvd = cursor.fetchone()[0]

    risk = {'Critical': 0, 'Moderate': 0, 'Stable': 0}
    cursor.execute(f"SELECT p.Health_Risk, COUNT(*) FROM Patients p {scope} GROUP BY p.Health_Risk", arg)
    for row in cursor.fetchall():
        if row[0] in risk:
            risk[row[0]] = row[1]

    conn.close()
    return {
        'total':    total,
        'diabetic': diabetic,
        'cvd':      cvd,
        'critical': risk['Critical'],
        'moderate': risk['Moderate'],
        'stable':   risk['Stable'],
    }


# ── Patient List (scoped to a doctor's own patients) ─────────────────────────

def get_patients(limit=8, doctor_name=None):
    conn   = get_db_connection()
    cursor = conn.cursor()

    if doctor_name:
        cursor.execute("""
            SELECT TOP (?) p.Patient_name, p.Age, p.Gender, p.Blood_pressure_systolic,
                   p.Fasting_blood_glucose, p.Diabetes_diagnosis,
                   p.Cardiovascular_disease_diagnosis, p.Health_Risk
            FROM Patients p
            JOIN Users u ON u.Username = p.Patient_name
            WHERE u.Doctor_name = ?
            ORDER BY CASE p.Health_Risk
                        WHEN 'Critical' THEN 1
                        WHEN 'Moderate' THEN 2
                        ELSE 3
                     END
        """, (limit, doctor_name))
    else:
        cursor.execute("""
            SELECT TOP (?) Patient_name, Age, Gender, Blood_pressure_systolic,
                   Fasting_blood_glucose, Diabetes_diagnosis,
                   Cardiovascular_disease_diagnosis, Health_Risk
            FROM Patients
            ORDER BY CASE Health_Risk
                        WHEN 'Critical' THEN 1
                        WHEN 'Moderate' THEN 2
                        ELSE 3
                     END
        """, (limit,))

    rows = cursor.fetchall()
    conn.close()
    return rows


# ── Single Patient Record ─────────────────────────────────────────────────────

def get_patient_record(name=None):
    conn   = get_db_connection()
    cursor = conn.cursor()

    row = None
    if name:
        cursor.execute("""
            SELECT TOP 1 Patient_name, Age, Blood_pressure_systolic, Blood_pressure_diastolic,
                   Heart_rate, Fasting_blood_glucose, Cholesterol_level,
                   Diabetes_diagnosis, Cardiovascular_disease_diagnosis, Health_Risk
            FROM Patients WHERE Patient_name = ?
        """, (name,))
        row = cursor.fetchone()

    if not row:
        cursor.execute("""
            SELECT TOP 1 Patient_name, Age, Blood_pressure_systolic, Blood_pressure_diastolic,
                   Heart_rate, Fasting_blood_glucose, Cholesterol_level,
                   Diabetes_diagnosis, Cardiovascular_disease_diagnosis, Health_Risk
            FROM Patients
        """)
        row = cursor.fetchone()

    conn.close()
    if not row:
        return None

    return {
        'name': row[0], 'age': row[1],
        'bp_sys': row[2], 'bp_dia': row[3],
        'heart_rate': row[4], 'glucose': row[5], 'cholesterol': row[6],
        'diabetes': row[7], 'cvd': row[8], 'risk': row[9],
    }


# ── Patient Accounts (scoped to a doctor's own patients) ─────────────────────

def get_patient_accounts(doctor_name=None):
    conn   = get_db_connection()
    cursor = conn.cursor()

    if doctor_name:
        cursor.execute("""
            SELECT u.Username, p.Id, p.Age, p.Health_Risk
            FROM Users u
            LEFT JOIN Patients p ON p.Patient_name = u.Username
            WHERE u.Role = 'Patient'
              AND u.Doctor_name = ?
            ORDER BY u.Username
        """, (doctor_name,))
    else:
        cursor.execute("""
            SELECT u.Username, p.Id, p.Age, p.Health_Risk
            FROM Users u
            LEFT JOIN Patients p ON p.Patient_name = u.Username
            WHERE u.Role = 'Patient'
            ORDER BY u.Username
        """)

    rows = cursor.fetchall()
    conn.close()
    return [
        {
            'name':       r[0],
            'has_record': r[1] is not None,
            'age':        r[2],
            'risk':       r[3],
        }
        for r in rows
    ]


# ── Single Patient Clinical Record ───────────────────────────────────────────

def get_patient_clinical(name):
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT TOP 1 Patient_name, Age, Gender, Smoking_status, Sleep_hours_per_day,
               Blood_pressure_systolic, Blood_pressure_diastolic, Heart_rate, Body_temperature,
               Fasting_blood_glucose, Cholesterol_level, Insulin_level,
               Family_History_Diabetes, Family_history_Heart_disease, Previous_heart_condition,
               Stress_level, Diabetes_diagnosis, Cardiovascular_disease_diagnosis, Health_Risk
        FROM Patients WHERE Patient_name = ?
    """, (name,))
    row  = cursor.fetchone()
    conn.close()
    if not row:
        return None

    result = dict(zip([
        'Patient_name', 'Age', 'Gender', 'Smoking_status', 'Sleep_hours_per_day',
        'Blood_pressure_systolic', 'Blood_pressure_diastolic', 'Heart_rate', 'Body_temperature',
        'Fasting_blood_glucose', 'Cholesterol_level', 'Insulin_level',
        'Family_History_Diabetes', 'Family_history_Heart_disease', 'Previous_heart_condition',
        'Stress_level', 'Diabetes_diagnosis', 'Cardiovascular_disease_diagnosis', 'Health_Risk'
    ], row))

    result['diabetes_diagnosis'] = 1 if result['Diabetes_diagnosis'] == 'Yes' else 0 if result['Diabetes_diagnosis'] == 'No' else None
    result['cvd_diagnosis'] = 1 if result['Cardiovascular_disease_diagnosis'] == 'Yes' else 0 if result['Cardiovascular_disease_diagnosis'] == 'No' else None
    result['health_risk'] = result['Health_Risk']
    result['risk'] = result['Health_Risk']

    for k in ['Family_History_Diabetes', 'Family_history_Heart_disease', 'Previous_heart_condition']:
        result[k] = 1 if result[k] == 'Yes' else 0 if result[k] == 'No' else None

    return result


# ── Delete Patient (record + user account) ───────────────────────────────────

def delete_patient(username, doctor_name=None):
    conn   = get_db_connection()
    cursor = conn.cursor()

    if doctor_name:
        cursor.execute(
            "SELECT Id FROM Users WHERE Username = ? AND Role = 'Patient' AND Doctor_name = ?",
            (username, doctor_name)
        )
        if not cursor.fetchone():
            conn.close()
            return False, "Patient not found or you do not have permission to delete this patient."

    cursor.execute("DELETE FROM Patients WHERE Patient_name = ?", (username,))
    cursor.execute("DELETE FROM Users WHERE Username = ? AND Role = 'Patient'", (username,))

    conn.commit()
    conn.close()
    return True, f"Patient '{username}' has been deleted."


# ── Save Patient Record + Run ML Prediction ───────────────────────────────────

def save_patient_record(form):
    name = (form.get('username') or '').strip()
    if not name:
        raise ValueError('Patient name is required.')

    data = {
        'Patient_name':                  name,
        'Age':                           num(form.get('Age'), int),
        'Gender':                        pick(form.get('Gender'), ['Male', 'Female'], 'Unknown'),
        'Smoking_status':                pick(form.get('Smoking_status'), ['Smoker', 'Non-Smoker'], 'Non-Smoker'),
        'Sleep_hours_per_day':           num(form.get('Sleep_hours_per_day'), int),
        'Blood_pressure_systolic':       num(form.get('Blood_pressure_systolic'), int),
        'Blood_pressure_diastolic':      num(form.get('Blood_pressure_diastolic'), int),
        'Heart_rate':                    num(form.get('Heart_rate'), int),
        'Body_temperature':              num(form.get('Body_temperature'), float),
        'Fasting_blood_glucose':         num(form.get('Fasting_blood_glucose'), int),
        'Cholesterol_level':             num(form.get('Cholesterol_level'), int),
        'Insulin_level':                 num(form.get('Insulin_level'), float),
        'Family_History_Diabetes':       pick(form.get('Family_History_Diabetes'), ['Yes', 'No'], 'No'),
        'Family_history_Heart_disease':  pick(form.get('Family_history_Heart_disease'), ['Yes', 'No'], 'No'),
        'Previous_heart_condition':      pick(form.get('Previous_heart_condition'), ['Yes', 'No'], 'No'),
        'Stress_level':                  pick(form.get('Stress_level'), ['Low', 'Medium', 'High'], 'Low'),
    }

    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Id FROM Patients WHERE Patient_name = ?", (name,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("""
            UPDATE Patients SET
                Age = ?, Gender = ?, Smoking_status = ?, Sleep_hours_per_day = ?,
                Blood_pressure_systolic = ?, Blood_pressure_diastolic = ?, Heart_rate = ?,
                Body_temperature = ?, Fasting_blood_glucose = ?, Cholesterol_level = ?,
                Insulin_level = ?, Family_History_Diabetes = ?, Family_history_Heart_disease = ?,
                Previous_heart_condition = ?, Stress_level = ?,
                Diabetes_diagnosis = NULL, Cardiovascular_disease_diagnosis = NULL, Health_Risk = NULL
            WHERE Id = ?
        """, (
            data['Age'], data['Gender'], data['Smoking_status'], data['Sleep_hours_per_day'],
            data['Blood_pressure_systolic'], data['Blood_pressure_diastolic'], data['Heart_rate'],
            data['Body_temperature'], data['Fasting_blood_glucose'], data['Cholesterol_level'],
            data['Insulin_level'], data['Family_History_Diabetes'], data['Family_history_Heart_disease'],
            data['Previous_heart_condition'], data['Stress_level'], existing[0]
        ))
        patient_id = existing[0]
    else:
        cursor.execute("""
            INSERT INTO Patients
            (Patient_name, Age, Gender, Smoking_status, Sleep_hours_per_day,
             Blood_pressure_systolic, Blood_pressure_diastolic, Heart_rate, Body_temperature,
             Fasting_blood_glucose, Cholesterol_level, Insulin_level,
             Family_History_Diabetes, Family_history_Heart_disease, Previous_heart_condition, Stress_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['Patient_name'], data['Age'], data['Gender'], data['Smoking_status'],
            data['Sleep_hours_per_day'], data['Blood_pressure_systolic'], data['Blood_pressure_diastolic'],
            data['Heart_rate'], data['Body_temperature'], data['Fasting_blood_glucose'],
            data['Cholesterol_level'], data['Insulin_level'], data['Family_History_Diabetes'],
            data['Family_history_Heart_disease'], data['Previous_heart_condition'], data['Stress_level']
        ))
        cursor.execute("SELECT @@IDENTITY")
        patient_id = int(cursor.fetchone()[0])

    conn.commit()
    conn.close()

    _predict_single_patient(patient_id, data)


# ── ML Prediction (single patient) ───────────────────────────────────────────

def _predict_single_patient(patient_id, data):
    try:
        with open('core/model_diabetes.pkl', 'rb') as f:
            model_diabetes = pickle.load(f)
        with open('core/model_cardio.pkl', 'rb') as f:
            model_cardio = pickle.load(f)
    except FileNotFoundError:
        with open('model_diabetes.pkl', 'rb') as f:
            model_diabetes = pickle.load(f)
        with open('model_cardio.pkl', 'rb') as f:
            model_cardio = pickle.load(f)

    smoking  = 1 if data['Smoking_status'] == 'Smoker' else 0
    stress   = {'Low': 0, 'Medium': 1, 'High': 2}.get(data['Stress_level'], 0)
    fam_diab = 1 if data['Family_History_Diabetes'] == 'Yes' else 0
    fam_heart= 1 if data['Family_history_Heart_disease'] == 'Yes' else 0
    prev_h   = 1 if data['Previous_heart_condition'] == 'Yes' else 0

    diabetes_input = [[
        data['Age'], data['Fasting_blood_glucose'], data['Insulin_level'],
        fam_diab, stress, data['Sleep_hours_per_day'], data['Body_temperature']
    ]]
    cardio_input = [[
        data['Age'], smoking, data['Blood_pressure_systolic'],
        data['Blood_pressure_diastolic'], data['Heart_rate'], data['Cholesterol_level'],
        fam_heart, prev_h, stress
    ]]

    diabetes_pred = model_diabetes.predict(diabetes_input)[0]
    cardio_pred   = model_cardio.predict(cardio_input)[0]

    score = 0
    if diabetes_pred == 1:                               score += 3
    if cardio_pred == 1:                                 score += 3
    if data['Blood_pressure_systolic'] >= 140:           score += 2
    elif data['Blood_pressure_systolic'] >= 130:         score += 1
    if data['Fasting_blood_glucose'] >= 126:             score += 2
    elif data['Fasting_blood_glucose'] >= 100:           score += 1
    if data['Cholesterol_level'] >= 240:                 score += 2
    elif data['Cholesterol_level'] >= 200:               score += 1
    if data['Heart_rate'] >= 100:                        score += 1
    if smoking == 1:                                     score += 2
    if stress == 2:                                      score += 1
    if data['Sleep_hours_per_day'] <= 5:                 score += 1
    if data['Age'] >= 60:                                score += 2
    elif data['Age'] >= 45:                              score += 1

    if score >= 8:   health_risk = 'Critical'
    elif score >= 4: health_risk = 'Moderate'
    else:            health_risk = 'Stable'

    diabetes_str = 'Yes' if diabetes_pred == 1 else 'No'
    cardio_str   = 'Yes' if cardio_pred   == 1 else 'No'

    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE Patients
        SET Diabetes_diagnosis = ?,
            Cardiovascular_disease_diagnosis = ?,
            Health_Risk = ?
        WHERE Id = ?
    """, (diabetes_str, cardio_str, health_risk, patient_id))
    conn.commit()
    conn.close()


# ── Analytics Data (for charts page) ─────────────────────────────────────────

def get_analytics_data(doctor_name=None):
    """
    Returns all chart data as plain dicts ready to pass to the template.
    doctor_name=None  -> Admin (all patients)
    doctor_name=str   -> Doctor (own patients only)
    """
    conn   = get_db_connection()
    cursor = conn.cursor()

    if doctor_name:
        scope     = "JOIN Users u ON u.Username = p.Patient_name WHERE u.Doctor_name = ?"
        scope_and = "JOIN Users u ON u.Username = p.Patient_name WHERE u.Doctor_name = ? AND"
        arg       = (doctor_name,)
    else:
        scope     = "WHERE 1=1"
        scope_and = "WHERE"
        arg       = ()

    # ── Totals ──
    cursor.execute(f"SELECT COUNT(*) FROM Patients p {scope}", arg)
    total = cursor.fetchone()[0]

    cursor.execute(f"SELECT COUNT(*) FROM Patients p {scope_and} p.Diabetes_diagnosis = 'Yes'", arg)
    diabetic = cursor.fetchone()[0]

    cursor.execute(f"SELECT COUNT(*) FROM Patients p {scope_and} p.Cardiovascular_disease_diagnosis = 'Yes'", arg)
    cvd = cursor.fetchone()[0]

    # ── Risk counts ──
    risk = {'Critical': 0, 'Moderate': 0, 'Stable': 0}
    cursor.execute(f"SELECT p.Health_Risk, COUNT(*) FROM Patients p {scope} GROUP BY p.Health_Risk", arg)
    for row in cursor.fetchall():
        if row[0] in risk:
            risk[row[0]] = row[1]

    # ── Disease breakdown ──
    cursor.execute(
        f"SELECT p.Diabetes_diagnosis, p.Cardiovascular_disease_diagnosis FROM Patients p {scope}", arg
    )
    d_only = cvd_only = both = healthy = 0
    for r in cursor.fetchall():
        d = r[0] == 'Yes'
        c = r[1] == 'Yes'
        if d and c:   both     += 1
        elif d:       d_only   += 1
        elif c:       cvd_only += 1
        else:         healthy  += 1

    # ── Age by risk ──
    age_bins   = ['20-30', '30-40', '40-50', '50-60', '60-70', '70-80']
    age_ranges = [(20,30), (30,40), (40,50), (50,60), (60,70), (70,80)]
    age_risk   = {b: {'Stable': 0, 'Moderate': 0, 'Critical': 0} for b in age_bins}
    cursor.execute(f"SELECT p.Age, p.Health_Risk FROM Patients p {scope}", arg)
    for age, hrisk in cursor.fetchall():
        if age and hrisk:
            for label, (lo, hi) in zip(age_bins, age_ranges):
                if lo <= age < hi:
                    if hrisk in age_risk[label]:
                        age_risk[label][hrisk] += 1
                    break

    # ── Smoking vs CVD ──
    smoking_labels = ['Non-Smoker', 'Smoker']
    sm_yes = [0, 0]
    sm_no  = [0, 0]
    cursor.execute(
        f"SELECT p.Smoking_status, p.Cardiovascular_disease_diagnosis FROM Patients p {scope}", arg
    )
    for sm, cv in cursor.fetchall():
        idx = 1 if sm == 'Smoker' else 0
        if cv == 'Yes': sm_yes[idx] += 1
        else:           sm_no[idx]  += 1

    # ── Stress distribution (Admin only, but computed always) ──
    stress = {'Low': 0, 'Medium': 0, 'High': 0}
    cursor.execute(
        f"SELECT p.Stress_level, COUNT(*) FROM Patients p {scope} GROUP BY p.Stress_level", arg
    )
    for row in cursor.fetchall():
        if row[0] in stress:
            stress[row[0]] = row[1]

    # ── Family history impact (Admin only, but computed always) ──
    fam_diab_got = fam_diab_safe = fam_cvd_got = fam_cvd_safe = 0
    cursor.execute(
        f"SELECT p.Family_History_Diabetes, p.Diabetes_diagnosis FROM Patients p {scope}", arg
    )
    for fh, diag in cursor.fetchall():
        if fh == 'Yes':
            if diag == 'Yes': fam_diab_got  += 1
            else:             fam_diab_safe += 1

    cursor.execute(
        f"SELECT p.Family_history_Heart_disease, p.Cardiovascular_disease_diagnosis FROM Patients p {scope}", arg
    )
    for fh, diag in cursor.fetchall():
        if fh == 'Yes':
            if diag == 'Yes': fam_cvd_got  += 1
            else:             fam_cvd_safe += 1

    conn.close()

    return {
        'total':    total,
        'diabetic': diabetic,
        'cvd':      cvd,
        'critical': risk['Critical'],
        'moderate': risk['Moderate'],
        'stable':   risk['Stable'],
        'risk_data': risk,
        'disease_data': {
            'diabetes_only': d_only,
            'cvd_only':      cvd_only,
            'both':          both,
            'healthy':       healthy,
        },
        'age_risk_data': {
            'labels':   age_bins,
            'stable':   [age_risk[b]['Stable']   for b in age_bins],
            'moderate': [age_risk[b]['Moderate'] for b in age_bins],
            'critical': [age_risk[b]['Critical'] for b in age_bins],
        },
        'smoking_data': {
            'labels':  smoking_labels,
            'cvd_yes': sm_yes,
            'cvd_no':  sm_no,
        },
        'stress_data': stress,
        'family_data': {
            'diab_got':  fam_diab_got,
            'diab_safe': fam_diab_safe,
            'cvd_got':   fam_cvd_got,
            'cvd_safe':  fam_cvd_safe,
        },
    }