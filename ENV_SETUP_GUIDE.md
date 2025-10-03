# Newsauto Environment Configuration Guide

## Quick Setup Checklist

### 1. Email Configuration (Required for sending newsletters)

Choose ONE of these options:

#### Option A: Local Testing (Current Setting)
- Already configured to use MailHog on port 1025
- Run MailHog with: `docker run -p 1025:1025 -p 8025:8025 mailhog/mailhog`
- View emails at: http://localhost:8025

#### Option B: Gmail SMTP
1. Go to https://myaccount.google.com/apppasswords
2. Generate an app-specific password (16 characters)
3. Update .env:
   ```
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx  # App password, not regular password!
   SMTP_FROM=Newsletter Name <your-email@gmail.com>
   SMTP_TLS=True
   ```

#### Option C: Resend.com (Modern API)
1. Sign up at https://resend.com
2. Get API key from https://resend.com/api-keys
3. Update .env:
   ```
   RESEND_API_KEY=re_xxxxxxxxxxxxx
   ```

### 2. Reddit API (Optional - for Reddit content sources)

1. Go to https://www.reddit.com/prefs/apps
2. Click "Create App" or "Create Another App"
3. Choose "script" type
4. Note the client ID (under "personal use script")
5. Note the secret
6. Update .env:
   ```
   REDDIT_CLIENT_ID=your_client_id_here
   REDDIT_CLIENT_SECRET=your_secret_here
   REDDIT_USER_AGENT=Newsauto/1.0 by YourRedditUsername
   ```

### 3. Database Configuration

#### Development (Current):
- SQLite is already configured
- Database file: `./data/newsletter.db`

#### Production:
```
DATABASE_URL=postgresql://username:password@localhost:5432/newsauto
```

### 4. Ollama Models

Verify your installed models match the configuration:
```bash
ollama list
```

Current configuration expects:
- `mistral:7b-instruct` (primary)
- `deepseek-r1:1.5b` (analytical)
- `phi3:mini` (classification)

Pull missing models:
```bash
ollama pull mistral:7b-instruct
ollama pull deepseek-r1:1.5b
ollama pull phi3:mini
```

### 5. Timezone Configuration

Update `TIMEZONE` in .env to your local timezone:
- US Eastern: `America/New_York`
- US Pacific: `America/Los_Angeles`
- UK: `Europe/London`
- Japan: `Asia/Tokyo`
- [Full list](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)

### 6. Security Note

✅ Your SECRET_KEY is already generated and secure
⚠️ Never commit .env to version control
⚠️ Keep app-specific passwords and API keys secure

## Testing Your Configuration

### Test Email:
```bash
python -m newsauto.cli test-email --to your-email@example.com
```

### Test Ollama:
```bash
curl http://localhost:11434/api/tags
```

### Test Reddit (if configured):
```bash
python -m newsauto.cli test-reddit
```

## Common Issues

### Email not sending?
- Check firewall/antivirus blocking SMTP ports
- For Gmail: Ensure 2FA is enabled and using app password
- For MailHog: Ensure Docker container is running

### Ollama connection failed?
- Start Ollama: `ollama serve`
- Check port 11434 is not blocked

### Reddit API errors?
- Verify client ID and secret are correct
- Check Reddit app type is "script"
- Ensure user agent includes your username

## Environment Variables Reference

See `.env.example` for all available options with descriptions.