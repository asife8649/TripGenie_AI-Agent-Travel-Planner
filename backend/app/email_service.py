import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

def send_otp_email(to_email: str, otp: str):
    enabled = os.getenv("SMTP_ENABLED", "false").lower() == "true"
    if not enabled:
        print(f"DEV OTP for {to_email}: {otp}")
        return

    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM") or username
    if not username or not password or not sender:
        raise ValueError("SMTP_ENABLED=true but SMTP_USERNAME, SMTP_PASSWORD, or SMTP_FROM is missing")

    msg = EmailMessage()
    msg["Subject"] = "TripGenie Email Verification OTP"
    msg["From"] = sender
    msg["To"] = to_email
    msg.set_content(
        f"Your TripGenie verification OTP is {otp}. "
        "It expires in 10 minutes."
    )

    with smtplib.SMTP(os.getenv("SMTP_HOST", "smtp.gmail.com"), int(os.getenv("SMTP_PORT", "587"))) as server:
        server.starttls()
        server.login(username, password)
        server.send_message(msg)
