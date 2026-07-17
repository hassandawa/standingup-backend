import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "startingup")
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").strip().lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:5173")

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "noreply@startingup.ai")

MAILJET_API_KEY = os.getenv("MAILJET_API_KEY", "")
MAILJET_SECRET_KEY = os.getenv("MAILJET_SECRET_KEY", "")
MAILJET_FROM = os.getenv("MAILJET_FROM", SMTP_FROM)
MAILJET_FROM_NAME = os.getenv("MAILJET_FROM_NAME", "startingUP")

if AI_PROVIDER not in {"gemini", "groq"}:
    raise EnvironmentError("AI_PROVIDER must be either 'gemini' or 'groq'.")

if AI_PROVIDER == "gemini" and not GEMINI_API_KEY:
    raise EnvironmentError("GEMINI_API_KEY is not set. Add it to your .env file.")

if AI_PROVIDER == "groq" and not GROQ_API_KEY:
    raise EnvironmentError("GROQ_API_KEY is not set. Add it to your .env file.")
