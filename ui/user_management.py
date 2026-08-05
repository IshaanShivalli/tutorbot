<<<<<<< HEAD
import hashlib
import json 
import random
import smtplib
import ssl
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path 
from typing import Any

from config import EMAIL_FROM, SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_USE_TLS

USER_DATA_FILE = Path(__file__).resolve().parent / "user_data.json"
DEFAULT_ADMIN_PASSWORD = "admin"
CODE_TTL_MINUTES = 15


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _verify_password(password: str, password_hash: str) -> bool:
    return _hash_password(password) == password_hash


def _default_user(username: str, role: str = "student", email: str = "", password_hash: str | None = None) -> dict[str, Any]:
    return {
    "username": username,
    "role": role,
    "email": email,
    "password_hash": password_hash,
    "created_at": datetime.utcnow().isoformat() + "Z",
    "last_active": None,
    "verified": False,
    }


def _load_raw() -> dict[str, Any]:
    if not USER_DATA_FILE.exists():
        return {}
    try:
        with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_raw(data: dict[str, Any]) -> None:
    try:
        with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass


def _ensure_structure(data: dict[str, Any]) -> dict[str, Any]:
    if "users" not in data or not isinstance(data["users"], dict):
        data["users"] = {}
    if "current_user" not in data or not isinstance(data["current_user"], str):
        data["current_user"] = "guest"
    if "pending_verifications" not in data or not isinstance(data["pending_verifications"], dict):
        data["pending_verifications"] = {}
    return data


def _ensure_default_users(data: dict[str, Any]) -> dict[str, Any]:
    data = _ensure_structure(data)
    users = data["users"]
    if "guest" not in users:
        users["guest"] = _default_user("guest", role="guest", email="guest@tutorbot.com")
    if "admin" not in users:
        users["admin"] = _default_user(
        "admin",
        role="admin",
        email="admin@tutorbot.com",
        password_hash=_hash_password(DEFAULT_ADMIN_PASSWORD),
        )
    return data


def _load_data() -> dict[str, Any]:
    raw = _load_raw()
    raw = _ensure_structure(raw)
    raw = _ensure_default_users(raw)
    return raw


def _generate_code() -> str:
    return f"{random.randint(100000, 999999)}"


def _send_email(to_email: str, subject: str, body: str) -> None:
    if not SMTP_SERVER or not SMTP_USER or not SMTP_PASSWORD:
        return
    message = EmailMessage()
    message["From"] = EMAIL_FROM
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)
    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
        if SMTP_USE_TLS:
            server.starttls(context=context)
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(message)


def _save_data(data: dict[str, Any]) -> None:
    _save_raw(data)


def get_current_user() -> dict[str, Any]:
    data = _load_data()
    username = data.get("current_user", "guest")
    user = data["users"].get(username)
    if not user:
        user = _default_user(username)
        data["users"][username] = user
        _save_data(data)
    return user


def set_current_user(username: str) -> dict[str, Any]:
    username = username.strip().lower()
    if not username:
        raise ValueError("Username cannot be empty")
    data = _load_data()
    user = data["users"].get(username)
    if not user:
        raise KeyError(f"User '{username}' does not exist")
    user["last_active"] = datetime.utcnow().isoformat() + "Z"
    data["current_user"] = username
    _save_data(data)
    return user


def _create_pending_verification(username: str, purpose: str) -> dict[str, Any]:
    data = _load_data()
    code = _generate_code()
    expires_at = (datetime.utcnow() + timedelta(minutes=CODE_TTL_MINUTES)).isoformat() + "Z"
    data["pending_verifications"][username] = {
    "code": code,
    "purpose": purpose,
    "expires_at": expires_at,
    "sent_at": datetime.utcnow().isoformat() + "Z",
    }
    _save_data(data)
    return data["pending_verifications"][username]


def _clear_pending_verification(username: str) -> None:
    data = _load_data()
    if username in data["pending_verifications"]:
        del data["pending_verifications"][username]
        _save_data(data)


def _send_verification_code(user: dict[str, Any], purpose: str, code: str) -> bool:
    subject = f"TutorBot verification code for {purpose}"
    body = (
    f"Hello {user['username']},\n\n"
    f"Your TutorBot verification code is: {code}\n\n"
    f"Enter the code with /verify {user['username']} <code> to complete {purpose}.\n"
    f"This code expires in {CODE_TTL_MINUTES} minutes.\n\n"
    f"If you did not request this, ignore this message.\n"
    f"Thanks,\nTutorBot Team"
    )
    if user.get("email") and SMTP_SERVER and SMTP_USER and SMTP_PASSWORD:
        try:
            _send_email(user["email"], subject, body)
            return True
        except Exception:
            pass
    return False


