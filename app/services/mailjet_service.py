import json
import logging
import urllib.request
import urllib.error
import base64
from app.config import MAILJET_API_KEY, MAILJET_SECRET_KEY, MAILJET_FROM, MAILJET_FROM_NAME

logger = logging.getLogger(__name__)

MAILJET_API_URL = "https://api.mailjet.com/v3.1/send"


async def send_via_mailjet(recipient: str, subject: str, html_body: str) -> tuple[bool, str]:
    """Send email via Mailjet REST API (uses HTTPS port 443, not blocked by firewalls)."""
    if not MAILJET_API_KEY or not MAILJET_SECRET_KEY:
        return False, "MAILJET_API_KEY or MAILJET_SECRET_KEY is not set."

    payload = json.dumps({
        "Messages": [
            {
                "From": {
                    "Email": MAILJET_FROM,
                    "Name": MAILJET_FROM_NAME,
                },
                "To": [
                    {
                        "Email": recipient,
                        "Name": recipient,
                    }
                ],
                "Subject": subject,
                "HTMLPart": html_body,
            }
        ]
    }).encode("utf-8")

    auth = base64.b64encode(f"{MAILJET_API_KEY}:{MAILJET_SECRET_KEY}".encode()).decode()
    req = urllib.request.Request(
        MAILJET_API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode())
            messages = body.get("Messages", [])
            if messages and messages[0].get("Status") == "success":
                logger.info("Email sent to %s via Mailjet", recipient)
                return True, "ok"
            errors = messages[0].get("Errors", [{"ErrorMessage": "unknown"}]) if messages else [{"ErrorMessage": "empty response"}]
            err_msg = "; ".join(e.get("ErrorMessage", str(e)) for e in errors)
            logger.error("Mailjet send error for %s: %s", recipient, err_msg)
            return False, f"Mailjet error: {err_msg}"
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode())
            err_msg = detail.get("ErrorMessage", str(e))
        except Exception:
            err_msg = str(e)
        logger.error("Mailjet HTTP error for %s: %s", recipient, err_msg)
        return False, f"Mailjet HTTP error: {err_msg}"
    except urllib.error.URLError as e:
        logger.error("Mailjet connection error for %s: %s", recipient, e.reason)
        return False, f"Mailjet connection error: {e.reason}"
    except Exception as e:
        logger.error("Mailjet unexpected error for %s: %s", recipient, e, exc_info=True)
        return False, f"Mailjet error: {e}"
