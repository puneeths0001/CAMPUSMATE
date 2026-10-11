"""
Campus Mate - your study, money and safety companion.
Run with:  streamlit run app.py
"""
import html as _html
import os
import re
import urllib.parse
import urllib.request
from datetime import date, datetime, time as dtime, timedelta

import streamlit as st

from common import (
    AI_STATUS, ai_available, ask_ai, due_dt, due_label, fmt_time, get_setting, init_db,
    run, secret, send_digest, set_setting, smart_parse, table, tg_find_chats, tg_send,
    tg_send_location,
)

try:
    import altair as alt
except Exception:
    alt = None

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
# Design  (glass look with a Dark / Light mode switch)
# To change colours later, edit the hex codes (like #8B5CF6) below.
# ----------------------------------------------------------------------------
CAP = ('<svg width="26" height="26" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">'
       '<polygon points="32,14 58,28 32,42 6,28" fill="#C084FC"/>'
       '<path d="M17 36 v10 c0 5 30 5 30 0 v-10 l-15 7.5 z" fill="#F472B6"/>'
       '<path d="M58 28 v15" stroke="#22D3EE" stroke-width="3.5" stroke-linecap="round"/>'
       '<circle cx="58" cy="46" r="3.5" fill="#22D3EE"/></svg>')

PALETTE = ["#8B5CF6", "#EC4899", "#06B6D4", "#F59E0B", "#22C55E", "#3B82F6", "#F43F5E"]

DARK_VARS = dict(bg="#06070a", text="#F3F4F6", muted="#9CA3AF", card="rgba(18,20,29,.55)",
                 border="rgba(255,255,255,.08)", input="rgba(18,20,29,.7)", nav="rgba(6,7,10,.7)",
                 grid="rgba(255,255,255,.025)", o1=".30", o2=".20", o3=".20", btn="rgba(18,20,29,.6)",
                 btnborder="rgba(255,255,255,.12)", btntext="#e5e7eb", pill="rgba(18,20,29,.55)",
                 pilltext="#c4b5fd", thumb="#1f2937")
LIGHT_VARS = dict(bg="#F6F5FB", text="#111827", muted="#4B5563", card="rgba(255,255,255,.8)",
                  border="rgba(17,24,39,.10)", input="#FFFFFF", nav="rgba(255,255,255,.85)",
                  grid="rgba(17,24,39,.035)", o1=".16", o2=".12", o3=".12", btn="rgba(255,255,255,.9)",
                  btnborder="rgba(17,24,39,.15)", btntext="#111827", pill="rgba(255,255,255,.8)",
                  pilltext="#6D28D9", thumb="#CBD5E1")

BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html, body, .stApp, .stMarkdown, button, input, textarea { font-family: 'Inter', sans-serif !important; }
.stApp {
  background-color: var(--bg);
  background-image:
    radial-gradient(650px circle at 0% 0%, rgba(147,51,234,var(--o1)), transparent 60%),
    radial-gradient(520px circle at 100% 30%, rgba(6,182,212,var(--o2)), transparent 60%),
    radial-gradient(580px circle at 35% 100%, rgba(219,39,119,var(--o3)), transparent 60%),
    linear-gradient(to right, var(--grid) 1px, transparent 1px),
    linear-gradient(to bottom, var(--grid) 1px, transparent 1px);
  background-size: auto, auto, auto, 64px 64px, 64px 64px;
  background-attachment: fixed;
}
[data-testid="stHeader"] { background: transparent; }
footer { visibility: hidden; }
.block-container { padding-top: 1.5rem; max-width: 780px; }
h1, h2, h3 { letter-spacing: -0.02em; font-weight: 800; }

.cm-nav { display:flex; align-items:center; gap:12px; padding:10px 16px; margin-bottom:18px;
  background: var(--nav); border:1px solid var(--border); border-radius:18px; backdrop-filter: blur(20px); }
