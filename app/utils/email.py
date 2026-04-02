import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = os.getenv("SMTP_SENDER_EMAIL", "bhargav280421@gmail.com") # Using the provided email as default
SENDER_PASSWORD = os.getenv("SMTP_APP_PASSWORD", "kxds fpuh kztg vxqp") # The provided Google App Password

def send_otp_email(to_email: str, otp: str) -> bool:
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email
    msg['Subject'] = "EliteCare OTP Verification"

    body = f"Your OTP for patient registration is: {otp}\n\nThis OTP is valid for 10 minutes.\n\nDo not share this with anyone."
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, to_email, text)
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
        return False
