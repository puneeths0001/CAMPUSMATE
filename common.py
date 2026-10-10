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
from datetime import date, timedelta

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
                task TEXT, kind TEXT, due TEXT, done INTEGER DEFAULT 0);
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


def smart_parse(text):
    """Returns (task, kind, due_date, date_found, used_ai). AI first, simple rules as backup."""
    if ai_available():
        today = date.today()
        out = ask_ai(
            f"Today is {today.strftime('%A, %Y-%m-%d')}. A student noted something a teacher said: \"{text}\"\n"
            f"Reply with ONLY JSON like {{\"task\": \"short clear task\", \"kind\": one of {KIND_NAMES}, "
            f"\"due\": \"YYYY-MM-DD\"}}. If no date is mentioned, use tomorrow."
        )
        if out:
            try:
                d = json.loads(re.search(r"\{.*\}", out, re.S).group(0))
                kind = d.get("kind") if d.get("kind") in KIND_NAMES else detect_kind(text)
                return d.get("task") or text, kind, date.fromisoformat(d["due"]), True, True
            except Exception:
                pass
    due, found = parse_due(text)
    return text, detect_kind(text), due, found, False


def days_label(due_str):
    left = (date.fromisoformat(due_str) - date.today()).days
    if left < 0:
        return f"🔴 Overdue by {-left} day(s)"
    if left == 0:
        return "🟠 Due TODAY"
    if left == 1:
        return "🟡 Due tomorrow"
    return f"🟢 {left} days left"


def tonight_digest():
    """Text listing everything due tomorrow / today / overdue, or None if nothing."""
    today, tomorrow = date.today().isoformat(), (date.today() + timedelta(days=1)).isoformat()
    df = table("SELECT * FROM reminders WHERE done=0 AND due<=? ORDER BY due", (tomorrow,))
    if df.empty:
        return None
    lines = ["🎒 Campus Mate - pack your bag check!"]
    for _, r in df.iterrows():
        tag = "OVERDUE" if r["due"] < today else ("TODAY" if r["due"] == today else "TOMORROW")
        lines.append(f"• [{tag}] {r['task']} ({r['kind']})")
    return "\n".join(lines)


def send_digest():
    chat = get_setting("student_chat_id")
    if not chat:
        return False, "Student Telegram chat is not set up yet (Setup tab)."
    text = tonight_digest()
    if not text:
        return True, "Nothing due tomorrow, so no message was needed."
    return tg_send(chat, text)
