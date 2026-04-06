import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import requests

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = os.getenv("SMTP_SENDER_EMAIL", "bhargav280421@gmail.com") 
SENDER_PASSWORD = os.getenv("SMTP_APP_PASSWORD", "kxds fpuh kztg vxqp") 

# For Vercel Relay
VERCEL_EMAIL_URL = os.getenv("VERCEL_EMAIL_URL")
VERCEL_SMTP_SECRET = os.getenv("VERCEL_SMTP_SECRET", "super-secret-elitecare-key123")

def send_otp_email(to_email: str, otp: str) -> bool:
    subject = "EliteCare OTP Verification"
    body = f"Your OTP for patient registration is: {otp}\n\nThis OTP is valid for 10 minutes.\n\nDo not share this with anyone."
    
    # If the app is deployed and pointed to Vercel relay
    if VERCEL_EMAIL_URL:
        try:
            headers = {
                "content-type": "application/json"
            }
            data = {
                "to_email": to_email,
                "otp": otp,
                "secret": VERCEL_SMTP_SECRET
            }
            
            response = requests.post(VERCEL_EMAIL_URL, headers=headers, json=data)
            response.raise_for_status() 
            return True
            
        except Exception as e:
            print(f"Failed to send email via Vercel Relay to {to_email}: {e}")
            return False

    # Fallback to local SMTP (for local dev)
    else:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
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
            print(f"Failed to send email via SMTP to {to_email}: {e}")
            return False
