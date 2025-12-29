# Troubleshooting Guide

## HTTP 401 Error - Invalid Credentials

### Symptom
```
ERROR:asr_proxy:🎤 [ASR Proxy] ❌ Connection Error: server rejected WebSocket connection: HTTP 401
```

### Cause
The credentials (AppID, Token, Secret) in your database are either:
- Expired
- Incorrect
- From the wrong application

### Solution

#### Step 1: Get Correct Credentials from VolcEngine Console

1. Visit: https://console.volcengine.com/speech/app
2. Log in to your VolcEngine account
3. Select your application
4. Copy the following values:
   - **AppID** (应用ID)
   - **Access Token** (访问令牌)
   - **Secret Key** (密钥)

**Important**: Make sure you're copying from the **correct application** in the console.

#### Step 2: Update Credentials in Database

**Option A: Use the Update Script (Recommended)**
```bash
python3 update_credentials.py
```

Follow the prompts and paste your credentials when asked.

**Option B: Manual Update via SQL**
```bash
sqlite3 scriptbuddy.db
```

Then run:
```sql
-- Update ASR credentials
UPDATE script_configs SET value='YOUR_APPID' WHERE category='asr' AND key_name='appId';
UPDATE script_configs SET value='YOUR_ACCESS_TOKEN' WHERE category='asr' AND key_name='token';
UPDATE script_configs SET value='YOUR_SECRET_KEY' WHERE category='asr' AND key_name='secret';

-- Update TTS credentials (use same values if same app)
UPDATE script_configs SET value='YOUR_APPID' WHERE category='tts' AND key_name='appId';
UPDATE script_configs SET value='YOUR_ACCESS_TOKEN' WHERE category='tts' AND key_name='token';
UPDATE script_configs SET value='YOUR_SECRET_KEY' WHERE category='tts' AND key_name='secret';

-- Verify
SELECT * FROM script_configs WHERE category IN ('asr', 'tts');
```

Exit with: `.quit`

**Option C: Re-initialize Database**

Edit `api/init_db.py` and update the credentials on lines 62-68, then run:
```bash
python3 api/init_db.py
```

⚠️ **Warning**: This will delete all existing data!

#### Step 3: Verify Credentials
```bash
python3 check_db.py
```

Check that your new credentials are saved correctly.

#### Step 4: Restart Server
```bash
cd api
uvicorn main:app --reload
```

#### Step 5: Test Connection

Try using the ASR feature again. You should see:
```
INFO:asr_proxy:🎤 [ASR Proxy] ✓ Connected to VolcEngine
```

---

## HTTP 403 Error - Forbidden

### Symptom
```
ERROR:asr_proxy:🎤 [ASR Proxy] ❌ Connection Error: server rejected WebSocket connection: HTTP 403
```

### Cause
The authentication format is correct, but:
- Wrong credential type used (e.g., using `token` instead of `secret` for ASR)
- Application doesn't have permission for the service
- IP restrictions or quota limits

### Solution
1. Verify you're using the correct credential mapping:
   - ASR: Uses `secret` for `X-Api-Access-Key`
   - TTS: Uses `token` for `Authorization`
2. Check your VolcEngine console for service activation and quotas
3. Verify no IP whitelist restrictions

---

## No Response from VolcEngine

### Symptom
Connection hangs or times out without error.

### Cause
- Network connectivity issues
- Firewall blocking WebSocket connections
- Wrong endpoint URL

### Solution
1. Check internet connection
2. Verify firewall allows WebSocket (WSS) connections
3. Confirm endpoint URLs:
   - ASR: `wss://openspeech.bytedance.com/api/v3/sauc/bigmodel`
   - TTS: `wss://openspeech.bytedance.com/api/v1/tts/ws_binary`

---

## Browser Extension Warnings (Can Be Ignored)

### Symptom
```
Unchecked runtime.lastError: A listener indicated an asynchronous response...
[Deprecation] The ScriptProcessorNode is deprecated...
```

### Cause
These are browser extension warnings, NOT errors from your application.

### Solution
✅ **Safe to ignore**. These don't affect functionality.

To reduce clutter:
- Test in incognito/private mode
- Disable browser extensions temporarily
- Use browser console filtering

---

## Database Connection Issues

### Symptom
```
Error connecting to database: unable to open database file
```

### Cause
Database file doesn't exist or has permission issues.

### Solution
```bash
# Initialize database
python3 api/init_db.py

# Verify it was created
ls -la scriptbuddy.db

# Check permissions
chmod 644 scriptbuddy.db
```

---

## Quick Diagnostic Commands

```bash
# Check database contents
python3 check_db.py

# Update credentials
python3 update_credentials.py

# Test ASR authentication
curl -i -N \
  -H "X-Api-Resource-Id: volc.bigasr.sauc.duration" \
  -H "X-Api-Request-Id: test-123" \
  -H "X-Api-Access-Key: YOUR_SECRET_KEY" \
  -H "X-Api-App-Key: YOUR_APPID" \
  wss://openspeech.bytedance.com/api/v3/sauc/bigmodel

# Check server logs
cd api
uvicorn main:app --reload --log-level debug
```

---

## Still Having Issues?

1. **Check VolcEngine Service Status**: https://console.volcengine.com/speech
2. **Verify Account Quota**: Make sure you haven't exceeded usage limits
3. **Review Logs**: Check both frontend console and backend terminal for errors
4. **Test with Sample Code**: Try the official sample code to verify credentials work
