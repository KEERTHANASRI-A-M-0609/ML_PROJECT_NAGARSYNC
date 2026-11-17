import os
import smtplib
from email.message import EmailMessage


def send_email_notification(to_email: str, subject: str, body: str) -> dict:
    """Send email when SMTP is configured. Returns delivery metadata; never raises."""
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM") or user
    if not host or not sender or not to_email:
        return {"attempted": False, "delivered": False, "reason": "smtp_not_configured"}
    try:
        msg = EmailMessage()
        msg["Subject"] = subject[:200]
        msg["From"] = sender
        msg["To"] = to_email
        msg.set_content(body)
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            smtp.starttls()
            if user and password:
                smtp.login(user, password)
            smtp.send_message(msg)
        return {"attempted": True, "delivered": True}
    except Exception as exc:
        return {"attempted": True, "delivered": False, "reason": str(exc)[:200]}
