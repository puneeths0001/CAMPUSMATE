# 🎓 Campus Mate
Study smart. Spend wisely. Stay safe.

A student companion with smart reminders, an expense tracker, an SOS safety alert,
a scam-link shield and a progress report.

## Run on your computer
```
pip install -r requirements.txt
streamlit run app.py
```
Optional nightly reminders (second terminal, same folder):
```
python reminder_bot.py
```

## Keys (all optional, set in the app's ⚙️ Setup tab)
- `GEMINI_API_KEY`: free key from https://aistudio.google.com/apikey
- `TELEGRAM_BOT_TOKEN`: create a bot with @BotFather on Telegram

## Put it online (Streamlit Community Cloud)
1. Upload this folder to a GitHub repository.
2. Go to https://share.streamlit.io, sign in with GitHub, click **Create app**, pick the repo and `app.py`.
3. Under **Advanced settings → Secrets**, paste:
```
GEMINI_API_KEY = "your-key"
TELEGRAM_BOT_TOKEN = "your-token"
```
4. Deploy. You get a public link that works on any phone.

Note: on Streamlit Cloud the saved data can reset when the app restarts, so use the
"Load demo data" button in Setup before a demo.
