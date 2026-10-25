import os
import smtplib
import ssl
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()

OTP_MINUTES = 10

PURPOSES = {
    "register": {
        "subject": "Your TripGenie verification code",
        "heading": "Verify your email",
        "line": "Use this code to finish creating your TripGenie account.",
    },
    "reset": {
        "subject": "Your TripGenie password reset code",
        "heading": "Reset your password",
        "line": "Use this code to reset your TripGenie password.",
    },
}


def smtp_enabled() -> bool:
    return os.getenv("SMTP_ENABLED", "false").lower() == "true"


def _html(otp: str, heading: str, line: str) -> str:
    return f"""\
<div style="font-family:Arial,Helvetica,sans-serif;background:#f4f6fb;padding:24px">
  <div style="max-width:460px;margin:auto;background:#fff;border-radius:16px;padding:28px;border:1px solid #e6e9f2">
    <div style="font-weight:800;color:#6b5cff;letter-spacing:1px;font-size:13px">TRIPGENIE</div>
    <h2 style="margin:10px 0 6px;color:#171d2f">{heading}</h2>
    <p style="color:#59667b;font-size:14px;line-height:1.5;margin:0 0 18px">{line}</p>
    <div style="font-size:34px;font-weight:800;letter-spacing:8px;text-align:center;background:#f1efff;color:#171d2f;border-radius:12px;padding:16px 0">{otp}</div>
    <p style="color:#738096;font-size:12.5px;margin:18px 0 0;line-height:1.5">
      This code expires in {OTP_MINUTES} minutes. If you did not request it, you can ignore this email —
      nobody can use the code without your password.
    </p>
  </div>
</div>"""


def send_otp_email(to_email: str, otp: str, purpose: str = "register"):
    """Send an OTP. With SMTP_ENABLED=false the OTP is printed in the terminal instead."""
    if not smtp_enabled():
        print(f"DEV OTP ({purpose}) for {to_email}: {otp}")
        return

    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME")
    password = (os.getenv("SMTP_PASSWORD") or "").replace(" ", "")  # Google shows app passwords with spaces
    sender = os.getenv("SMTP_FROM") or username
    if not username or not password or not sender:
        raise ValueError("SMTP_ENABLED=true but SMTP_USERNAME, SMTP_PASSWORD or SMTP_FROM is missing in .env")

    copy = PURPOSES.get(purpose, PURPOSES["register"])
    msg = EmailMessage()
    msg["Subject"] = copy["subject"]
    msg["From"] = f"TripGenie <{sender}>" if "<" not in sender else sender
    msg["To"] = to_email
    msg.set_content(
        f"{copy['heading']}\n\nYour TripGenie code is: {otp}\n"
        f"It expires in {OTP_MINUTES} minutes. If you did not request this, ignore this email."
    )
    msg.add_alternative(_html(otp, copy["heading"], copy["line"]), subtype="html")

    try:
        if port == 465:  # implicit SSL
            with smtplib.SMTP_SSL(host, port, timeout=20, context=ssl.create_default_context()) as server:
                server.login(username, password)
                server.send_message(msg)
        else:  # 587 / STARTTLS
            with smtplib.SMTP(host, port, timeout=20) as server:
                server.starttls(context=ssl.create_default_context())
                server.login(username, password)
                server.send_message(msg)
    except smtplib.SMTPAuthenticationError as error:
        raise RuntimeError(
            "SMTP login rejected. For Gmail use a 16-character App Password "
            "(Google Account > Security > 2-Step Verification > App passwords), not your normal password."
        ) from error
