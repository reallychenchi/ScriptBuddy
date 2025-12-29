# VolcEngine Authentication Configuration

## Configuration Keys Mapping

### ASR (语音识别) - V2L API

Database config → API usage:

| Database Key | Value | Used As | API Header |
|--------------|-------|---------|------------|
| `appId` | 5349866810 | app_key | `X-Api-App-Key` |
| `token` | j_DA2hGKCvrytiS1fM-1jN5Cqz6Mxpx3 | access_token | `X-Api-Access-Key` ✅ |
| `secret` | 1oJHD2KkFJTMbLgPIx4fAR9XS7qGZNM7 | (also works) | (alternative) |
| `cluster` | volc_auction_streaming_2.0 | cluster | (metadata) |

**API Endpoint**: `wss://openspeech.bytedance.com/api/v2/asr`

⚠️ **Note**: V3 API (`/api/v3/sauc/bigmodel*`) requires a higher tier account. We use V2 which works with standard accounts.

**Headers**:
```python
{
    "X-Api-Resource-Id": "volc.bigasr.sauc.duration",
    "X-Api-Request-Id": "<uuid>",
    "X-Api-Access-Key": "<token>",       # V2L_ACCESS_TOKEN
    "X-Api-App-Key": "<appId>"           # V2L_APPID
}
```

---

### TTS (语音合成) - L2V API

Database config → API usage:

| Database Key | Value | Used As | API Header |
|--------------|-------|---------|------------|
| `appId` | 5349866810 | appid | (in payload) |
| `token` | j_DA2hGKCvrytiS1fM-1jN5Cqz6Mxpx3 | access_token | `Authorization: Bearer;{token}` |
| `secret` | 1oJHD2KkFJTMbLgPIx4fAR9XS7qGZNM7 | (not used) | - |
| `cluster` | volc_tts_streaming | cluster | (in payload) |

**API Endpoint**: `wss://openspeech.bytedance.com/api/v1/tts/ws_binary`

**Headers**:
```python
{
    "Authorization": "Bearer;<token>"
}
```

**Payload** (injected by proxy):
```json
{
    "app": {
        "appid": "<appId>",
        "token": "<token>",
        "cluster": "<cluster>"
    }
}
```

---

## Important Notes

### 🔴 Critical: Different APIs Use Different Credentials!

**ASR V2 API uses ACCESS TOKEN:**
- ✅ Correct: `"X-Api-Access-Key": token` (V2L_ACCESS_TOKEN)
- ℹ️ Alternative: `"X-Api-Access-Key": secret` (also works)

**TTS uses ACCESS TOKEN:**
- ✅ Correct: `"Authorization": "Bearer;" + token`

### Authentication Methods Summary
- **ASR (V2)**: Uses custom headers (`X-Api-*`) with ACCESS TOKEN
- **TTS**: Uses `Authorization: Bearer` header with ACCESS TOKEN + payload injection

### Credential Usage Table

| Credential | ASR V2 API | TTS API |
|------------|------------|---------|
| `appId` | ✅ Used (`X-Api-App-Key`) | ✅ Used (payload `appid`) |
| `token` | ✅ Used (`X-Api-Access-Key`) | ✅ Used (`Authorization` + payload `token`) |
| `secret` | ℹ️ Works (alternative) | ❌ Not used |

### API Version Notes

- **V2 API** (`/api/v2/asr`): Works with standard accounts ✅
- **V3 API** (`/api/v3/sauc/bigmodel*`): Requires higher tier account, returns 403 Forbidden for basic accounts ❌

---

## Verification

To verify authentication is working:

1. Check backend logs for successful connection:
   ```
   INFO:asr_proxy:🎤 [ASR Proxy] ✓ Connected to VolcEngine
   ```

2. If you see `HTTP 401` or `HTTP 403` errors:
   - **For ASR**: Verify you're using `secret` (NOT `token`) for `X-Api-Access-Key`
   - **For TTS**: Verify you're using `token` for `Authorization` header
   - Check that `appId` is correct
   - Verify credentials in database match VolcEngine console values

3. Common authentication errors:
   - `HTTP 401 Unauthorized`: Wrong credentials or missing headers
   - `HTTP 403 Forbidden`: Correct format but wrong credential values, or using token instead of secret for ASR

4. Update credentials in database:
   ```bash
   python3 api/init_db.py  # Re-initialize with correct values
   ```

5. Verify credentials in database:
   ```bash
   python3 check_db.py
   ```
