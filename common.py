"""
Campus Mate - shared helpers (database, Telegram, AI, reminder parsing).
Used by both app.py (the website) and reminder_bot.py (nightly notifications).
"""
import json
import os
import re
import sqlite3
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta

import pandas as pd

# The database file lives next to this script so the app and the bot share it.
DB = os.environ.get(
    "CAMPUSMATE_DB",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "campusmate.db"),
)


# ----------------------------------------------------------------------------
# Database
# ----------------------------------------------------------------------------
def run(sql, params=()):
    with sqlite3.connect(DB) as c:
        c.execute(sql, params)
        c.commit()


def table(sql, params=()):
    with sqlite3.connect(DB) as c:
        return pd.read_sql_query(sql, c, params=params)


def init_db():
    with sqlite3.connect(DB) as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS reminders(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT, kind TEXT, due TEXT, done INTEGER DEFAULT 0,
                due_time TEXT DEFAULT '', done_at TEXT);
            CREATE TABLE IF NOT EXISTS expenses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day TEXT, amount REAL, mode TEXT, category TEXT, note TEXT);
            CREATE TABLE IF NOT EXISTS marks(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT, exam TEXT, score REAL, max_score REAL, day TEXT);
            CREATE TABLE IF NOT EXISTS settings(
                key TEXT PRIMARY KEY, value TEXT);
            """
        )
        cols = [r[1] for r in c.execute("PRAGMA table_info(reminders)")]
        if "due_time" not in cols:
            c.execute("ALTER TABLE reminders ADD COLUMN due_time TEXT DEFAULT ''")
        if "done_at" not in cols:
            c.execute("ALTER TABLE reminders ADD COLUMN done_at TEXT")
        c.commit()


def get_setting(key, default=""):
    df = table("SELECT value FROM settings WHERE key=?", (key,))
    return df["value"][0] if len(df) else default


def set_setting(key, value):
    run("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, str(value)))


def secret(name):
    """Look for a key in environment variables / Streamlit secrets first, then the Setup tab."""
    return os.environ.get(name) or get_setting(name)


# ----------------------------------------------------------------------------
# Telegram
# ----------------------------------------------------------------------------
def tg_call(method, payload=None):
    token = secret("TELEGRAM_BOT_TOKEN")
    if not token:
        return False, "Telegram bot token is not set (see the Setup tab)."
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=json.dumps(payload or {}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return True, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return False, json.loads(e.read().decode()).get("description", "Telegram error")
        except Exception:
            return False, "Telegram error"
    except Exception as e:
        return False, f"Could not reach Telegram: {e}"


def tg_send(chat_id, text):
    ok, res = tg_call("sendMessage", {"chat_id": chat_id, "text": text})
    return ok, ("Sent" if ok else res)


def tg_send_location(chat_id, lat, lon):
    return tg_call("sendLocation", {"chat_id": chat_id, "latitude": lat, "longitude": lon})


def tg_find_chats():
    """People who pressed Start / sent a message to the bot -> {chat_id: name}."""
    ok, res = tg_call("getUpdates")
    if not ok:
        return False, res
    chats = {}
    for u in res.get("result", []):
        ch = (u.get("message") or {}).get("chat")
        if ch:
            name = " ".join(x for x in [ch.get("first_name"), ch.get("last_name")] if x) or ch.get("title", "Unknown")
            chats[ch["id"]] = name
    return True, chats


# ----------------------------------------------------------------------------
# AI (Gemini free tier, or Anthropic). Returns None if no key / any problem.
# ----------------------------------------------------------------------------
AI_STATUS = {"error": ""}


def ai_available():
    return bool(secret("GEMINI_API_KEY") or secret("ANTHROPIC_API_KEY"))


def _post(url, body, headers):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode())["error"]["message"]
        except Exception:
            detail = ""
        raise RuntimeError(f"HTTP {e.code}: {detail}".strip())


GEMINI_MODELS = ["gemini-flash-latest", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]


def ask_ai(prompt):
    AI_STATUS["error"] = ""
    gem, ant = secret("GEMINI_API_KEY"), secret("ANTHROPIC_API_KEY")
    try:
        if gem:
            gem = gem.strip()
            models = ([os.environ["GEMINI_MODEL"]] if os.environ.get("GEMINI_MODEL") else []) + GEMINI_MODELS
            last = ""
            for model in models:  # try each model name until one works
                try:
                    d = _post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                        {"contents": [{"parts": [{"text": prompt}]}]},
                        {"Content-Type": "application/json", "x-goog-api-key": gem},
                    )
                    return d["candidates"][0]["content"]["parts"][0]["text"].strip()
                except RuntimeError as e:
                    last = f"{model}: {e}"
                    if "HTTP 404" not in str(e):
                        break  # a different problem (bad key, limit...) - no point trying other models
            AI_STATUS["error"] = last
            return None
        if ant:
            d = _post(
                "https://api.anthropic.com/v1/messages",
                {"model": "claude-haiku-5-5", "max_tokens": 600,
                 "messages": [{"role": "user", "content": prompt}]},
                {"Content-Type": "application/json", "x-api-key": ant.strip(), "anthropic-version": "2023-06-01"},
            )
            return d["content"][0]["text"].strip()
    except Exception as e:
        AI_STATUS["error"] = str(e)
    return None


# ----------------------------------------------------------------------------
# Reminders: understanding what the teacher said
# ----------------------------------------------------------------------------
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
KINDS = [
    ("Test / Exam", r"\b(test|exam|quiz|viva|practical|unit test)\b"),
    ("Homework", r"\b(homework|hw|worksheet)\b"),
    ("Assignment", r"\b(assignment|submit|submission|report)\b"),
    ("Project", r"\b(project|model|presentation|ppt|chart)\b"),
    ("Bring item", r"\b(bring|carry|book|notebook|record|instrument|guitar|kit|uniform|lab coat|calculator|id card)\b"),
]
KIND_NAMES = [k for k, _ in KINDS] + ["Other"]


def detect_kind(text):
    t = text.lower()
    for name, pattern in KINDS:
        if re.search(pattern, t):
            return name
    return "Other"


def parse_due(text):
    t, today = text.lower(), date.today()
    if "day after tomorrow" in t:
        return today + timedelta(days=2), True
    if re.search(r"\b(tomorrow|tmrw|tmr)\b", t):
        return today + timedelta(days=1), True
    if re.search(r"\btoday\b", t):
        return today, True
    m = re.search(r"in (\d+) days?", t)
    if m:
        return today + timedelta(days=int(m.group(1))), True
    for i, d in enumerate(WEEKDAYS):
        if re.search(rf"\b{d}\b", t):
            return today + timedelta(days=(i - today.weekday()) % 7 or 7), True
    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", t)
    if m:
        try:
            year = int(m.group(3)) if m.group(3) else today.year
            year += 2000 if year < 100 else 0
            return date(year, int(m.group(2)), int(m.group(1))), True
        except ValueError:
            pass
    return today + timedelta(days=1), False


def parse_time(text):
    """Find a time like '9 am', '4:30 pm' or 'at 16:30'. Returns 'HH:MM' or ''."""
    t = text.lower()
    m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)", t)
    if m:
        h, mi, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3)[0]
        if 1 <= h <= 12 and mi < 60:
            if ap == "p" and h != 12:
                h += 12
            if ap == "a" and h == 12:
                h = 0
            return f"{h:02d}:{mi:02d}"
    m = re.search(r"\b(?:at|by)\s*([01]?\d|2[0-3]):([0-5]\d)\b", t)
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"
    if re.search(r"\bnoon\b", t):
        return "12:00"
    return ""


def fmt_time(hhmm):
    """'16:30' -> '4:30 PM'"""
    try:
        return datetime.strptime(hhmm, "%H:%M").strftime("%I:%M %p").lstrip("0")
    except Exception:
        return ""


def smart_parse(text):
    """Returns (task, kind, due_date, date_found, used_ai, due_time 'HH:MM' or '')."""
    if ai_available():
        today = date.today()
        out = ask_ai(
            f"Today is {today.strftime('%A, %Y-%m-%d')}. A student noted something a teacher said: \"{text}\"\n"
            f"Reply with ONLY JSON like {{\"task\": \"short clear task\", \"kind\": one of {KIND_NAMES}, "
            f"\"due\": \"YYYY-MM-DD\", \"time\": \"HH:MM in 24h, or empty string if no time is mentioned\"}}. "
            f"If no date is mentioned, use tomorrow."
        )
        if out:
            try:
                d = json.loads(re.search(r"\{.*\}", out, re.S).group(0))
                kind = d.get("kind") if d.get("kind") in KIND_NAMES else detect_kind(text)
                tm = d.get("time") or ""
                if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", tm):
                    tm = parse_time(text)
                return d.get("task") or text, kind, date.fromisoformat(d["due"]), True, True, tm
            except Exception:
                pass
    due, found = parse_due(text)
    return text, detect_kind(text), due, found, False, parse_time(text)


def due_dt(due_str, time_str=""):
    """The exact moment a task is due (end of day if no time was set)."""
    return datetime.fromisoformat(f"{due_str} {time_str or '23:59'}")


def due_label(due_str, time_str=""):
    now = datetime.now()
    d = due_dt(due_str, time_str)
    when = f" at {fmt_time(time_str)}" if time_str else ""
    if now > d:
        if d.date() == now.date():
            return f"🔴 Time passed{when}"
        return f"🔴 Overdue by {(now.date() - d.date()).days} day(s)"
    left = (d.date() - now.date()).days
    if left == 0:
        return f"🟠 Due TODAY{when}"
    if left == 1:
        return f"🟡 Due tomorrow{when}"
    return f"🟢 {left} days left{when}"


def days_label(due_str):
    return due_label(due_str, "")


def tonight_digest():
    """Text listing everything due tomorrow / today / overdue, or None if nothing."""
    today, tomorrow = date.today().isoformat(), (date.today() + timedelta(days=1)).isoformat()
    df = table("SELECT * FROM reminders WHERE done=0 AND due<=? ORDER BY due, COALESCE(NULLIF(due_time,''),'23:59')", (tomorrow,))
    if df.empty:
        return None
    lines = ["🎒 Campus Mate - pack your bag check!"]
    for _, r in df.iterrows():
        tag = "OVERDUE" if r["due"] < today else ("TODAY" if r["due"] == today else "TOMORROW")
        when = f" at {fmt_time(r['due_time'])}" if isinstance(r["due_time"], str) and r["due_time"] else ""
        lines.append(f"• [{tag}] {r['task']} ({r['kind']}){when}")
    return "\n".join(lines)


def send_digest():
    chat = get_setting("student_chat_id")
    if not chat:
        return False, "Student Telegram chat is not set up yet (Setup tab)."
    text = tonight_digest()
    if not text:
        return True, "Nothing due tomorrow, so no message was needed."
    return tg_send(chat, text)
