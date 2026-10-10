"""
Campus Mate - nightly reminder bot.

Leave this running in a second terminal:   python reminder_bot.py
Every evening (default 8 PM, change it in the app's Setup tab) it sends the
student a Telegram message listing everything due tomorrow, today or overdue.
"""
import time
from datetime import datetime

from common import get_setting, init_db, send_digest, set_setting

init_db()
print("Campus Mate reminder bot is running. Press Ctrl + C to stop.")

while True:
    now = datetime.now()
    hour = int(get_setting("digest_hour", "20") or 20)
    today = now.date().isoformat()
    if now.hour >= hour and get_setting("last_digest") != today:
        ok, info = send_digest()
        print(f"[{now:%H:%M}] {'OK' if ok else 'FAILED'}: {info}")
        if ok:
            set_setting("last_digest", today)
    time.sleep(60)