def _create_user_and_pending(username: str, email: str, password: str) -> tuple[dict[str, Any], dict[str, Any], bool]:
    data = _load_data()
    user = _default_user(username, role="student", email=email, password_hash=_hash_password(password))
    user["last_active"] = datetime.utcnow().isoformat() + "Z"
    data["users"][username] = user
    _save_data(data)
    verification = _create_pending_verification(username, "registration")
    sent = _send_verification_code(user, "registration", verification["code"])
    return user, verification, sent


def login(username: str, password: str) -> tuple[dict[str, Any], dict[str, Any], bool]:
    username = username.strip().lower()
    if not username:
        raise ValueError("Username cannot be empty")
    if not password:
        raise ValueError("Password cannot be empty")
    data = _load_data()
    user = data["users"].get(username)
    if not user:
        raise KeyError(f"User '{username}' does not exist")
    if not user.get("password_hash") or not _verify_password(password, user["password_hash"]):
        raise ValueError("Invalid username or password")
    verification = _create_pending_verification(username, "login")
    sent = _send_verification_code(user, "login", verification["code"])
    return user, verification, sent


def register(username: str, email: str, password: str) -> tuple[dict[str, Any], dict[str, Any], bool]:
    username = username.strip().lower()
    email = email.strip()
    if not username:
        raise ValueError("Username cannot be empty")
    if not email or "@" not in email or "." not in email:
        raise ValueError("A valid email address is required")
    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters")
    data = _load_data()
    if username in data["users"]:
        raise KeyError(f"User '{username}' already exists")
    user = _default_user(username, role="student", email=email, password_hash=_hash_password(password))
    user["last_active"] = datetime.utcnow().isoformat() + "Z"
    data["users"][username] = user
    _save_data(data)
    verification = _create_pending_verification(username, "registration")
    sent = _send_verification_code(user, "registration", verification["code"])
    return user, verification, sent


def verify(username: str, code: str, purpose: str | None = None) -> dict[str, Any]:
    username = username.strip().lower()
    code = code.strip()
    if not username:
        raise ValueError("Username cannot be empty")
    if not code:
        raise ValueError("Verification code cannot be empty")
    data = _load_data()
    pending = data["pending_verifications"].get(username)
    if not pending:
        raise KeyError("No pending verification found for that user")
    if purpose and pending["purpose"] != purpose:
        raise ValueError(f"Expected purpose '{pending['purpose']}' for this verification")
    if pending["code"] != code:
        raise ValueError("Invalid verification code")
    if datetime.utcnow().isoformat() + "Z" > pending["expires_at"]:
        raise ValueError("Verification code has expired")
    _clear_pending_verification(username)
    user = set_current_user(username)
    user["verified"] = True
    data = _load_data()
    data["users"][username] = user
    _save_data(data)
    return user


def logout() -> dict[str, Any]:
    data = _load_data()
    data["current_user"] = "guest"
    data["users"]["guest"]["last_active"] = datetime.utcnow().isoformat() + "Z"
    _save_data(data)
    return data["users"]["guest"]


def list_users() -> list[dict[str, Any]]:
    data = _load_data()
    return sorted(data["users"].values(), key=lambda user: (user["role"] != "admin", user["username"]))


def get_user(username: str) -> dict[str, Any] | None:
    data = _load_data()
    return data["users"].get(username.strip().lower())


def set_user_role(username: str, role: str) -> dict[str, Any]:
    if role not in ("student", "admin", "guest"):
        raise ValueError("Invalid role")
    data = _load_data()
    user = data["users"].get(username.strip().lower())
    if not user:
        raise KeyError(f"User '{username}' does not exist")
    user["role"] = role
    _save_data(data)
    return user


def delete_user(username: str) -> None:
    username = username.strip().lower()
    data = _load_data()
    if username == "guest":
        raise ValueError("Cannot delete the guest account")
    if username not in data["users"]:
        raise KeyError(f"User '{username}' does not exist")
    admins = [u for u in data["users"].values() if u["role"] == "admin" and u["username"] != username]
    if not admins and data["users"][username]["role"] == "admin":
        raise ValueError("Cannot delete the last admin user")
    if data.get("current_user") == username:
        data["current_user"] = "guest"
    del data["users"][username]
    _save_data(data)


def is_admin(username: str | None = None) -> bool:
    user = get_current_user() if username is None else get_user(username)
    return bool(user and user.get("role") == "admin")
