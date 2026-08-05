import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

STREAK_FILE = Path(__file__).resolve().parent / "streak_data.json"

@dataclass
class StreakResult:
    count: int
    is_new_day: bool
    longest: int


def _load_raw() -> dict:
    if not STREAK_FILE.exists():
        return {}
    try:
        with open(STREAK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_raw(data: dict) -> None:
    try:
        with open(STREAK_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass


def _ensure_user_data(data: dict, username: str) -> dict:
    if "users" not in data or not isinstance(data["users"], dict):
        data["users"] = {}
    username = username.strip().lower() or "guest"
    if username not in data["users"] or not isinstance(data["users"][username], dict):
        data["users"][username] = {
            "streak": 0,
            "longest": 0,
            "last_date": None,
        }
    else:
        data["users"][username].setdefault("streak", 0)
        data["users"][username].setdefault("longest", 0)
        data["users"][username].setdefault("last_date", None)
    return data


def update_streak_for_user(username: str, activity_date: date | None = None) -> StreakResult:
    data = _load_raw()
    username = username.strip().lower() or "guest"
    data = _ensure_user_data(data, username)

    today = activity_date or date.today()
    user_data = data["users"][username]
    last_date_str = user_data.get("last_date")
    current_streak = user_data.get("streak", 0)
    longest_streak = user_data.get("longest", 0)

    is_new_day = False
    if last_date_str is None:
        current_streak = 1
        is_new_day = True
    else:
        try:
            last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
        except ValueError:
            last_date = None

        if last_date == today:
            pass
        elif last_date is not None and (today - last_date).days == 1:
            current_streak += 1
            is_new_day = True
        else:
            current_streak = 1
            is_new_day = True

    longest_streak = max(longest_streak, current_streak)
    user_data["streak"] = current_streak
    user_data["longest"] = longest_streak
    user_data["last_date"] = today.strftime("%Y-%m-%d")

    _save_raw(data)
    return StreakResult(count=current_streak, is_new_day=is_new_day, longest=longest_streak)


def get_current_streak(username: str) -> StreakResult:
    data = _load_raw()
    data = _ensure_user_data(data, username)
    user_data = data["users"][username]
    return StreakResult(
        count=user_data.get("streak", 0),
        is_new_day=False,
        longest=user_data.get("longest", 0),
    )
