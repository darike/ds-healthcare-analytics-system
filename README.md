# Healthcare Analytics System

A Flask-based predictive analytics web platform designed for clinical environments, featuring role-based dashboards for **Admins, Doctors, and Patients**. The system integrates relational data (T-SQL) for records and unstructured data (MongoDB) for clinical notes, with an integrated machine learning engine for health risk forecasting.

## Features
- **Role-Based Access**: Specialized views for Admins, Doctors, and Patients.
- **Predictive Analytics**: Integrated Scikit-learn module for disease risk forecasting (Logistic Regression/Random Forest).
- **Hybrid Storage**: Uses SQL Server for structured patient profiles and MongoDB for unstructured medical notes/sensor data.
- **Data Pipeline**: Automated ingestion and cleaning of clinical datasets.
- **Admin Control**: User role provisioning with automatic database schema bootstrapping.

## Requirements
- Python 3.12+ (recommended).
- SQL Server with ODBC Driver 17+ installed.
- MongoDB instance (for unstructured clinical data).

## Setup
1. Create and activate a Python 3.12 virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1

2. Install dependencies:
   ```powershell
   pip install -r requirements.txt  

## Environment Variables
Use these keys in `.env` (example values shown):

```
FLASK_ENV=development
FLASK_SECRET_KEY=replace-with-a-strong-secret

# SQL Server configuration
SQL_SERVER=localhost\\SQLEXPRESS
SQL_DATABASE=HealthCareAnalyticsDB

# MongoDB configuration (reserved for future use)
MONGO_URI=mongodb://localhost:27017/
MONGO_DATABASE=HealthCareAnalyticsDB
```


Notes:
- The SQL Server connection uses `Trusted_Connection=yes`, so Windows
	authentication is expected. `SQL_USER` and `SQL_PASSWORD` are not used.
- The app creates a `Users` table on startup if it does not exist.

## Running the App
From the project root:

```
python app.py
```

The server runs at `http://localhost:5000`.

## Default Admin Login
On first run, the app seeds a default admin account:
- Username: `admin`
- Password: `admin123`

Change this account after the first login.

## Verify ODBC Driver (Optional)
You can list available ODBC drivers with:

```
python test.py
```

If `ODBC Driver 17 for SQL Server` does not appear, install it and try again.