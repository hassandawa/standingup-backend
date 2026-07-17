import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, MAILJET_API_KEY
from app.services.mailjet_service import send_via_mailjet

logger = logging.getLogger(__name__)


async def send_email(recipient: str, subject: str, html_body: str) -> tuple[bool, str]:
    """Send an HTML email.

    Tries Mailjet REST API first (HTTPS, port 443 — rarely blocked).
    Falls back to SMTP if Mailjet is not configured or fails.
    Returns (True, "ok") on success or (False, <reason>) on failure.
    """
    if MAILJET_API_KEY:
        ok, msg = await send_via_mailjet(recipient, subject, html_body)
        if ok:
            return True, "ok"
        logger.warning("Mailjet failed, falling back to SMTP: %s", msg)
    else:
        logger.info("Mailjet not configured, trying SMTP.")

    return await _send_via_smtp(recipient, subject, html_body)


async def _send_via_smtp(recipient: str, subject: str, html_body: str) -> tuple[bool, str]:
    """Send an HTML email via SMTP."""
    if not SMTP_HOST:
        msg = "SMTP_HOST is not set. No email provider configured."
        logger.warning("Email not sent: %s", msg)
        return False, msg

    missing = []
    if not SMTP_USER:
        missing.append("SMTP_USER")
    if not SMTP_PASSWORD:
        missing.append("SMTP_PASSWORD")
    if not SMTP_FROM:
        missing.append("SMTP_FROM")
    if missing:
        msg = f"SMTP configuration incomplete: {', '.join(missing)} not set."
        logger.warning("Email not sent: %s", msg)
        return False, msg

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM
        msg["To"] = recipient
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.set_debuglevel(False)
            server.ehlo()
            if not server.has_extn("STARTTLS"):
                logger.warning("SMTP server %s does not advertise STARTTLS", SMTP_HOST)
            else:
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, [recipient], msg.as_string())

        logger.info("Email sent successfully to %s via %s", recipient, SMTP_HOST)
        return True, "ok"

    except smtplib.SMTPAuthenticationError:
        msg = "SMTP authentication failed. Check SMTP_USER and SMTP_PASSWORD."
        logger.error("Email auth failure for %s via %s: %s", recipient, SMTP_HOST, msg)
        return False, msg
    except smtplib.SMTPException as e:
        msg = f"SMTP error: {e}"
        logger.error("Email SMTP error for %s via %s: %s", recipient, SMTP_HOST, e)
        return False, msg
    except TimeoutError:
        msg = f"Connection timed out connecting to SMTP host {SMTP_HOST}:{SMTP_PORT}."
        logger.error("Email timeout for %s: %s", recipient, msg)
        return False, msg
    except Exception as e:
        msg = f"Unexpected email error: {e}"
        logger.error("Email send failed for %s: %s", recipient, e, exc_info=True)
        return False, msg
