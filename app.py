"""
Campus Mate - your study, money and safety companion.
Run with:  streamlit run app.py
"""
import os
import re
import urllib.parse
import urllib.request
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from common import (
    AI_STATUS, ai_available, ask_ai, days_label, get_setting, init_db, run,
    secret, send_digest, set_setting, smart_parse, table, tg_call, tg_find_chats,
    tg_send, tg_send_location,
)

try:  # real phone GPS (optional extra package)
    from streamlit_js_eval import get_geolocation
except Exception:
    get_geolocation = None

st.set_page_config(page_title="Campus Mate", page_icon="🎓", layout="centered")

# Let keys saved in Streamlit Cloud "Secrets" work like normal environment variables.
try:
    for _k in st.secrets:
        os.environ.setdefault(_k, str(st.secrets[_k]))
except Exception:
    pass

# ----------------------------------------------------------------------------
# Design  (dark glass look: glowing purple / pink / cyan)
# To change colours later, edit the hex codes (like #8B5CF6) in the CSS below.
# ----------------------------------------------------------------------------
CAP = ('<svg width="26" height="26" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">'
       '<polygon points="32,14 58,28 32,42 6,28" fill="#C084FC"/>'
       '<path d="M17 36 v10 c0 5 30 5 30 0 v-10 l-15 7.5 z" fill="#F472B6"/>'
       '<path d="M58 28 v15" stroke="#22D3EE" stroke-width="3.5" stroke-linecap="round"/>'
       '<circle cx="58" cy="46" r="3.5" fill="#22D3EE"/></svg>')

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html, body, .stApp, .stMarkdown, button, input, textarea { font-family: 'Inter', sans-serif !important; }

/* Page background: dark with glowing colour orbs and a faint grid */
.stApp {
  background-color: #06070a;
  background-image:
    radial-gradient(650px circle at 0% 0%, rgba(147,51,234,.30), transparent 60%),
    radial-gradient(520px circle at 100% 30%, rgba(6,182,212,.20), transparent 60%),
    radial-gradient(580px circle at 35% 100%, rgba(219,39,119,.20), transparent 60%),
    linear-gradient(to right, rgba(255,255,255,.025) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(255,255,255,.025) 1px, transparent 1px);
  background-size: auto, auto, auto, 64px 64px, 64px 64px;
  background-attachment: fixed;
}
[data-testid="stHeader"] { background: transparent; }
footer { visibility: hidden; }
.block-container { padding-top: 1.5rem; max-width: 780px; }
h1, h2, h3 { letter-spacing: -0.02em; font-weight: 800; }

/* Header */
.cm-nav { display:flex; align-items:center; gap:12px; padding:10px 16px; margin-bottom:18px;
  background: rgba(6,7,10,.7); border:1px solid rgba(255,255,255,.08); border-radius:18px;
  backdrop-filter: blur(20px); }
