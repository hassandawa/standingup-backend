import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from app.config import CONTACT_EMAIL
from app.database import contact_messages
from app.models.schemas import ContactRequest
from app.services.email_service import send_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/contact", tags=["contact"])


@router.post("")
async def submit_contact_message(payload: ContactRequest):
    doc = {
        "name": payload.name.strip(),
        "email": payload.email.strip().lower(),
        "subject": payload.subject.strip() or "General inquiry",
        "message": payload.message.strip(),
        "created_at": datetime.now(timezone.utc),
    }
    try:
        contact_messages.insert_one(doc)
    except Exception as exc:
        logger.error("Failed to save contact message: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to submit your message. Please try again.")
    html_body = f"""
        <p>New contact form message from startingUP:</p>
        <p><strong>Name:</strong> {doc['name']}<br>
        <strong>Email:</strong> {doc['email']}<br>
        <strong>Subject:</strong> {doc['subject']}</p>
        <p><strong>Message:</strong><br>{doc['message'].replace(chr(10), '<br>')}</p>
    """
    try:
        sent, reason = await send_email(CONTACT_EMAIL, f"[startingUP Contact] {doc['subject']}", html_body)
        if not sent:
            logger.warning("Contact notification email not sent: %s", reason)
    except Exception as exc:
        logger.error("Contact notification email failed: %s", exc, exc_info=True)
        # Message is already saved to the database, so this isn't fatal.
    return {"message": "Thanks for reaching out! We'll get back to you soon."}
