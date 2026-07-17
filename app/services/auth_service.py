import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.database import users, password_resets

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
HASH_ITERATIONS = 210_000
RESET_TOKEN_EXPIRY_MINUTES = 15


class AuthError(Exception):
    """Expected authentication failure."""


class DuplicateUserError(AuthError):
    """Raised when an email is already registered."""


def _normalize_email(email: str) -> str:
    clean = email.strip().lower()
    if not EMAIL_RE.match(clean):
        raise AuthError("Enter a valid email address.")
    return clean


def _hash_password(password: str, salt_hex: str | None = None) -> tuple[str, str]:
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        HASH_ITERATIONS,
    )
    return salt.hex(), digest.hex()


def _public_user(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "name": doc["name"],
        "email": doc["email"],
        "created_at": doc["created_at"],
    }


def _new_token() -> str:
    return secrets.token_urlsafe(32)


def create_user(name: str, email: str, password: str) -> dict:
    clean_name = name.strip()
    if not clean_name:
        raise AuthError("Name is required.")
    clean_email = _normalize_email(email)
    salt, password_hash = _hash_password(password)
    now = datetime.now(timezone.utc)
    token = _new_token()
    doc = {
        "name": clean_name,
        "email": clean_email,
        "password_salt": salt,
        "password_hash": password_hash,
        "tokens": [token],
        "created_at": now,
        "updated_at": now,
    }
    try:
        result = users.insert_one(doc)
    except DuplicateKeyError as exc:
        raise DuplicateUserError("An account with this email already exists.") from exc
    doc["_id"] = result.inserted_id
    return {"token": token, "user": _public_user(doc)}


def authenticate_user(email: str, password: str) -> dict:
    clean_email = _normalize_email(email)
    user = users.find_one({"email": clean_email})
    if not user:
        raise AuthError("Invalid email or password.")
    _, candidate_hash = _hash_password(password, user["password_salt"])
    if not hmac.compare_digest(candidate_hash, user["password_hash"]):
        raise AuthError("Invalid email or password.")
    token = _new_token()
    users.update_one(
        {"_id": user["_id"]},
        {"$push": {"tokens": token}, "$set": {"updated_at": datetime.now(timezone.utc)}},
    )
    return {"token": token, "user": _public_user(user)}


def request_password_reset(email: str) -> str:
    clean_email = _normalize_email(email)
    user = users.find_one({"email": clean_email})
    if not user:
        return ""
    password_resets.delete_many({"email": clean_email})
    token = secrets.token_urlsafe(48)
    password_resets.insert_one({
        "token": token,
        "email": clean_email,
        "user_id": user["_id"],
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES),
    })
    return token


def verify_reset_token(token: str) -> dict:
    if not token:
        raise AuthError("Reset token is required.")
    doc = password_resets.find_one({"token": token})
    if not doc:
        raise AuthError("Invalid or expired reset token.")
    if doc["expires_at"] < datetime.now(timezone.utc):
        password_resets.delete_one({"_id": doc["_id"]})
        raise AuthError("Reset token has expired. Please request a new one.")
    return {"email": doc["email"], "token": token}


def reset_password(token: str, new_password: str) -> bool:
    if not token:
        raise AuthError("Reset token is required.")
    if len(new_password) < 8:
        raise AuthError("Password must be at least 8 characters.")
    doc = password_resets.find_one({"token": token})
    if not doc:
        raise AuthError("Invalid or expired reset token.")
    if doc["expires_at"] < datetime.now(timezone.utc):
        password_resets.delete_one({"_id": doc["_id"]})
        raise AuthError("Reset token has expired. Please request a new one.")
    salt, password_hash = _hash_password(new_password)
    users.update_one(
        {"_id": doc["user_id"]},
        {"$set": {
            "password_salt": salt,
            "password_hash": password_hash,
            "updated_at": datetime.now(timezone.utc),
        }},
    )
    password_resets.delete_one({"_id": doc["_id"]})
    return True


def get_user_by_token(token: str) -> dict | None:
    if not token:
        return None
    user = users.find_one({"tokens": token})
    return _public_user(user) if user else None


def get_user_by_id(user_id: str) -> dict | None:
    if not user_id:
        return None
    try:
        user = users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        return None
    return _public_user(user) if user else None


def logout_user(token: str) -> bool:
    if not token:
        return False
    result = users.update_one(
        {"tokens": token},
        {"$pull": {"tokens": token}, "$set": {"updated_at": datetime.now(timezone.utc)}},
    )
    return result.modified_count > 0