.cm-logo { width:44px; height:44px; border-radius:14px; padding:1.5px;
  background: linear-gradient(135deg,#8B5CF6,#EC4899,#06B6D4); }
.cm-logo > div { width:100%; height:100%; background:#0A0B10; border-radius:12.5px;
  display:flex; align-items:center; justify-content:center; }
.cm-brand { font-weight:800; font-size:1.3rem; letter-spacing:-0.01em; color:#fff; }
.cm-brand span { color:#8B5CF6; }
.cm-hero { text-align:center; margin:6px 0 22px; }
.cm-pill { display:inline-flex; align-items:center; gap:8px; padding:6px 14px; border-radius:999px;
  background: rgba(18,20,29,.55); border:1px solid rgba(139,92,246,.35); color:#c4b5fd;
  font-size:.75rem; font-weight:600; backdrop-filter: blur(16px); }
.cm-ping { width:8px; height:8px; border-radius:50%; background:#EC4899; animation: cmPing 1.6s infinite; }
@keyframes cmPing { 0% { box-shadow:0 0 0 0 rgba(236,72,153,.7); } 100% { box-shadow:0 0 0 10px rgba(236,72,153,0); } }
.cm-title { font-size:2rem; font-weight:800; line-height:1.15; margin:14px 0 4px; color:#fff; }
.gradient-text { background: linear-gradient(135deg,#A855F7 0%,#EC4899 50%,#3B82F6 100%);
  -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; }

/* Glass cards */
div[data-testid="stMetric"], [data-testid="stExpander"] {
  background: rgba(18,20,29,.55); border:1px solid rgba(255,255,255,.08);
  border-radius:16px; backdrop-filter: blur(16px); }
div[data-testid="stMetric"] { padding:14px 18px; }
[data-testid="stExpander"] details { border:none; background:transparent; }
[data-testid="stAlert"] { border-radius:14px; }

/* Inputs */
div[data-baseweb="input"], div[data-baseweb="base-input"], div[data-baseweb="textarea"],
div[data-baseweb="select"] > div { border-radius:12px; background: rgba(18,20,29,.7); }

/* Buttons: gradient for main actions, glass for the rest */
.stButton > button, .stLinkButton > a { border-radius:14px; font-weight:600;
  background: rgba(18,20,29,.6); border:1px solid rgba(255,255,255,.12); color:#e5e7eb; transition: all .25s; }
.stButton > button:hover, .stLinkButton > a:hover { border-color:#8B5CF6; color:#fff; }
.stButton > button[kind="primary"], button[data-testid="stBaseButton-primary"] {
  background: linear-gradient(90deg,#9333EA,#DB2777,#06B6D4); border:none; color:#fff;
  box-shadow: 0 10px 28px rgba(147,51,234,.35); }
.stButton > button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover {
  transform: scale(1.02); box-shadow: 0 12px 34px rgba(147,51,234,.55); color:#fff; }

/* Tabs */
button[data-baseweb="tab"] { font-weight:600; color:#9ca3af; }
button[data-baseweb="tab"][aria-selected="true"] { color:#fff; }
div[data-baseweb="tab-highlight"] { background: linear-gradient(90deg,#A855F7,#EC4899,#06B6D4) !important;
  height:3px; border-radius:3px; }
div[data-baseweb="tab-border"] { background: rgba(255,255,255,.08) !important; }

::-webkit-scrollbar { width:8px; height:8px; }
::-webkit-scrollbar-track { background:#06070a; }
::-webkit-scrollbar-thumb { background:#1f2937; border-radius:4px; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def header():
    st.markdown(
        f'<div class="cm-nav"><div class="cm-logo"><div>{CAP}</div></div>'
        '<div class="cm-brand">CAMPUS<span>MATE</span></div></div>'
        '<div class="cm-hero"><div class="cm-pill"><span class="cm-ping"></span>'
        'Your study · money · safety companion</div>'
        '<div class="cm-title">Study smart. <span class="gradient-text">Spend wisely.</span> Stay safe.</div></div>',
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------------------
# 1. Reminders
# ----------------------------------------------------------------------------
def reminders_tab():
    st.subheader("📝 Smart Reminders")
    st.caption("Type what the teacher said, in plain words. Campus Mate finds the type and the date.")
    text = st.text_input("What did the teacher say?", placeholder="e.g. Bring chemistry record on Friday")
    if st.button("Add reminder", type="primary") and text.strip():
        task, kind, due, found, used_ai = smart_parse(text.strip())
        run("INSERT INTO reminders(task,kind,due) VALUES(?,?,?)", (task, kind, due.isoformat()))
        how = "🤖 AI" if used_ai else "📏 smart rules"
        if found:
            st.success(f"{how}: saved as **{kind}**, due **{due.strftime('%a, %d %b')}**")
        else:
            st.warning(f"No date found, so I set it for tomorrow ({due.strftime('%a, %d %b')}). Try adding 'on Friday' or '25/10'.")

    df = table("SELECT * FROM reminders WHERE done=0 ORDER BY due")
    if df.empty:
        st.info("No pending reminders. You're all caught up! 🎉")
    else:
        urgent = [d for d in df["due"] if (date.fromisoformat(d) - date.today()).days <= 1]
        if urgent:
            st.error(f"⏰ {len(urgent)} thing(s) due today, tomorrow or overdue. Pack your bag tonight!")
    for _, r in df.iterrows():
        c1, c2, c3 = st.columns([5, 1.4, 1])
        c1.markdown(f"**{r['task']}**  \n{r['kind']} · {days_label(r['due'])} ({r['due']})")
        if c2.button("✅ Done", key=f"done{r['id']}"):
            run("UPDATE reminders SET done=1 WHERE id=?", (int(r["id"]),))
            st.rerun()
        if c3.button("🗑️", key=f"del{r['id']}"):
            run("DELETE FROM reminders WHERE id=?", (int(r["id"]),))
            st.rerun()

    st.divider()
    if st.button("📲 Send me tonight's reminder on Telegram now"):
        ok, info = send_digest()
        (st.success if ok else st.error)(info)


# ----------------------------------------------------------------------------
# 2. Expenses
# ----------------------------------------------------------------------------
def expenses_tab():
    st.subheader("💸 Expense Tracker")
    budget = float(get_setting("budget", "3000") or 3000)
    new_budget = st.number_input("Monthly budget (₹)", min_value=0.0, value=budget, step=100.0)
    if new_budget != budget:
        set_setting("budget", new_budget)

    with st.expander("➕ Add an expense", expanded=True):
        c1, c2 = st.columns(2)
        amount = c1.number_input("Amount (₹)", min_value=0.0, step=10.0)
        mode = c2.selectbox("Paid by", ["UPI", "Cash"])
        c3, c4 = st.columns(2)
        category = c3.selectbox("Category", ["Food", "Travel", "Stationery", "Fees", "Entertainment", "Shopping", "Other"])
        day = c4.date_input("Date", value=date.today())
        note = st.text_input("Note (optional)")
        if st.button("Save expense", type="primary") and amount > 0:
            run("INSERT INTO expenses(day,amount,mode,category,note) VALUES(?,?,?,?,?)",
                (day.isoformat(), amount, mode, category, note))
            st.success("Saved!")
            st.rerun()

    df = table("SELECT * FROM expenses ORDER BY day DESC, id DESC")
    if df.empty:
        st.info("No expenses yet.")
        return
    this = df[df["day"].str.startswith(date.today().strftime("%Y-%m"))]
    spent = this["amount"].sum()
    m1, m2, m3 = st.columns(3)
    m1.metric("Spent this month", f"₹{spent:,.0f}")
    m2.metric("Budget left", f"₹{new_budget - spent:,.0f}")
    upi, cash = this[this["mode"] == "UPI"]["amount"].sum(), this[this["mode"] == "Cash"]["amount"].sum()
    m3.metric("UPI / Cash", f"₹{upi:,.0f} / ₹{cash:,.0f}")
    if new_budget > 0:
        st.progress(min(spent / new_budget, 1.0))
        if spent >= new_budget:
            st.error("🚨 You've crossed your monthly budget!")
        elif spent >= 0.8 * new_budget:
            st.warning("⚠️ You've used over 80% of your budget.")
    if not this.empty:
        by_cat = this.groupby("category")["amount"].sum()
        st.markdown("**Spending by category**")
        st.bar_chart(by_cat)
        st.info(f"💡 Your biggest spending area this month is **{by_cat.idxmax()}**.")
    st.markdown("**Recent transactions**")
    st.dataframe(df[["day", "amount", "mode", "category", "note"]].head(15), hide_index=True)


# ----------------------------------------------------------------------------
# 3. SOS
# ----------------------------------------------------------------------------
def sos_tab():
    st.subheader("🆘 SOS Safety Alert")
    st.caption("One tap sends your live GPS location straight to your guardian on Telegram.")
    name = st.text_input("Your name", value=get_setting("student_name"))
    g_name = st.text_input("Guardian's name", value=get_setting("g_name"))
    g_phone = st.text_input("Guardian's WhatsApp number with country code (backup option)",
                            value=get_setting("g_phone"), placeholder="919876543210")
    if st.button("Save details"):
        set_setting("student_name", name)
        set_setting("g_name", g_name)
        set_setting("g_phone", g_phone)
        st.success("Saved!")

    tg_ready = bool(secret("TELEGRAM_BOT_TOKEN") and get_setting("guardian_chat_id"))
    if tg_ready:
        st.success("✅ Telegram auto-alert is connected.")
    else:
        st.warning("Telegram auto-alert isn't set up yet. Open the ⚙️ Setup tab. The WhatsApp button still works as backup.")

    lat = lon = None
    use_gps = st.checkbox("📍 Use my phone's GPS location")
    if use_gps:
        if get_geolocation is None:
            st.error("GPS add-on not installed. Run: pip install streamlit-js-eval")
        else:
            loc = get_geolocation()
            if loc and "coords" in loc:
                lat, lon = loc["coords"]["latitude"], loc["coords"]["longitude"]
                st.success(f"Location found: {lat:.5f}, {lon:.5f}")
            else:
                st.info("Waiting for location... tap **Allow** when your browser asks.")
    typed = st.text_input("…or type / paste your location", placeholder="Library gate, or a Google Maps link")

    if lat is not None:
        where = f"https://www.google.com/maps?q={lat},{lon}"
    else:
        where = typed or "(location not provided)"
    msg = (f"🚨 EMERGENCY from {name or 'your child'}: I feel unsafe and need help. "
           f"Location: {where}. Please call me immediately.")

    st.markdown("&nbsp;")
    if st.button("🚨 I FEEL UNSAFE", type="primary", use_container_width=True):
        if tg_ready:
            gid = get_setting("guardian_chat_id")
            ok, info = tg_send(gid, msg)
            if ok and lat is not None:
                tg_send_location(gid, lat, lon)
            if ok:
                st.error("🚨 Alert sent to your guardian on Telegram!")
            else:
                st.error(f"Could not send Telegram alert: {info}")
        st.code(msg)
        digits = re.sub(r"[^0-9]", "", g_phone)
        if digits:
            st.link_button(f"📲 Also send to {g_name or 'guardian'} on WhatsApp",
                           f"https://wa.me/{digits}?text={urllib.parse.quote(msg)}")
        st.markdown("**Emergency numbers (India):** 112 (Police/All emergencies) · 1098 (Child helpline) · 181 (Women helpline)")

    if tg_ready and st.button("🧪 Send a TEST message to my guardian"):
        ok, info = tg_send(get_setting("guardian_chat_id"),
                           f"✅ Test from Campus Mate: {name or 'your child'} has connected this safety alert.")
        (st.success if ok else st.error)("Test sent!" if ok else info)


# ----------------------------------------------------------------------------
# 4. Scam shield
# ----------------------------------------------------------------------------
TEXT_RULES = [
    (r"(registration|processing|application|security|refundable|joining)\s+(fee|fees|deposit|charges?)", 3,
     "Asks you to pay a fee. Real scholarships and genuine jobs don't charge you."),
    (r"\b(otp|cvv|pin|password|aadhaar|aadhar)\b", 3, "Asks for sensitive details (OTP/PIN/password/Aadhaar)."),
    (r"(urgent|last chance|hurry|act now|expires (today|soon)|limited seats|within \d+ (hours|minutes))", 1,
     "Creates fake urgency to make you rush."),
    (r"(guaranteed|100% ?(selection|placement|job|success))", 2, "Promises guaranteed results, a classic scam sign."),
    (r"earn\s*(rs\.?|₹|inr)?\s*\d", 2, "Promises easy earnings."),
    (r"(bank|upi|account)\s*(details|number|id)", 2, "Asks for your bank or UPI details."),
    (r"(congratulations|you (have been|are|were) (selected|shortlisted|chosen)|you (won|have won))", 2,
     "Says you're selected or won something you never applied for."),
    (r"(gift card|lottery|prize|lucky draw)", 2, "Mentions prizes, gift cards or lotteries."),
    (r"(whatsapp|telegram)\s*(group|us|number|me)", 1, "Pushes you to move the chat to WhatsApp/Telegram."),
    (r"(work from home|part[- ]time).{0,40}(earn|income|salary)", 2, "Too-good-to-be-true work-from-home offer."),
]
SHORTENERS = {"bit.ly", "tinyurl.com", "goo.gl", "t.co", "cutt.ly", "rb.gy", "is.gd", "shorturl.at", "ow.ly", "tiny.cc"}
RISKY_TLDS = (".xyz", ".top", ".club", ".online", ".site", ".click", ".buzz", ".work", ".info", ".link", ".live", ".shop")
OFFICIAL_ENDINGS = (".gov.in", ".nic.in", ".ac.in", ".edu", ".edu.in", ".gov")
BAIT_WORDS = ("scholarship", "job", "offer", "hackathon", "placement", "internship", "verify", "reward", "claim", "career")
URL_RE = re.compile(
    r"(https?://[^\s]+|www\.[^\s]+|\b[\w-]+(?:\.[\w-]+)*\.(?:com|in|org|net|xyz|top|club|online|site|link|info|ly|gl|co|click|live|shop)\b(?:/[^\s]*)?)",
    re.I,
)


def analyze(text):
    score, reasons, urls = 0, [], URL_RE.findall(text)
    low = text.lower()
    for pattern, pts, why in TEXT_RULES:
        if re.search(pattern, low):
            score += pts
            reasons.append(why)
    for u in urls:
        full = u if u.startswith("http") else "http://" + u
        host = (urllib.parse.urlparse(full).hostname or "").lower()
        if host.endswith(OFFICIAL_ENDINGS):
            score -= 2
            reasons.append(f"✅ `{host}` ends with an official government/education domain.")
            continue
        if host in SHORTENERS:
            score += 2
            reasons.append(f"`{host}` is a link shortener that hides the real destination.")
        if host.endswith(RISKY_TLDS):
            score += 2
            reasons.append(f"`{host}` uses an extension often used by scam sites.")
        if full.startswith("http://"):
            score += 1
            reasons.append(f"`{host}` isn't using secure HTTPS.")
        if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", host):
            score += 3
            reasons.append("The link is a raw IP address, not a real website name.")
        if host.count("-") >= 2:
            score += 1
            reasons.append(f"`{host}` has many hyphens, common in fake lookalike sites.")
        if any(w in host for w in BAIT_WORDS):
            score += 2
            reasons.append(f"`{host}` is full of bait words (scholarship/job/offer...) but isn't an official domain.")
    return max(score, 0), reasons, urls


def scam_tab():
    st.subheader("🛡️ Scam Link Shield")
    st.caption("Paste a message or link about scholarships, hackathons, placements or job offers.")
    text = st.text_area("Paste here", height=130,
                        placeholder="Congratulations! You are selected for a scholarship. Pay ₹499 registration fee at http://nsp-scholar-claim.xyz")
    if st.button("Check it", type="primary") and text.strip():
        score, reasons, urls = analyze(text)
        if score >= 5:
            st.error(f"🔴 HIGH RISK (score {score}). Do NOT click or pay anything.")
        elif score >= 2:
            st.warning(f"🟡 SUSPICIOUS (score {score}). Verify on the official website before trusting it.")
        else:
            st.success(f"🟢 No obvious red flags (score {score}). Still, never share OTPs or pay to get an opportunity.")
        if urls:
            st.write("**Links found:**", ", ".join(f"`{u}`" for u in urls))
        for r in reasons:
            st.write("•", r)
        if ai_available():
            with st.spinner("AI is taking a second look..."):
                ai = ask_ai("A student received this message. In 3 short, simple sentences say whether it looks "
                            f"like a scam, why, and what they should do:\n\n{text}")
            if ai:
                st.info("🤖 " + ai)
            else:
                st.caption(f"(AI explanation unavailable: {AI_STATUS['error']})")
    with st.expander("🔒 Safety rules to remember"):
        st.markdown(
            "- Real scholarships, jobs and hackathons **never** ask for a fee to select you.\n"
            "- **Never** share OTP, PIN or password with anyone.\n"
            "- Check scholarships on the official site: *scholarships.gov.in*.\n"
            "- If it says 'urgent', slow down. Scammers rush you.\n"
            "- Report cyber fraud: **1930** or *cybercrime.gov.in*."
        )


# ----------------------------------------------------------------------------
# 5. Progress
# ----------------------------------------------------------------------------
def progress_tab():
    st.subheader("📈 Progress Report")
    with st.expander("➕ Add marks", expanded=True):
        c1, c2 = st.columns(2)
        subject = c1.text_input("Subject", placeholder="Maths")
        exam = c2.text_input("Exam name", placeholder="Unit Test 1")
        c3, c4, c5 = st.columns(3)
        score = c3.number_input("Marks scored", min_value=0.0, step=1.0)
        max_score = c4.number_input("Out of", min_value=1.0, value=100.0, step=1.0)
        day = c5.date_input("Date", value=date.today(), key="mark_date")
        if st.button("Save marks", type="primary") and subject.strip() and exam.strip():
            if score > max_score:
                st.error("Marks scored can't be more than the total.")
            else:
                run("INSERT INTO marks(subject,exam,score,max_score,day) VALUES(?,?,?,?,?)",
                    (subject.strip().title(), exam.strip(), score, max_score, day.isoformat()))
                st.success("Saved!")
                st.rerun()

    df = table("SELECT * FROM marks ORDER BY day, id")
    if df.empty:
        st.info("Add your marks to see your progress report.")
        return
    df["pct"] = (df["score"] / df["max_score"] * 100).round(1)
    avg = df.groupby("subject")["pct"].mean().round(1).sort_values()
    st.metric("Overall average", f"{df['pct'].mean():.1f}%")
    st.markdown("**Average by subject**")
    st.bar_chart(avg)
    if df["exam"].nunique() > 1:
        st.markdown("**Trend over time**")
        st.line_chart(df.pivot_table(index="day", columns="subject", values="pct", aggfunc="mean"))

    st.markdown("### 🎯 Your improvement plan")
    weak = []
    for subj, g in df.groupby("subject"):
        dropping = len(g) >= 2 and g["pct"].iloc[-1] < g["pct"].iloc[-2] - 5
        if g["pct"].mean() < 60 or dropping:
            weak.append((subj, g["pct"].mean(), dropping))
    if not weak:
        st.success("Great work! No weak subjects. Keep revising regularly. 🌟")
    for subj, a, dropping in weak:
        why = "scores are dropping" if dropping else f"average is {a:.0f}%"
        st.warning(f"**{subj}**: {why}. Spend 45 min daily: 20 min revising notes, 20 min solving past questions, 5 min fixing mistakes.")
    st.caption(f"Your strongest subject is **{avg.index[-1]}** ({avg.iloc[-1]:.0f}%). Use the same habits for the weaker ones.")

    if st.button("🤖 Get a personalised AI study plan"):
        if not ai_available():
            st.info("Add a free AI key in the ⚙️ Setup tab to enable this. The plan above works without it.")
        else:
            with st.spinner("Building your plan..."):
                ai = ask_ai(f"A student's average % by subject is {avg.to_dict()}. Give a friendly 7-day study plan "
                            "in under 150 words, focused on the weakest subjects.")
            if ai:
                st.info(ai)
            else:
                st.error(f"AI unavailable: {AI_STATUS['error']}")


# ----------------------------------------------------------------------------
# 6. Setup
# ----------------------------------------------------------------------------
def key_box(label, name, help_text):
    """A password box that saves a key. Shows if it's already set elsewhere (env/Secrets)."""
    if os.environ.get(name):
        st.success(f"✅ {label} is set (from Secrets / environment).")
        return
    current = get_setting(name)
    val = st.text_input(label, value=current, type="password", help=help_text)
    if val != current:
        set_setting(name, val.strip())
        st.rerun()


def setup_tab():
    st.subheader("⚙️ Setup")

    st.markdown("#### 🤖 AI (free)")
    st.caption("Get a free key at **aistudio.google.com/apikey** (Google Gemini). Paste it here.")
    key_box("Gemini API key", "GEMINI_API_KEY", "From aistudio.google.com/apikey")
    if ai_available() and st.button("Test AI"):
        out = ask_ai("Reply with exactly: AI is working")
        if out:
            st.success(out)
        else:
            st.error(f"AI failed: {AI_STATUS['error']}")

    st.markdown("#### 📡 Telegram bot")
    st.caption("1) In Telegram, search **@BotFather** → send `/newbot` → copy the token it gives you.")
    key_box("Telegram bot token", "TELEGRAM_BOT_TOKEN", "Looks like 123456789:ABC...")
    if secret("TELEGRAM_BOT_TOKEN"):
        st.caption("2) Open your new bot in Telegram and press **Start**. Ask your guardian to do the same.")
        if st.button("🔍 Find chats"):
            ok, res = tg_find_chats()
            if ok and res:
                st.session_state["chats"] = res
            elif ok:
                st.warning("No chats found yet. Make sure you and your guardian pressed Start on the bot.")
            else:
                st.error(res)
        chats = st.session_state.get("chats", {})
        if chats:
            options = {f"{n} ({cid})": cid for cid, n in chats.items()}
            labels = list(options)
            s_pick = st.selectbox("Which one is the STUDENT?", labels, key="s_pick")
            g_pick = st.selectbox("Which one is the GUARDIAN?", labels, key="g_pick")
            if st.button("Save Telegram contacts"):
                set_setting("student_chat_id", options[s_pick])
                set_setting("guardian_chat_id", options[g_pick])
                st.success("Saved! SOS alerts and nightly reminders are ready.")
        st.caption(f"Student chat: `{get_setting('student_chat_id') or 'not set'}` · "
                   f"Guardian chat: `{get_setting('guardian_chat_id') or 'not set'}`")

    st.markdown("#### 🌙 Nightly reminder time")
    hour = int(get_setting("digest_hour", "20") or 20)
    new_hour = st.slider("Send tomorrow's reminders at (24h clock)", 15, 23, hour)
    if new_hour != hour:
        set_setting("digest_hour", new_hour)
    st.caption("Keep `python reminder_bot.py` running in a second terminal to send these automatically.")

    st.markdown("#### 🧪 Demo data")
    c1, c2 = st.columns(2)
    if c1.button("Load demo data"):
        today = date.today()
        run("DELETE FROM reminders"); run("DELETE FROM expenses"); run("DELETE FROM marks")
        for task, kind, d in [("Bring chemistry record", "Bring item", 1), ("Maths unit test", "Test / Exam", 3),
                              ("Physics assignment submission", "Assignment", 2), ("Science project model", "Project", 6)]:
            run("INSERT INTO reminders(task,kind,due) VALUES(?,?,?)", (task, kind, (today + timedelta(days=d)).isoformat()))
        for i, (amt, mode, cat, note) in enumerate([(120, "UPI", "Food", "Canteen"), (60, "Cash", "Travel", "Bus"),
                                                    (250, "UPI", "Stationery", "Notebooks"), (180, "UPI", "Entertainment", "Movie"),
                                                    (90, "Cash", "Food", "Snacks"), (400, "UPI", "Shopping", "Headphones")]):
            run("INSERT INTO expenses(day,amount,mode,category,note) VALUES(?,?,?,?,?)",
                ((today - timedelta(days=i)).isoformat(), amt, mode, cat, note))
        for subj, exam, sc, d in [("Maths", "Unit Test 1", 72, 60), ("Maths", "Unit Test 2", 61, 20),
                                  ("Physics", "Unit Test 1", 55, 60), ("Physics", "Unit Test 2", 58, 20),
                                  ("English", "Unit Test 1", 84, 60), ("English", "Unit Test 2", 88, 20),
                                  ("Chemistry", "Unit Test 1", 66, 60), ("Chemistry", "Unit Test 2", 70, 20)]:
            run("INSERT INTO marks(subject,exam,score,max_score,day) VALUES(?,?,?,?,?)",
                (subj, exam, sc, 100, (today - timedelta(days=d)).isoformat()))
        st.success("Demo data loaded! Check the other tabs.")
    if c2.button("Clear all data"):
        run("DELETE FROM reminders"); run("DELETE FROM expenses"); run("DELETE FROM marks")
        st.success("All reminders, expenses and marks cleared.")


# ----------------------------------------------------------------------------
init_db()
header()
tabs = st.tabs(["📝 Reminders", "💸 Expenses", "🆘 SOS", "🛡️ Scam Shield", "📈 Progress", "⚙️ Setup"])
for tab, fn in zip(tabs, [reminders_tab, expenses_tab, sos_tab, scam_tab, progress_tab, setup_tab]):
    with tab:
        fn()
