"""
streak.py

Tracks the user's daily usage streak for TutorBot, persisted to a small
JSON file so it survives restarts.

Rules:
- Opening the app on a new calendar day that is exactly one day after the
  last recorded day extends the streak by 1.
- Opening the app again on the same day the streak was already counted
  leaves it unchanged (no double-counting within a day).
- Opening the app after skipping one or more days resets the streak to 1.
- First-ever run starts the streak at 1.
"""

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


STREAK_FILE = Path(__file__).resolve().parent / "streak_data.json"


@dataclass
class StreakResult:
    count: int
    is_new_day: bool          # True if today's visit just extended/started the streak
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
        pass  # Streak tracking is a nice-to-have; never crash the app over it.


def update_streak_on_open() -> StreakResult:
    """
    Call once per app launch. Reads the stored streak, applies the daily
    rules above based on today's date, persists the result, and returns it.
    """
    data = _load_raw()

    today = date.today()
    last_date_str = data.get("last_date")
    current_streak = data.get("streak", 0)
    longest_streak = data.get("longest", 0)

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
            pass  # already counted today, no change
        elif last_date is not None and (today - last_date).days == 1:
            current_streak += 1
            is_new_day = True
        else:
            current_streak = 1
            is_new_day = True

    longest_streak = max(longest_streak, current_streak)

    _save_raw({
        "streak": current_streak,
        "longest": longest_streak,
        "last_date": today.strftime("%Y-%m-%d"),
    })

    return StreakResult(count=current_streak, is_new_day=is_new_day, longest=longest_streak)


def get_current_streak() -> StreakResult:
    """Reads the streak without mutating it (e.g. for display refreshes)."""
    data = _load_raw()
    return StreakResult(
        count=data.get("streak", 0),
        is_new_day=False,
        longest=data.get("longest", 0),
    )