=======
import hashlib
import json 
import random
import smtplib
import ssl
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path 
from typing import Any

from config import EMAIL_FROM, SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_USE_TLS

USER_DATA_FILE = Path(__file__).resolve().parent / "user_data.json"
DEFAULT_ADMIN_PASSWORD = "admin"
CODE_TTL_MINUTES = 15


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _verify_password(password: str, password_hash: str) -> bool:
    return _hash_password(password) == password_hash


def _default_user(username: str, role: str = "student", email: str = "", password_hash: str | None = None) -> dict[str, Any]:
    return {
    "username": username,
    "role": role,
    "email": email,
    "password_hash": password_hash,
    "created_at": datetime.utcnow().isoformat() + "Z",
    "last_active": None,
    "verified": False,
    }


def _load_raw() -> dict[str, Any]:
    if not USER_DATA_FILE.exists():
        return {}
    try:
        with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_raw(data: dict[str, Any]) -> None:
    try:
        with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass


def _ensure_structure(data: dict[str, Any]) -> dict[str, Any]:
    if "users" not in data or not isinstance(data["users"], dict):
        data["users"] = {}
    if "current_user" not in data or not isinstance(data["current_user"], str):
        data["current_user"] = "guest"
    if "pending_verifications" not in data or not isinstance(data["pending_verifications"], dict):
        data["pending_verifications"] = {}
    return data


def _ensure_default_users(data: dict[str, Any]) -> dict[str, Any]:
    data = _ensure_structure(data)
    users = data["users"]
    if "guest" not in users:
        users["guest"] = _default_user("guest", role="guest", email="guest@tutorbot.com")
    if "admin" not in users:
        users["admin"] = _default_user(
        "admin",
        role="admin",
        email="admin@tutorbot.com",
        password_hash=_hash_password(DEFAULT_ADMIN_PASSWORD),
        )
    return data


def _load_data() -> dict[str, Any]:
    raw = _load_raw()
    raw = _ensure_structure(raw)
    raw = _ensure_default_users(raw)
    return raw


def _generate_code() -> str:
    return f"{random.randint(100000, 999999)}"


def _send_email(to_email: str, subject: str, body: str) -> None:
    if not SMTP_SERVER or not SMTP_USER or not SMTP_PASSWORD:
        return
    message = EmailMessage()
    message["From"] = EMAIL_FROM
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)
    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
        if SMTP_USE_TLS:
            server.starttls(context=context)
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(message)


def _save_data(data: dict[str, Any]) -> None:
    _save_raw(data)


def get_current_user() -> dict[str, Any]:
    data = _load_data()
    username = data.get("current_user", "guest")
    user = data["users"].get(username)
    if not user:
        user = _default_user(username)
        data["users"][username] = user
        _save_data(data)
    return user


def set_current_user(username: str) -> dict[str, Any]:
    username = username.strip().lower()
    if not username:
        raise ValueError("Username cannot be empty")
    data = _load_data()
    user = data["users"].get(username)
    if not user:
        raise KeyError(f"User '{username}' does not exist")
    user["last_active"] = datetime.utcnow().isoformat() + "Z"
    data["current_user"] = username
    _save_data(data)
    return user


def _create_pending_verification(username: str, purpose: str) -> dict[str, Any]:
    data = _load_data()
    code = _generate_code()
    expires_at = (datetime.utcnow() + timedelta(minutes=CODE_TTL_MINUTES)).isoformat() + "Z"
    data["pending_verifications"][username] = {
    "code": code,
    "purpose": purpose,
    "expires_at": expires_at,
    "sent_at": datetime.utcnow().isoformat() + "Z",
    }
    _save_data(data)
    return data["pending_verifications"][username]


def _clear_pending_verification(username: str) -> None:
    data = _load_data()
    if username in data["pending_verifications"]:
        del data["pending_verifications"][username]
        _save_data(data)


def _send_verification_code(user: dict[str, Any], purpose: str, code: str) -> bool:
    subject = f"TutorBot verification code for {purpose}"
    body = (
    f"Hello {user['username']},\n\n"
    f"Your TutorBot verification code is: {code}\n\n"
    f"Enter the code with /verify {user['username']} <code> to complete {purpose}.\n"
    f"This code expires in {CODE_TTL_MINUTES} minutes.\n\n"
    f"If you did not request this, ignore this message.\n"
    f"Thanks,\nTutorBot Team"
    )
    if user.get("email") and SMTP_SERVER and SMTP_USER and SMTP_PASSWORD:
        try:
            _send_email(user["email"], subject, body)
            return True
        except Exception:
            pass
    return False


