import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import pickle
from auth import get_db_connection


# LOAD TRAINING DATA

df = pd.read_csv('ML_Training_Dataset.csv')
df.columns = df.columns.str.strip()

# ENCODE TRAINING DATA

for col in [
    'Family_History_Diabetes',
    'Family_history_Heart_disease',
    'Previous_heart_condition',
    'Diabetes_diagnosis',
    'Cardiovascular_disease_diagnosis'
]:
    df[col] = df[col].map({'Yes': 1, 'No': 0})

df['Smoking_status'] = df['Smoking_status'].map({'Smoker': 1, 'Non-Smoker': 0})
df['Stress_level']   = df['Stress_level'].map({'Low': 0, 'Medium': 1, 'High': 2})
df['Gender']         = df['Gender'].map({'Male': 1, 'Female': 0})


# HEALTH RISK — SCORE BASED

def risk_level(row):
    score = 0
    
    if row['Diabetes_diagnosis'] == 1:               score += 3
    if row['Cardiovascular_disease_diagnosis'] == 1: score += 3

    if row['Blood_pressure_systolic'] >= 140:        score += 2
    elif row['Blood_pressure_systolic'] >= 130:      score += 1

    if row['Fasting_blood_glucose'] >= 126:          score += 2
    elif row['Fasting_blood_glucose'] >= 100:        score += 1

    if row['Cholesterol_level'] >= 240:              score += 2
    elif row['Cholesterol_level'] >= 200:            score += 1

    if row['Heart_rate'] >= 100:                     score += 1

    if row['Smoking_status'] == 1:                   score += 2
    if row['Stress_level'] == 2:                     score += 1
    if row['Sleep_hours_per_day'] <= 5:              score += 1

    if row['Age'] >= 60:                             score += 2
    elif row['Age'] >= 45:                           score += 1

    if score >= 8:   return 'Critical'
    elif score >= 4: return 'Moderate'
    else:            return 'Stable'


df['Health_Risk'] = df.apply(risk_level, axis=1)

# MODEL 1 : DIABETES PREDICTION

diabetes_features = [
    'Age', 'Fasting_blood_glucose', 'Insulin_level',
    'Family_History_Diabetes', 'Stress_level',
    'Sleep_hours_per_day', 'Body_temperature'
]

X = df[diabetes_features]
y = df['Diabetes_diagnosis']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model_diabetes = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
model_diabetes.fit(X_train, y_train)

print("Diabetes Accuracy:", round(accuracy_score(y_test, model_diabetes.predict(X_test)) * 100, 2), "%")

with open('model_diabetes.pkl', 'wb') as f:
    pickle.dump(model_diabetes, f)

# MODEL 2 : CARDIOVASCULAR DISEASE PREDICTION

cardio_features = [
    'Age', 'Smoking_status', 'Blood_pressure_systolic',
    'Blood_pressure_diastolic', 'Heart_rate', 'Cholesterol_level',
    'Family_history_Heart_disease', 'Previous_heart_condition', 'Stress_level'
]

X = df[cardio_features]
y = df['Cardiovascular_disease_diagnosis']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model_cardio = RandomForestClassifier(n_estimators=100, max_depth=8,random_state=42)
model_cardio.fit(X_train, y_train)

print("Cardiovascular Accuracy:", round(accuracy_score(y_test, model_cardio.predict(X_test)) * 100, 2), "%")

with open('model_cardio.pkl', 'wb') as f:
    pickle.dump(model_cardio, f)

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

print("ML Engine initialized and models trained successfully.")