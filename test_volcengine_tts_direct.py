#!/usr/bin/env python3
"""
Direct test of VolcEngine TTS API
This bypasses the proxy and tests directly with VolcEngine
"""

import asyncio
import websockets
import json

# Your credentials
TTS_APPID = "5349866810"
TTS_TOKEN = "j_DA2hGKCvrytiS1fM-1jN5Cqz6Mxpx3"
TTS_SECRET = "1oJHD2KkFJTMbLgPIx4fAR9XS7qGZNM7"
TTS_CLUSTER = "volc_tts_streaming"

async def test_tts_connection(use_secret=False):
    """Test connection to VolcEngine TTS"""

    token = TTS_SECRET if use_secret else TTS_TOKEN
    token_type = "SECRET" if use_secret else "TOKEN"

    print(f"\n{'='*60}")
    print(f"Testing TTS with {token_type}")
    print(f"{'='*60}")
    print(f"AppID: {TTS_APPID}")
    print(f"Token ({token_type}): {token}")
    print(f"Cluster: {TTS_CLUSTER}")

    # Build headers
    headers = {
        "Authorization": f"Bearer;{token}",
    }

    print(f"\nHeaders:")
    for k, v in headers.items():
        print(f"  {k}: {v}")

    # TTS endpoint
    endpoint = "wss://openspeech.bytedance.com/api/v1/tts/ws_binary"

    print(f"\n→ Testing endpoint: {endpoint}")
    try:
        async with websockets.connect(
            endpoint,
            extra_headers=headers,
            timeout=5
        ) as ws:
            print(f"  ✅ SUCCESS! Connected to TTS endpoint")
            print(f"  ✅ Authentication successful!")
            print(f"  Response headers: {ws.response_headers}")
            print(f"\n  ℹ️  Note: This endpoint requires binary protocol for actual TTS")
            print(f"     Your tts_proxy.py handles this correctly.")
            return True

    except websockets.exceptions.InvalidStatusCode as e:
        print(f"  ❌ FAILED: {e}")
        if e.status_code == 401:
            print(f"     → Authentication failed - token may be invalid or expired")
        elif e.status_code == 403:
            print(f"     → Access forbidden - service may not be activated")
        return False
    except Exception as e:
        print(f"  ❌ ERROR: {type(e).__name__}: {e}")
        return False

async def main():
    print("="*60)
    print("VolcEngine TTS Connection Test")
    print("="*60)

    # Test with TOKEN
    success1 = await test_tts_connection(use_secret=False)

    # Test with SECRET
    success2 = await test_tts_connection(use_secret=True)

    print("\n" + "="*60)
    print("RESULTS:")
    print("="*60)
    if success1:
        print("✅ Works with TOKEN")
    if success2:
        print("✅ Works with SECRET")
    if not success1 and not success2:
        print("❌ Failed with both credentials")
        print("\nPossible issues:")
        print("1. TTS service not activated in VolcEngine console")
        print("2. Credentials expired or incorrect")
        print("3. Account doesn't have permission for TTS service")
        print("4. Cluster ID incorrect")
        print("5. Quota exceeded")
        print("\nPlease check:")
        print("→ https://console.volcengine.com/speech/service")
        print("→ https://console.volcengine.com/speech/app")

if __name__ == "__main__":
    asyncio.run(main())
