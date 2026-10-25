"""Check your SMTP settings without running the whole app.

    cd backend
    python test_email.py you@example.com
"""
import sys

from app.email_service import send_otp_email, smtp_enabled

if len(sys.argv) < 2:
    sys.exit("Usage: python test_email.py recipient@example.com")

print("SMTP_ENABLED =", smtp_enabled())
try:
    send_otp_email(sys.argv[1], "123456", "register")
    print("OK - check the inbox (and spam folder)." if smtp_enabled() else "SMTP is disabled: OTP printed above only.")
except Exception as error:
    print("FAILED:", error)
    sys.exit(1)