.cm-logo { width:44px; height:44px; border-radius:14px; padding:1.5px;
  background: linear-gradient(135deg,#8B5CF6,#EC4899,#06B6D4); }
.cm-logo > div { width:100%; height:100%; background:#0A0B10; border-radius:12.5px;
  display:flex; align-items:center; justify-content:center; }
.cm-brand { font-weight:800; font-size:1.3rem; letter-spacing:-0.01em; color:var(--text); }
.cm-brand span { color:#8B5CF6; }
.cm-hero { text-align:center; margin:6px 0 14px; }
.cm-pill { display:inline-flex; align-items:center; gap:8px; padding:6px 14px; border-radius:999px;
  background: var(--pill); border:1px solid rgba(139,92,246,.35); color:var(--pilltext);
  font-size:.75rem; font-weight:600; backdrop-filter: blur(16px); }
.cm-ping { width:8px; height:8px; border-radius:50%; background:#EC4899; animation: cmPing 1.6s infinite; }
@keyframes cmPing { 0% { box-shadow:0 0 0 0 rgba(236,72,153,.7); } 100% { box-shadow:0 0 0 10px rgba(236,72,153,0); } }
.cm-title { font-size:2rem; font-weight:800; line-height:1.15; margin:14px 0 4px; color:var(--text); }
.gradient-text { background: linear-gradient(135deg,#A855F7 0%,#EC4899 50%,#3B82F6 100%);
  -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; }

div[data-testid="stMetric"], [data-testid="stExpander"] {
  background: var(--card); border:1px solid var(--border); border-radius:16px; backdrop-filter: blur(16px); }
div[data-testid="stMetric"] { padding:14px 18px; }
[data-testid="stExpander"] details { border:none; background:transparent; }
[data-testid="stAlert"] { border-radius:14px; }

div[data-baseweb="input"], div[data-baseweb="base-input"], div[data-baseweb="textarea"],
div[data-baseweb="select"] > div { border-radius:12px; background: var(--input); }

.stButton > button, .stLinkButton > a { border-radius:14px; font-weight:600;
  background: var(--btn); border:1px solid var(--btnborder); color: var(--btntext); transition: all .25s; }
.stButton > button:hover, .stLinkButton > a:hover { border-color:#8B5CF6; }
.stButton > button[kind="primary"], button[data-testid="stBaseButton-primary"] {
  background: linear-gradient(90deg,#9333EA,#DB2777,#06B6D4); border:none; color:#fff;
  box-shadow: 0 10px 28px rgba(147,51,234,.35); }
.stButton > button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover {
  transform: scale(1.02); box-shadow: 0 12px 34px rgba(147,51,234,.55); color:#fff; }
.st-key-sos_btn button { width:100%; padding:.9rem 0; font-size:1.1rem; }

button[data-baseweb="tab"] { font-weight:600; color: var(--muted); }
button[data-baseweb="tab"][aria-selected="true"] { color: var(--text); }
div[data-baseweb="tab-highlight"] { background: linear-gradient(90deg,#A855F7,#EC4899,#06B6D4) !important;
  height:3px; border-radius:3px; }
div[data-baseweb="tab-border"] { background: var(--border) !important; }

::-webkit-scrollbar { width:8px; height:8px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--thumb); border-radius:4px; }

/* Scam result panel (stays dark in both modes, like a warning screen) */
.sc-panel { background:#170533; border:1px solid rgba(255,255,255,.08); border-radius:28px; padding:24px 22px; margin:10px 0; }
.sc-badge { display:inline-block; background:var(--c, #EF4444); color:#fff; font-weight:800; font-size:.72rem;
  letter-spacing:.08em; padding:5px 12px; border-radius:999px; margin-bottom:14px; }
.sc-panel svg { display:block; }
.sc-head { font-size:2rem; font-weight:800; line-height:1.15; color:#fff; margin:14px 0 16px; }
.sc-box { border-radius:10px; padding:14px 16px; color:#1f2937; font-size:.88rem; line-height:1.5; margin-bottom:20px; }
.sc-sub { color:#d8c9f5; font-size:1.05rem; font-weight:500; margin-bottom:14px; }
.sc-reason { display:flex; gap:14px; margin:0 0 18px; }
.sc-flag { flex:none; padding-top:2px; }
.sc-rt { color:#fff; font-size:1.05rem; font-weight:600; }
.sc-rd { color:#b9a8d6; font-size:.9rem; line-height:1.5; margin-top:2px; }
.sc-steps { background: var(--card); border:1px solid var(--border); border-radius:16px;
  padding:16px 20px; margin:10px 0; backdrop-filter: blur(16px); }
.sc-st { font-weight:700; font-size:1.05rem; margin-bottom:6px; color: var(--text); }
.sc-steps ol { margin:0; padding-left:20px; color: var(--text); line-height:1.7; font-size:.92rem; }
"""

# Extra rules that only apply in LIGHT mode (they turn the dark-themed Streamlit widgets light)
LIGHT_FIX = """
/* ---- text colours ---- */
h1, h2, h3, h4, [data-testid="stHeading"] * { color: var(--text) !important; }
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] strong, [data-testid="stMarkdownContainer"] em,
[data-testid="stMarkdownContainer"] del, [data-testid="stWidgetLabel"] p,
[data-testid="stMetricLabel"] *, [data-testid="stMetricValue"] *,
[data-testid="stExpander"] summary * { color: var(--text) !important; }
[data-testid="stCaptionContainer"] * { color: var(--muted) !important; }
button[data-baseweb="tab"][aria-selected="false"] p { color: var(--muted) !important; }
.stButton > button[kind="primary"] p, button[data-testid="stBaseButton-primary"] p { color:#fff !important; }

/* ---- text boxes, number boxes, text areas: white with a thin border ---- */
[data-testid="stTextInputRootElement"], [data-testid="stNumberInputContainer"],
div[data-baseweb="input"], div[data-baseweb="base-input"], div[data-baseweb="textarea"],
div[data-baseweb="select"] > div { background-color: var(--input) !important; }
div[data-baseweb="input"], div[data-baseweb="textarea"], div[data-baseweb="select"] > div {
  border: 1px solid var(--border) !important; }
input, textarea { background-color: var(--input) !important; color: var(--text) !important;
  -webkit-text-fill-color: var(--text) !important; caret-color: var(--text); }
input::placeholder, textarea::placeholder { color: #9CA3AF !important; -webkit-text-fill-color: #9CA3AF !important; }

/* ---- dropdown boxes (select, time) ---- */
div[data-baseweb="select"] > div div { background-color: transparent !important; color: var(--text) !important; }
div[data-baseweb="select"] svg { fill: var(--muted) !important; color: var(--muted) !important; }

/* ---- the little + and - on number boxes ---- */
[data-testid="stNumberInput"] button { background-color: rgba(17,24,39,.07) !important; color: var(--text) !important; }
[data-testid="stNumberInput"] button svg { fill: var(--text) !important; }

/* ---- expander header bar ---- */
[data-testid="stExpander"], [data-testid="stExpander"] details { background-color: var(--card) !important; }
[data-testid="stExpander"] summary { background-color: transparent !important; }
[data-testid="stExpander"] summary:hover { background-color: rgba(17,24,39,.05) !important; }
[data-testid="stExpander"] summary svg { fill: var(--text) !important; color: var(--text) !important; }

/* ---- progress track and sliders ---- */
div[role="progressbar"] { background-color: rgba(17,24,39,.12) !important; }
[data-testid="stSliderTickBarMin"], [data-testid="stSliderTickBarMax"] { color: var(--muted) !important; }
"""


def is_dark():
    return st.session_state.get("dark_mode", True)


def build_css(dark):
    v = DARK_VARS if dark else LIGHT_VARS
    root = ":root{" + ";".join(f"--{k}:{val}" for k, val in v.items()) + ";color-scheme:" + ("dark" if dark else "light") + "}"
    return "<style>" + root + BASE_CSS + ("" if dark else LIGHT_FIX) + "</style>"


def header():
    st.markdown(
        f'<div class="cm-nav"><div class="cm-logo"><div>{CAP}</div></div>'
        '<div class="cm-brand">CAMPUS<span>MATE</span></div></div>'
        '<div class="cm-hero"><div class="cm-pill"><span class="cm-ping"></span>'
        'Your study · money · safety companion</div>'
        '<div class="cm-title">Study smart. <span class="gradient-text">Spend wisely.</span> Stay safe.</div></div>',
        unsafe_allow_html=True,
    )


# ---- charts that look right in both modes ----
def style_chart(chart):
    fg = "#E5E7EB" if is_dark() else "#374151"
    grid = "rgba(255,255,255,.10)" if is_dark() else "rgba(17,24,39,.12)"
    return (chart.properties(height=260)
            .configure(background="transparent")
            .configure_axis(labelColor=fg, titleColor=fg, gridColor=grid, domainColor=grid, tickColor=grid)
            .configure_legend(labelColor=fg, titleColor=fg)
            .configure_view(strokeWidth=0))


def show_chart(chart):
    st.altair_chart(style_chart(chart), theme=None)


def bar_chart(series, ymax=None):
    if alt is None:
        st.bar_chart(series)
        return
    d = series.reset_index()
    d.columns = ["label", "value"]
    y = alt.Y("value:Q", title=None, scale=alt.Scale(domain=[0, ymax]) if ymax else alt.Undefined)
    show_chart(alt.Chart(d).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6, color="#8B5CF6").encode(
        x=alt.X("label:N", sort=None, title=None, axis=alt.Axis(labelAngle=-30)), y=y,
        tooltip=["label", "value"]))


def line_chart(df):
    """df needs columns: day, subject, pct"""
    if alt is None:
        line_chart(df)
        return
    d = df.groupby(["day", "subject"], as_index=False)["pct"].mean()
    show_chart(alt.Chart(d).mark_line(point=True, strokeWidth=3).encode(
        x=alt.X("day:O", title=None, axis=alt.Axis(labelAngle=-30)),
        y=alt.Y("pct:Q", title=None, scale=alt.Scale(domain=[0, 100])),
        color=alt.Color("subject:N", scale=alt.Scale(range=PALETTE)),
        tooltip=["day", "subject", "pct"]))


# ----------------------------------------------------------------------------
# 1. Reminders
# ----------------------------------------------------------------------------
def tm_of(r):
    return r["due_time"] if isinstance(r["due_time"], str) else ""


def when_text(due_str, time_str):
    txt = date.fromisoformat(due_str).strftime("%a, %d %b")
    return txt + (f", {fmt_time(time_str)}" if time_str else "")


def on_time(r):
    """True/False if we know when the task was finished, otherwise None."""
    d = r["done_at"]
    if not isinstance(d, str) or not d:
        return None
    return datetime.fromisoformat(d) <= due_dt(r["due"], tm_of(r))


def reminders_tab():
    st.subheader("📝 Smart Reminders")
    st.caption("Type what the teacher said. Campus Mate finds the type, date and time. You can also pick them yourself.")

    msg = st.session_state.pop("rem_msg", None)
    if msg:
        (st.success if msg[0] == "ok" else st.warning)(msg[1])
    if st.session_state.pop("reset_rem", False):  # clear the box after saving
        st.session_state.pop("rem_text", None)

    text = st.text_input("What did the teacher say?", placeholder="e.g. Bring chemistry record on Friday at 9 am",
                         key="rem_text")
    how = st.radio("Due date and time", ["Auto-detect from my sentence", "Pick manually"],
                   horizontal=True, key="rem_how")
    pick_date, pick_time, use_time = date.today() + timedelta(days=1), dtime(9, 0), False
    if how == "Pick manually":
        c1, c2 = st.columns(2)
        pick_date = c1.date_input("Due date", value=date.today() + timedelta(days=1),
                                  min_value=date.today(), key="rem_date")
        use_time = c2.checkbox("Set a time", key="rem_use_time")
        if use_time:
            pick_time = c2.time_input("Due time", value=dtime(9, 0), key="rem_time")

    if st.button("Add reminder", type="primary") and text.strip():
        task, kind, due, found, used_ai, tm = smart_parse(text.strip())
        if how == "Pick manually":
            due, found, tm = pick_date, True, (pick_time.strftime("%H:%M") if use_time else "")
        run("INSERT INTO reminders(task,kind,due,due_time) VALUES(?,?,?,?)", (task, kind, due.isoformat(), tm))
        src = "🤖 AI" if used_ai else "📏 smart rules"
        if found:
            st.session_state["rem_msg"] = ("ok", f"{src}: saved as **{kind}**, due **{when_text(due.isoformat(), tm)}**")
        else:
            st.session_state["rem_msg"] = ("warn", f"No date found, so I set it for tomorrow ({when_text(due.isoformat(), tm)}). "
                                                    "Try adding 'on Friday' or '25/10', or use Pick manually.")
        st.session_state["reset_rem"] = True
        st.rerun()

    pend = table("SELECT * FROM reminders WHERE done=0 ORDER BY due, COALESCE(NULLIF(due_time,''),'23:59')")
    done = table("SELECT * FROM reminders WHERE done=1 ORDER BY COALESCE(done_at,'') DESC")

    # ---- completed-task tracking ----
    total = len(pend) + len(done)
    if total:
        known = [k for k in (on_time(r) for _, r in done.iterrows()) if k is not None]
        m1, m2, m3 = st.columns(3)
        m1.metric("Pending", len(pend))
        m2.metric("Completed", len(done))
        m3.metric("Done on time", f"{sum(known) / len(known) * 100:.0f}%" if known else "-")
        st.progress(len(done) / total, text=f"{len(done)} of {total} tasks completed")

    urgent = [d for d in pend["due"] if (date.fromisoformat(d) - date.today()).days <= 1]
    if urgent:
        st.error(f"⏰ {len(urgent)} thing(s) due today, tomorrow or overdue. Pack your bag tonight!")

    # ---- edit a reminder (change its date / time) ----
    eid = st.session_state.get("edit_rem")
    if eid is not None:
        row = pend[pend["id"] == eid]
        if row.empty:
            st.session_state.pop("edit_rem", None)
        else:
            r = row.iloc[0]
            with st.container(border=True):
                st.markdown("**✏️ Edit reminder**")
                new_task = st.text_input("Task", value=r["task"], key=f"rt{eid}")
                c1, c2 = st.columns(2)
                new_date = c1.date_input("Due date", value=date.fromisoformat(r["due"]), key=f"rd{eid}")
                has_t = c2.checkbox("Set a time", value=bool(tm_of(r)), key=f"rc{eid}")
                new_time = ""
                if has_t:
                    old = tm_of(r) or "09:00"
                    t_val = c2.time_input("Due time", value=dtime(int(old[:2]), int(old[3:5])), key=f"rtm{eid}")
                    new_time = t_val.strftime("%H:%M")
                s1, s2 = st.columns(2)
                if s1.button("💾 Save changes", type="primary", key="save_rem") and new_task.strip():
                    run("UPDATE reminders SET task=?, due=?, due_time=? WHERE id=?",
                        (new_task.strip(), new_date.isoformat(), new_time, int(eid)))
                    st.session_state.pop("edit_rem", None)
                    st.toast("Reminder updated ✅")
                    st.rerun()
                if s2.button("Cancel", key="cancel_rem"):
                    st.session_state.pop("edit_rem", None)
                    st.rerun()

    # ---- pending list ----
    if pend.empty:
        st.info("No pending reminders. You're all caught up! 🎉")
    for _, r in pend.iterrows():
        rid, tm = int(r["id"]), tm_of(r)
        c1, c2, c3, c4 = st.columns([5, 1.7, 1, 1])
        c1.markdown(f"**{r['task']}**  \n{r['kind']} · {due_label(r['due'], tm)}  \n📅 {when_text(r['due'], tm)}")
        if c2.button("✅ Done", key=f"done{rid}"):
            run("UPDATE reminders SET done=1, done_at=? WHERE id=?", (datetime.now().strftime("%Y-%m-%d %H:%M"), rid))
            st.toast("Nice work! Task completed 🎉")
            st.rerun()
        if c3.button("✏️", key=f"editr{rid}"):
            st.session_state["edit_rem"] = rid
            st.rerun()
        if c4.button("🗑️", key=f"delr{rid}"):
            run("DELETE FROM reminders WHERE id=?", (rid,))
            st.rerun()

    # ---- completed list ----
    if not done.empty:
        with st.expander(f"✅ Completed tasks ({len(done)})"):
            for _, r in done.iterrows():
                rid, tm = int(r["id"]), tm_of(r)
                ot = on_time(r)
                badge = "" if ot is None else (" · ✅ On time" if ot else " · ⏰ Finished late")
                fin = ""
                if isinstance(r["done_at"], str) and r["done_at"]:
                    fin = " · finished " + datetime.fromisoformat(r["done_at"]).strftime("%d %b, %I:%M %p")
                c1, c2, c3 = st.columns([5, 1.7, 1])
                c1.markdown(f"~~{r['task']}~~  \n{r['kind']} · due {when_text(r['due'], tm)}{fin}{badge}")
                if c2.button("↩️ Undo", key=f"undo{rid}"):
                    run("UPDATE reminders SET done=0, done_at=NULL WHERE id=?", (rid,))
                    st.rerun()
                if c3.button("🗑️", key=f"deld{rid}"):
                    run("DELETE FROM reminders WHERE id=?", (rid,))
                    st.rerun()

    st.divider()
    if st.button("📲 Send me tonight's reminder on Telegram now"):
        ok, info = send_digest()
        if ok:
            st.success(info)
        else:
            st.error(info)


# ----------------------------------------------------------------------------
# 2. Expenses
# ----------------------------------------------------------------------------
CATS = ["Food", "Travel", "Stationery", "Fees", "Entertainment", "Shopping", "Other"]
MODES = ["UPI", "Cash"]


def expense_form(prefix, amount=0.0, mode="UPI", category="Food", day=None, note=""):
    """The boxes used both for adding and for editing an expense."""
    c1, c2 = st.columns(2)
    amount = c1.number_input("Amount (₹)", min_value=0.0, step=10.0, value=float(amount), key=f"{prefix}_amt")
    mode = c2.selectbox("Paid by", MODES, index=MODES.index(mode) if mode in MODES else 0, key=f"{prefix}_mode")
    c3, c4 = st.columns(2)
    category = c3.selectbox("Category", CATS, index=CATS.index(category) if category in CATS else len(CATS) - 1,
                            key=f"{prefix}_cat")
    day = c4.date_input("Date", value=day or date.today(), key=f"{prefix}_day")
    note = st.text_input("Note (optional)", value=note or "", key=f"{prefix}_note")
    return amount, mode, category, day, note


def expenses_tab():
    st.subheader("💸 Expense Tracker")
    budget = float(get_setting("budget", "3000") or 3000)
    new_budget = st.number_input("Monthly budget (₹)", min_value=0.0, value=budget, step=100.0)
    if new_budget != budget:
        set_setting("budget", new_budget)
    budget = new_budget

    # --- add an expense ---
    if st.session_state.pop("reset_add", False):  # clear the boxes after saving
        for k in ("add_amt", "add_note"):
            st.session_state.pop(k, None)
    with st.expander("➕ Add an expense", expanded=True):
        amount, mode, category, day, note = expense_form("add")
        if st.button("Save expense", type="primary") and amount > 0:
            run("INSERT INTO expenses(day,amount,mode,category,note) VALUES(?,?,?,?,?)",
                (day.isoformat(), amount, mode, category, note))
            st.session_state["reset_add"] = True
            st.toast("Expense saved ✅")
            st.rerun()

    df = table("SELECT * FROM expenses ORDER BY day DESC, id DESC")
    if df.empty:
        st.info("No expenses yet. Add your first one above.")
        return

    # --- this month's summary ---
    month = date.today().strftime("%Y-%m")
    this = df[df["day"].str.startswith(month)]
    spent = float(this["amount"].sum())
    left = budget - spent
    m1, m2 = st.columns(2)
    m1.metric("Total spent this month", f"₹{spent:,.0f}")
    m2.metric("Remaining budget", f"₹{left:,.0f}",
              delta=(f"₹{-left:,.0f} over budget" if left < 0 else f"of ₹{budget:,.0f}"),
              delta_color=("inverse" if left < 0 else "off"))
    if budget > 0:
        st.progress(min(spent / budget, 1.0), text=f"{spent / budget * 100:.0f}% of your budget used")
        if left < 0:
            st.error(f"⚠️ You're over budget by ₹{-left:,.0f} this month!")
        elif spent >= 0.8 * budget:
            st.warning(f"⚠️ Careful! Only ₹{left:,.0f} left, over 80% of your budget is gone.")
    upi = float(this[this["mode"] == "UPI"]["amount"].sum())
    st.caption(f"📱 UPI: ₹{upi:,.0f}  ·  💵 Cash: ₹{spent - upi:,.0f}")

    # --- charts ---
    if this.empty:
        st.info("No spending recorded this month yet.")
    else:
        by_cat = this.groupby("category")["amount"].sum().sort_values(ascending=False)
        t1, t2, t3 = st.tabs(["📊 By category", "🍩 Share", "📅 Daily"])
        with t1:
            bar_chart(by_cat)
        with t2:
            try:
                import altair as alt
                d = by_cat.reset_index()
                d.columns = ["category", "amount"]
                show_chart(alt.Chart(d).mark_arc(innerRadius=55).encode(
                    theta="amount:Q", color=alt.Color("category:N", scale=alt.Scale(range=PALETTE)),
                    tooltip=["category", "amount"]))
            except Exception:
                bar_chart(by_cat)
            for cat, amt in by_cat.items():
                st.write(f"**{cat}**: ₹{amt:,.0f} ({amt / spent * 100:.0f}%)")
        with t3:
            bar_chart(this.groupby("day")["amount"].sum())
        st.info(f"💡 Your biggest spending area this month is **{by_cat.index[0]}** (₹{by_cat.iloc[0]:,.0f}).")

    # --- history with edit and delete ---
    st.markdown("### 🧾 Expense history")
    months = ["All time"] + sorted({d[:7] for d in df["day"]}, reverse=True)
    pick = st.selectbox("Show", months, index=months.index(month) if month in months else 0)
    view = df if pick == "All time" else df[df["day"].str.startswith(pick)]
    st.caption(f"{len(view)} expense(s) · total ₹{view['amount'].sum():,.0f}")

    eid = st.session_state.get("edit_id")
    if eid is not None:
        row = df[df["id"] == eid]
        if row.empty:
            st.session_state.pop("edit_id", None)
        else:
            r = row.iloc[0]
            with st.container(border=True):
                st.markdown("**✏️ Edit expense**")
                a, m, c, d, n = expense_form(f"ef{eid}", r["amount"], r["mode"], r["category"],
                                             date.fromisoformat(r["day"]), r["note"])
                s1, s2 = st.columns(2)
                if s1.button("💾 Save changes", type="primary", key="save_edit"):
                    run("UPDATE expenses SET day=?, amount=?, mode=?, category=?, note=? WHERE id=?",
                        (d.isoformat(), a, m, c, n, int(eid)))
                    st.session_state.pop("edit_id", None)
                    st.toast("Expense updated ✅")
                    st.rerun()
                if s2.button("Cancel", key="cancel_edit"):
                    st.session_state.pop("edit_id", None)
                    st.rerun()

    for _, r in view.head(50).iterrows():
        rid = int(r["id"])
        c1, c2, c3 = st.columns([6, 1, 1])
        note_txt = f" · {r['note']}" if r["note"] else ""
        c1.markdown(f"**₹{r['amount']:,.0f}** · {r['category']} · {r['mode']}  \n{r['day']}{note_txt}")
        if c2.button("✏️", key=f"edit_{rid}"):
            st.session_state["edit_id"] = rid
            st.session_state.pop("del_id", None)
            st.rerun()
        if c3.button("🗑️", key=f"del_{rid}"):
            st.session_state["del_id"] = rid
            st.session_state.pop("edit_id", None)
            st.rerun()
        if st.session_state.get("del_id") == rid:
            st.warning(f"Delete this ₹{r['amount']:,.0f} {r['category']} expense? This can't be undone.")
            y, n = st.columns(2)
            if y.button("Yes, delete", key=f"yes_{rid}", type="primary"):
                run("DELETE FROM expenses WHERE id=?", (rid,))
                st.session_state.pop("del_id", None)
                st.toast("Expense deleted 🗑️")
                st.rerun()
            if n.button("Cancel", key=f"no_{rid}"):
                st.session_state.pop("del_id", None)
                st.rerun()


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
    if st.button("🚨 I FEEL UNSAFE", type="primary", key="sos_btn"):
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
esc = _html.escape

TEXT_RULES = [
    (r"(registration|processing|application|security|refundable|joining)\s+(fee|fees|deposit|charges?)", 3,
     "Request for payment", "You're asked to pay a fee. Real scholarships, jobs and hackathons don't charge you to be selected."),
    (r"\b(otp|cvv|pin|password|aadhaar|aadhar)\b", 3,
     "Request for personal information", "This message asks for an OTP, PIN, password or Aadhaar. Legitimate sources never ask for these."),
    (r"(urgent|last chance|hurry|act now|expires (today|soon)|limited seats|within \d+ (hours|minutes))", 1,
     "Urgency", "The message creates pressure to act fast, so you don't have time to think or check."),
    (r"(guaranteed|100% ?(selection|placement|job|success))", 2,
     "Unrealistic promises", "Guaranteed selection or results is a classic scam sign. Nobody can promise that."),
    (r"earn\s*(rs\.?|₹|inr)?\s*\d", 2,
     "Too-good-to-be-true earnings", "It promises easy money. Real work doesn't pay big for little effort."),
    (r"(bank|upi|account)\s*(details|number|id)", 2,
     "Request for bank details", "It asks for your bank or UPI details, which scammers use to take your money."),
    (r"(congratulations|you (have been|are|were) (selected|shortlisted|chosen)|you (won|have won))", 2,
     "Surprise selection", "It says you're selected or won something you never applied for."),
    (r"(gift card|lottery|prize|lucky draw)", 2,
     "Prizes and gifts", "Prizes, gift cards and lotteries are common bait in scam messages."),
    (r"(whatsapp|telegram)\s*(group|us|number|me)", 1,
     "Moving the chat elsewhere", "It pushes you to continue on WhatsApp or Telegram, away from official channels."),
    (r"(work from home|part[- ]time).{0,40}(earn|income|salary)", 2,
     "Easy work-from-home offer", "Easy work-from-home income offers are a very common scam."),
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
    """Returns (score, reasons, good_signs, urls). Each reason has a title, description and points."""
    found, good, score = {}, [], 0
    urls = URL_RE.findall(text)
    low = text.lower()

    def add(title, pts, desc):
        nonlocal score
        score += pts
        if title in found:
            found[title]["desc"] += " " + desc
            found[title]["pts"] += pts
        else:
            found[title] = {"title": title, "desc": desc, "pts": pts}

    for pattern, pts, title, desc in TEXT_RULES:
        if re.search(pattern, low):
            add(title, pts, desc)
    for u in urls:
        full = u if u.startswith("http") else "http://" + u
        host = (urllib.parse.urlparse(full).hostname or "").lower()
        if host.endswith(OFFICIAL_ENDINGS):
            score -= 2
            good.append(f"The link '{host}' ends with an official government or education domain.")
            continue
        if host in SHORTENERS:
            add("Hidden link destination", 2, f"'{host}' is a link shortener that hides where you'll really land.")
        if host.endswith(RISKY_TLDS):
            add("Suspicious links", 2, f"'{host}' uses an ending often seen on scam websites.")
        if full.startswith("http://"):
            add("Insecure connection", 1, f"'{host}' doesn't use secure HTTPS.")
        if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", host):
            add("Suspicious links", 3, "The link is a raw IP address, not a real website name.")
        if host.count("-") >= 2:
            add("Lookalike website", 1, f"'{host}' has many hyphens, common in fake copies of real sites.")
        if any(w in host for w in BAIT_WORDS):
            add("Suspicious website name", 2,
                f"'{host}' is stuffed with bait words (scholarship, job, offer...) but isn't an official domain.")
    reasons = sorted(found.values(), key=lambda r: -r["pts"])
    return max(score, 0), reasons, good, urls


LEVELS = {
    "high": dict(label="HIGH RISK", headline="This is probably a scam.", color="#EF4444", box="#FECACA",
                 note="This message shows signs of a scam, but sometimes real messages have similar signs. "
                      "Still unsure? Check the official website or call 1930."),
    "medium": dict(label="MEDIUM RISK", headline="This looks suspicious.", color="#F59E0B", box="#FDE68A",
                   note="This message has some warning signs. Check it carefully before you click or reply. "
                        "Still unsure? Ask a teacher or call 1930."),
    "low": dict(label="LOW RISK", headline="No obvious warning signs.", color="#22C55E", box="#BBF7D0",
                note="We didn't find common scam signs, but no checker is perfect. Stay careful with links and payments."),
}
NEXT_STEPS = {
    "high": ["Don't click any link, reply, or pay anything.",
             "Never share your OTP, PIN, password or Aadhaar number.",
             "Check the opportunity yourself on the official website. Type the address, don't use the link.",
             "Show the message to a parent, teacher or your placement cell.",
             "Report it at cybercrime.gov.in or call 1930, then block the sender."],
    "medium": ["Don't click the link or pay anything yet.",
               "Search for the organisation's official website and compare the details.",
               "Ask your teacher or placement cell if it's genuine.",
               "Remember: real opportunities never ask you to pay to be selected.",
               "If you're still unsure, treat it as a scam."],
    "low": ["Still check the sender and the link before you apply.",
            "Never pay a fee or share an OTP/PIN to get an opportunity.",
            "For scholarships, use official sites like scholarships.gov.in.",
            "If anything feels off later, come back and check again."],
}
FLAG_SVG = ('<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#F472B6" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round"><path d="M5 21V4"/><path d="M5 4h12l-2.5 4 2.5 4H5"/></svg>')


def risk_level(score):
    return "high" if score >= 5 else ("medium" if score >= 2 else "low")


def icon_svg(level, color):
    shape = ('<circle cx="32" cy="32" r="24"/><path d="M21 33 l8 8 14-16"/>' if level == "low"
             else '<path d="M32 8 L58 54 H6 Z"/><path d="M32 26 V38"/><circle cx="32" cy="46" r="1.5" fill="' + color + '"/>')
    return ('<svg width="60" height="60" viewBox="0 0 64 64" fill="none" stroke="' + color +
            '" stroke-width="4" stroke-linejoin="round" stroke-linecap="round">' + shape + '</svg>')


def reasons_html(items):
    return "".join(
        '<div class="sc-reason"><div class="sc-flag">' + FLAG_SVG + '</div><div><div class="sc-rt">' +
        esc(r["title"]) + '</div><div class="sc-rd">' + esc(r["desc"]) + '</div></div></div>' for r in items)


def panel_html(level, reasons):
    lv = LEVELS[level]
    body = ""
    if reasons:
        body = '<div class="sc-sub">Here are the key reasons why:</div>' + reasons_html(reasons[:3])
    else:
        body = '<div class="sc-sub">We did not spot any common scam signs in this message.</div>'
    return ('<div class="sc-panel" style="--c:' + lv["color"] + '"><div class="sc-badge">' + lv["label"] + '</div>' +
            icon_svg(level, lv["color"]) + '<div class="sc-head">' + lv["headline"] + '</div>' +
            '<div class="sc-box" style="background:' + lv["box"] + '">' + esc(lv["note"]) + '</div>' + body + '</div>')


def steps_html(level):
    items = "".join("<li>" + esc(s) + "</li>" for s in NEXT_STEPS[level])
    return '<div class="sc-steps"><div class="sc-st">✅ What to do next</div><ol>' + items + '</ol></div>'


def render_scam(res):
    level = risk_level(res["score"])
    st.markdown(panel_html(level, res["reasons"]), unsafe_allow_html=True)
    n = len(res["reasons"])
    if n > 3:
        with st.expander(f"Show all {n} reasons"):
            st.markdown('<div class="sc-panel">' + reasons_html(res["reasons"]) + '</div>', unsafe_allow_html=True)
    for g in res["good"]:
        st.success("✅ " + g)
    if res["urls"]:
        st.caption("Links found: " + ", ".join(res["urls"]))
    st.markdown(steps_html(level), unsafe_allow_html=True)
    if res["ai"]:
        st.info("🤖 AI second opinion: " + res["ai"])
    elif res["ai_err"]:
        st.caption(f"(AI second opinion unavailable: {res['ai_err']})")


def scam_tab():
    st.subheader("🛡️ Scam Link Shield")
    st.caption("Paste a message or link about scholarships, hackathons, placements or job offers.")
    text = st.text_area("Paste here", height=130, key="scam_text",
                        placeholder="Congratulations! You are selected for a scholarship. Pay ₹499 registration fee at http://nsp-scholar-claim.xyz")
    if st.button("Check it", type="primary") and text.strip():
        score, reasons, good, urls = analyze(text)
        ai, ai_err = None, ""
        if ai_available():
            with st.spinner("AI is taking a second look..."):
                ai = ask_ai("A student received this message. In 3 short, simple sentences say whether it looks "
                            f"like a scam, why, and what they should do:\n\n{text}")
            ai_err = "" if ai else AI_STATUS["error"]
        st.session_state["scam"] = dict(score=score, reasons=reasons, good=good, urls=urls, ai=ai, ai_err=ai_err)
    if st.session_state.get("scam"):
        render_scam(st.session_state["scam"])
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
    bar_chart(avg, ymax=100)
    if df["exam"].nunique() > 1:
        st.markdown("**Trend over time**")
        line_chart(df)

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
        for task, kind, d, tm in [("Bring chemistry record", "Bring item", 1, "08:30"), ("Maths unit test", "Test / Exam", 3, "10:00"),
                                  ("Physics assignment submission", "Assignment", 2, "17:00"), ("Science project model", "Project", 6, "")]:
            run("INSERT INTO reminders(task,kind,due,due_time) VALUES(?,?,?,?)", (task, kind, (today + timedelta(days=d)).isoformat(), tm))
        yday, two = (today - timedelta(days=1)).isoformat(), (today - timedelta(days=2)).isoformat()
        run("INSERT INTO reminders(task,kind,due,due_time,done,done_at) VALUES(?,?,?,?,1,?)",
            ("English homework", "Homework", yday, "18:00", f"{yday} 16:30"))
        run("INSERT INTO reminders(task,kind,due,due_time,done,done_at) VALUES(?,?,?,?,1,?)",
            ("Bring geometry box", "Bring item", two, "08:00", f"{yday} 09:15"))
        run("INSERT INTO reminders(task,kind,due,due_time,done,done_at) VALUES(?,?,?,?,1,?)",
            ("Chemistry worksheet", "Homework", two, "", f"{two} 20:10"))
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
if "dark_mode" not in st.session_state:  # remembered in the link, so a refresh keeps your choice
    st.session_state["dark_mode"] = st.query_params.get("mode", "dark") != "light"
st.markdown(build_css(is_dark()), unsafe_allow_html=True)
header()
_space, _switch = st.columns([2, 1])
_switch.toggle("🌙 Dark mode", key="dark_mode")
st.query_params["mode"] = "dark" if st.session_state["dark_mode"] else "light"
tabs = st.tabs(["📝 Reminders", "💸 Expenses", "🆘 SOS", "🛡️ Scam Shield", "📈 Progress", "⚙️ Setup"])
for tab, fn in zip(tabs, [reminders_tab, expenses_tab, sos_tab, scam_tab, progress_tab, setup_tab]):
    with tab:
        fn()
