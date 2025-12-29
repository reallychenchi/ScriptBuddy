#!/usr/bin/env python3
"""
Direct test of VolcEngine ASR API
This bypasses the proxy and tests directly with VolcEngine
"""

import asyncio
import websockets
import uuid
import json

# Your credentials
V2L_APPID = "5349866810"
V2L_ACCESS_TOKEN = "j_DA2hGKCvrytiS1fM-1jN5Cqz6Mxpx3"
V2L_SECRET_KEY = "1oJHD2KkFJTMbLgPIx4fAR9XS7qGZNM7"

async def test_connection(use_secret=False):
    """Test connection to VolcEngine ASR"""

    access_key = V2L_SECRET_KEY if use_secret else V2L_ACCESS_TOKEN
    key_type = "SECRET_KEY" if use_secret else "ACCESS_TOKEN"

    print(f"\n{'='*60}")
    print(f"Testing with {key_type}")
    print(f"{'='*60}")
    print(f"AppID: {V2L_APPID}")
    print(f"Access Key ({key_type}): {access_key}")

    # Build headers
    reqid = str(uuid.uuid4())
    headers = {
        "X-Api-Resource-Id": "volc.bigasr.sauc.duration",
        "X-Api-Request-Id": reqid,
        "X-Api-Access-Key": access_key,
        "X-Api-App-Key": V2L_APPID
    }

    print(f"\nHeaders:")
    for k, v in headers.items():
        print(f"  {k}: {v}")

    # Try different endpoints
    endpoints = [
        "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_nostream",
        "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel",
        "wss://openspeech.bytedance.com/api/v2/asr",
    ]

    for endpoint in endpoints:
        print(f"\n→ Testing endpoint: {endpoint}")
        try:
            async with websockets.connect(
                endpoint,
                extra_headers=headers,
                timeout=5
            ) as ws:
                print(f"  ✅ SUCCESS! Connected to {endpoint}")
                print(f"  Response headers: {ws.response_headers}")
                return True
        except websockets.exceptions.InvalidStatusCode as e:
            print(f"  ❌ FAILED: {e}")
        except Exception as e:
            print(f"  ❌ ERROR: {type(e).__name__}: {e}")

    return False

async def main():
    print("="*60)
    print("VolcEngine ASR Connection Test")
    print("="*60)

    # Test with ACCESS_TOKEN
    success1 = await test_connection(use_secret=False)

    # Test with SECRET_KEY
    success2 = await test_connection(use_secret=True)

    print("\n" + "="*60)
    print("RESULTS:")
    print("="*60)
    if success1:
        print("✅ Works with ACCESS_TOKEN")
    if success2:
        print("✅ Works with SECRET_KEY")
    if not success1 and not success2:
        print("❌ Failed with both credentials")
        print("\nPossible issues:")
        print("1. Service not activated in VolcEngine console")
        print("2. Credentials expired or incorrect")
        print("3. Account doesn't have permission for ASR service")
        print("4. IP restrictions or regional limitations")
        print("5. Quota exceeded")
        print("\nPlease check:")
        print("→ https://console.volcengine.com/speech/service")
        print("→ https://console.volcengine.com/speech/app")

if __name__ == "__main__":
    asyncio.run(main())
