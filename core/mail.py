import smtplib
from email.mime.text import MIMEText

def send_doctor_credentials(email, username, password):

    print("=== MAIL FUNCTION STARTED ===")
    print("Recipient:", email)

    sender = "healthcareanalytics12@gmail.com"
    app_password = "nyqk vcvq ahwj ajvm"

    body = f"""
Welcome to Healthcare Analytics System.

Your account has been created successfully.

Username: {username}
Password: {password}
"""

    msg = MIMEText(body)
    msg["Subject"] = "Doctor Account Credentials"
    msg["From"] = sender
    msg["To"] = email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, app_password)
            server.send_message(msg)

        print("Email sent successfully.")

    except Exception as e:
        print("Email sending failed:", e)