# Pursuit setup guide

## Step 1: Telegram API Credentials

1. Go to https://my.telegram.org
2. Login with your phone number
3. Click "API Development Tools"
4. Create a new app (any name)
5. Copy `api_id` and `api_hash` into `.env`:
   ```
   TELEGRAM_API_ID=your_api_id
   TELEGRAM_API_HASH=your_api_hash
   ```

## Step 2: Generate Telegram Session String

```bash
cd pursuit
cp .env.example .env
# Fill in TELEGRAM_API_ID and TELEGRAM_API_HASH first, then:
python3 generate_session.py
```

Enter your phone number and OTP. Copy the printed session string into `.env`:
```
TELEGRAM_SESSION_STRING=1BVtsOKABu...long_string...
TELEGRAM_SELF_ID=123456789   # printed at the end
```

## Step 3: Get Telegram Group ID

```bash
python3 get_group_id.py
```

Find "SDE Jobs & Internships" (or whatever the group name is) in the output. Copy its ID:
```
TELEGRAM_GROUP_ID=-1001234567890
```

## Step 4: Gemini API Key (Free)

1. Go to https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copy into `.env`:
   ```
   GEMINI_API_KEY=AIzaSy...
   ```

## Step 5: Gmail App Password

1. Go to Gmail → Settings (gear icon) → See all settings
2. Security tab → Enable 2-Step Verification (if not already)
3. Security → Search "App passwords"
4. Create → Select "Other" → Name it "pursuit"
5. Copy the 16-character password into `.env`:
   ```
   GMAIL_ADDRESS=you@gmail.com
   GMAIL_APP_PASSWORD=abcd efgh ijkl mnop
   ```

## Step 6: Google Drive Setup (for form resume uploads)

1. Go to https://console.cloud.google.com
2. Create a new project (name it "pursuit")
3. Enable "Google Drive API" (search in APIs & Services)
4. Go to IAM & Admin → Service Accounts → Create Service Account
5. Name it "pursuit", click Done
6. Click the service account → Keys tab → Add Key → JSON
7. Download the JSON file

8. Create a Google Drive folder (e.g., "Job Applications Resumes")
9. Share the folder with the service account email (shown in the JSON as `client_email`)
10. Copy the folder ID from the URL: `drive.google.com/drive/folders/THIS_IS_THE_ID`

11. Base64 encode the JSON file:
    ```bash
    base64 -i ~/Downloads/service-account.json | tr -d '\n'
    ```
    Copy that output into `.env`:
    ```
    GOOGLE_SERVICE_ACCOUNT_B64=eyJr...very_long_string...
    GOOGLE_DRIVE_FOLDER_ID=1abc2def3ghi
    ```

## Step 7: Test Locally

```bash
JAC_HEADLESS=1 python3 -m pytest tests   # all tests should pass
python3 -m src.main            # starts monitoring... send a job message in the group to test
```

## Step 8 (optional): Run the bot on Fly.io

This runs the bot only. The dashboard is meant to run on your own machine.

```bash
# Install flyctl
brew install flyctl

# Login / signup
fly auth signup   # or: fly auth login

# Add credit card (required, but won't be charged on free tier)
fly auth login --browser

fly launch --no-deploy   # detects Dockerfile, sets up app

# Set all secrets on Fly.io (replaces .env on cloud):
fly secrets set TELEGRAM_API_ID=your_value
fly secrets set TELEGRAM_API_HASH=your_value
fly secrets set TELEGRAM_SESSION_STRING=your_value
fly secrets set TELEGRAM_GROUP_ID=your_value
fly secrets set TELEGRAM_SELF_ID=your_value
fly secrets set GEMINI_API_KEY=your_value
fly secrets set GMAIL_ADDRESS=your_value
fly secrets set GMAIL_APP_PASSWORD=your_value
fly secrets set GOOGLE_SERVICE_ACCOUNT_B64=your_value
fly secrets set GOOGLE_DRIVE_FOLDER_ID=your_value

# Deploy!
fly deploy

# Check logs:
fly logs
```

## What Happens After Deploy

- Bot starts monitoring the Telegram group 24/7
- New job message comes in → Gemini parses it
- Resume auto-tailored for that JD → PDF compiled
- PDF uploaded to your Google Drive folder
- Email sent (if email apply) OR Google Form filled (if form apply)
- You get a Telegram notification on your phone:
  ```
  ✅ Applied!
  🏢 Aspire, SWE Intern
  📨 Via: form → https://people-jobs.com/...
  ```

## Logs

Local: `logs/applications.log`
Cloud: `fly logs`
