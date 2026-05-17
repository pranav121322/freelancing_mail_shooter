# 🚀 AI Freelancing Mail Shooter

A production-ready Python backend that turns a Telegram message into a personalized job application email — powered by Google Gemini, sent via Brevo, and logged to Google Sheets.

---

## How It Works

```
You (Telegram) ──→ Webhook ──→ FastAPI ──→ Gemini (AI)
                                    │
                                    ├──→ Brevo (send email)
                                    ├──→ Google Sheets (log)
                                    └──→ Telegram reply ✅
```

**Message format:**
```
Email: hr@company.com
JD: Looking for a Python Backend Developer with FastAPI, AWS, PostgreSQL and 5+ years experience.
```

---

## Project Structure

```
mail-shooter/
├── app/
│   ├── main.py          # FastAPI app, routes, lifespan
│   ├── config.py        # Pydantic settings (env vars only)
│   ├── telegram_bot.py  # Bot logic, webhook setup, update processing
│   ├── ai_service.py    # Gemini API integration
│   ├── email_service.py # Brevo email sending with retries
│   ├── sheets_service.py# Google Sheets logging + duplicate check
│   ├── utils.py         # Parsing, validation, logging setup
│   └── prompt.py        # Gemini prompt templates
├── requirements.txt
├── railway.json
├── Procfile
├── runtime.txt
├── .gitignore
├── .env.example
└── README.md
```

---

## Local Setup

### 1. Clone and create virtual environment

```bash
git clone https://github.com/yourname/mail-shooter.git
cd mail-shooter
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env and fill in all values
```

### 3. Set up Google Sheets credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable **Google Sheets API** and **Google Drive API**
3. Create a **Service Account** → download JSON key
4. Share your Google Sheet with the service account email (Editor access)
5. Minify the JSON to one line and paste into `GOOGLE_CREDS_JSON` in your `.env`

```bash
# Minify helper:
python3 -c "import json,sys; print(json.dumps(json.load(open('credentials.json'))))"
```

### 4. Run locally with ngrok

```bash
# Terminal 1: Start the server
uvicorn app.main:app --reload --port 8000

# Terminal 2: Expose via ngrok
ngrok http 8000
```

Set `BASE_URL=https://xxxx.ngrok.io` in your `.env`, then restart the server — webhook registers automatically on startup.

---

## Railway Deployment

### 1. Install Railway CLI

```bash
npm install -g @railway/cli
railway login
```

### 2. Create project and deploy

```bash
railway init
railway up
```

### 3. Set environment variables

In Railway Dashboard → your project → **Variables**, add all variables from `.env.example`.

> **Tip:** For `GOOGLE_CREDS_JSON`, paste the minified single-line JSON directly. Railway handles it safely.

### 4. Get your public URL

Dashboard → Settings → Domains → **Generate Domain**

Set `BASE_URL=https://your-app.up.railway.app` in Railway variables.

### 5. Redeploy to register webhook

```bash
railway up
```

The app registers the webhook automatically on startup. Confirm via:
```
https://your-app.up.railway.app/health
```

---

## Webhook Management

| Endpoint | Description |
|---|---|
| `GET /health` | App health + config summary |
| `POST /webhook` | Telegram webhook receiver |
| `GET /set-webhook` | Manually (re)register webhook |
| `GET /delete-webhook` | Remove webhook (for polling mode) |

### Manual webhook registration (curl)

```bash
# Register
curl https://your-app.up.railway.app/set-webhook

# Verify with Telegram
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"

# Delete
curl https://your-app.up.railway.app/delete-webhook
```

---

## Telegram Bot Setup

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. `/newbot` → follow prompts → copy token
3. Set `TELEGRAM_BOT_TOKEN` in your environment
4. Send your bot a message in the format above

---

## Brevo Setup

1. Sign up at [brevo.com](https://brevo.com)
2. Go to **SMTP & API** → **API Keys** → Generate key
3. Set `BREVO_API_KEY`, `EMAIL_SENDER`, `EMAIL_SENDER_NAME`
4. Verify your sender email address in Brevo dashboard

---

## Gemini Setup

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create API key
3. Set `GEMINI_API_KEY`

---

## Example .env

See `.env.example` for all required variables with descriptions.

---

## Features

- ✅ Webhook-based Telegram bot (no polling)
- ✅ Gemini-powered personalized email generation
- ✅ HTML email via Brevo with retry logic (3 attempts)
- ✅ Google Sheets logging (Timestamp, Email, Subject, Status, JD)
- ✅ Duplicate email prevention
- ✅ Rate limiting delay between requests
- ✅ Structured logging
- ✅ FastAPI health endpoint
- ✅ Auto webhook registration on startup
- ✅ Graceful error handling at every step
- ✅ Pydantic settings validation (fails fast on missing env vars)

---

## License

MIT
