import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import resend

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = os.getenv("SMTP_SENDER_EMAIL", "bhargav280421@gmail.com") 
SENDER_PASSWORD = os.getenv("SMTP_APP_PASSWORD", "kxds fpuh kztg vxqp") 
RESEND_API_KEY = os.getenv("RESEND_API_KEY")

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

def send_otp_email(to_email: str, otp: str) -> bool:
    subject = "EliteCare OTP Verification"
    body = f"Your OTP for patient registration is: {otp}\n\nThis OTP is valid for 10 minutes.\n\nDo not share this with anyone."
    
    # If a Resend API key exists, use Resend (for production/deploy)
    if RESEND_API_KEY:
        try:
            params = {
                "from": "EliteCare <onboarding@resend.dev>",
                "to": [to_email],
                "subject": subject,
                "html": f"<p>Your OTP for patient registration is: <strong>{otp}</strong></p><p>This OTP is valid for 10 minutes.</p><p>Do not share this with anyone.</p>",
            }
            resend.Emails.send(params)
            return True
        except Exception as e:
            print(f"Failed to send email via Resend to {to_email}: {e}")
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