def _create_user_and_pending(username: str, email: str, password: str) -> tuple[dict[str, Any], dict[str, Any], bool]:
    data = _load_data()
    user = _default_user(username, role="student", email=email, password_hash=_hash_password(password))
    user["last_active"] = datetime.utcnow().isoformat() + "Z"
    data["users"][username] = user
    _save_data(data)
    verification = _create_pending_verification(username, "registration")
    sent = _send_verification_code(user, "registration", verification["code"])
    return user, verification, sent


def login(username: str, password: str) -> tuple[dict[str, Any], dict[str, Any], bool]:
    username = username.strip().lower()
    if not username:
        raise ValueError("Username cannot be empty")
    if not password:
        raise ValueError("Password cannot be empty")
    data = _load_data()
    user = data["users"].get(username)
    if not user:
        raise KeyError(f"User '{username}' does not exist")
    if not user.get("password_hash") or not _verify_password(password, user["password_hash"]):
        raise ValueError("Invalid username or password")
    verification = _create_pending_verification(username, "login")
    sent = _send_verification_code(user, "login", verification["code"])
    return user, verification, sent


def register(username: str, email: str, password: str) -> tuple[dict[str, Any], dict[str, Any], bool]:
    username = username.strip().lower()
    email = email.strip()
    if not username:
        raise ValueError("Username cannot be empty")
    if not email or "@" not in email or "." not in email:
        raise ValueError("A valid email address is required")
    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters")
    data = _load_data()
    if username in data["users"]:
        raise KeyError(f"User '{username}' already exists")
    user = _default_user(username, role="student", email=email, password_hash=_hash_password(password))
    user["last_active"] = datetime.utcnow().isoformat() + "Z"
    data["users"][username] = user
    _save_data(data)
    verification = _create_pending_verification(username, "registration")
    sent = _send_verification_code(user, "registration", verification["code"])
    return user, verification, sent


def verify(username: str, code: str, purpose: str | None = None) -> dict[str, Any]:
    username = username.strip().lower()
    code = code.strip()
    if not username:
        raise ValueError("Username cannot be empty")
    if not code:
        raise ValueError("Verification code cannot be empty")
    data = _load_data()
    pending = data["pending_verifications"].get(username)
    if not pending:
        raise KeyError("No pending verification found for that user")
    if purpose and pending["purpose"] != purpose:
        raise ValueError(f"Expected purpose '{pending['purpose']}' for this verification")
    if pending["code"] != code:
        raise ValueError("Invalid verification code")
    if datetime.utcnow().isoformat() + "Z" > pending["expires_at"]:
        raise ValueError("Verification code has expired")
    _clear_pending_verification(username)
    user = set_current_user(username)
    user["verified"] = True
    data = _load_data()
    data["users"][username] = user
    _save_data(data)
    return user


def logout() -> dict[str, Any]:
    data = _load_data()
    data["current_user"] = "guest"
    data["users"]["guest"]["last_active"] = datetime.utcnow().isoformat() + "Z"
    _save_data(data)
    return data["users"]["guest"]


def list_users() -> list[dict[str, Any]]:
    data = _load_data()
    return sorted(data["users"].values(), key=lambda user: (user["role"] != "admin", user["username"]))


def get_user(username: str) -> dict[str, Any] | None:
    data = _load_data()
    return data["users"].get(username.strip().lower())


def set_user_role(username: str, role: str) -> dict[str, Any]:
    if role not in ("student", "admin", "guest"):
        raise ValueError("Invalid role")
    data = _load_data()
    user = data["users"].get(username.strip().lower())
    if not user:
        raise KeyError(f"User '{username}' does not exist")
    user["role"] = role
    _save_data(data)
    return user


def delete_user(username: str) -> None:
    username = username.strip().lower()
    data = _load_data()
    if username == "guest":
        raise ValueError("Cannot delete the guest account")
    if username not in data["users"]:
        raise KeyError(f"User '{username}' does not exist")
    admins = [u for u in data["users"].values() if u["role"] == "admin" and u["username"] != username]
    if not admins and data["users"][username]["role"] == "admin":
        raise ValueError("Cannot delete the last admin user")
    if data.get("current_user") == username:
        data["current_user"] = "guest"
    del data["users"][username]
    _save_data(data)


def is_admin(username: str | None = None) -> bool:
    user = get_current_user() if username is None else get_user(username)
    return bool(user and user.get("role") == "admin")
>>>>>>> 6696ff70c425dd6f93af6c93d97bcaa324f38300
