import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")
DATABASE_NAME = os.getenv("DATABASE_NAME", "startingup")
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").strip().lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
FLUTTERWAVE_SECRET_KEY = os.getenv("FLUTTERWAVE_SECRET_KEY", "")
FLUTTERWAVE_WEBHOOK_HASH = os.getenv("FLUTTERWAVE_WEBHOOK_HASH", "")
FLUTTERWAVE_PLAN_ID_PRO = os.getenv("FLUTTERWAVE_PLAN_ID_PRO", "")
FLUTTERWAVE_PLAN_ID_TEAM = os.getenv("FLUTTERWAVE_PLAN_ID_TEAM", "")
FLUTTERWAVE_CURRENCY = os.getenv("FLUTTERWAVE_CURRENCY", "USD")
PLAN_AMOUNTS = {"pro": 50, "team": 100}

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_ID_PRO = os.getenv("STRIPE_PRICE_ID_PRO", "")
STRIPE_PRICE_ID_TEAM = os.getenv("STRIPE_PRICE_ID_TEAM", "")

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "noreply@startingup.ai")

MAILJET_API_KEY = os.getenv("MAILJET_API_KEY", "")
MAILJET_SECRET_KEY = os.getenv("MAILJET_SECRET_KEY", "")
MAILJET_FROM = os.getenv("MAILJET_FROM", SMTP_FROM)
MAILJET_FROM_NAME = os.getenv("MAILJET_FROM_NAME", "startingUP")

CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", SMTP_FROM)

ADMIN_EMAILS = {
    email.strip().lower()
    for email in os.getenv("ADMIN_EMAILS", "").split(",")
    if email.strip()
}

if not DATABASE_URL:
    raise EnvironmentError("DATABASE_URL is not set. Add your Neon/Postgres connection string.")

if AI_PROVIDER not in {"gemini", "groq"}:
    raise EnvironmentError("AI_PROVIDER must be either 'gemini' or 'groq'.")

if AI_PROVIDER == "gemini" and not GEMINI_API_KEY:
    raise EnvironmentError("GEMINI_API_KEY is not set. Add it to your .env file.")

if AI_PROVIDER == "groq" and not GROQ_API_KEY:
    raise EnvironmentError("GROQ_API_KEY is not set. Add it to your .env file.")
