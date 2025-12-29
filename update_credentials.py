#!/usr/bin/env python3
"""
Update VolcEngine credentials in the database

Usage:
    python3 update_credentials.py
"""

import sqlite3
import os

DB_FILE = "scriptbuddy.db"

def update_credentials():
    print("=" * 60)
    print("VolcEngine Credentials Update Tool")
    print("=" * 60)
    print()
    print("Please provide your credentials from VolcEngine console:")
    print("https://console.volcengine.com/speech/app")
    print()

    # Get ASR credentials
    print("📌 ASR (语音识别) Credentials:")
    asr_appid = input("  AppID: ").strip()
    asr_token = input("  Access Token: ").strip()
    asr_secret = input("  Secret Key: ").strip()

    print()
    print("📌 TTS (语音合成) Credentials:")
    use_same = input("  Use same credentials as ASR? (y/n): ").strip().lower()

    if use_same == 'y':
        tts_appid = asr_appid
        tts_token = asr_token
        tts_secret = asr_secret
    else:
        tts_appid = input("  AppID: ").strip()
        tts_token = input("  Access Token: ").strip()
        tts_secret = input("  Secret Key: ").strip()

    print()
    print("📌 LLM (DeepSeek) Credentials:")
    llm_key = input("  API Key (press Enter to keep current): ").strip()

    # Update database
    print()
    print("Updating database...")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Update ASR
    cursor.execute("UPDATE script_configs SET value=? WHERE category='asr' AND key_name='appId'", (asr_appid,))
    cursor.execute("UPDATE script_configs SET value=? WHERE category='asr' AND key_name='token'", (asr_token,))
    cursor.execute("UPDATE script_configs SET value=? WHERE category='asr' AND key_name='secret'", (asr_secret,))

    # Update TTS
    cursor.execute("UPDATE script_configs SET value=? WHERE category='tts' AND key_name='appId'", (tts_appid,))
    cursor.execute("UPDATE script_configs SET value=? WHERE category='tts' AND key_name='token'", (tts_token,))
    cursor.execute("UPDATE script_configs SET value=? WHERE category='tts' AND key_name='secret'", (tts_secret,))

    # Update LLM if provided
    if llm_key:
        cursor.execute("UPDATE script_configs SET value=? WHERE category='llm' AND key_name='apiKey'", (llm_key,))

    conn.commit()
    conn.close()

    print()
    print("✅ Credentials updated successfully!")
    print()
    print("Updated values:")
    print(f"  ASR AppID: {asr_appid}")
    print(f"  ASR Token: {asr_token[:10]}...")
    print(f"  ASR Secret: {asr_secret[:10]}...")
    print(f"  TTS AppID: {tts_appid}")
    print(f"  TTS Token: {tts_token[:10]}...")
    print(f"  TTS Secret: {tts_secret[:10]}...")
    if llm_key:
        print(f"  LLM Key: {llm_key[:10]}...")

    print()
    print("🔄 Please restart your FastAPI server for changes to take effect:")
    print("   cd api && uvicorn main:app --reload")

if __name__ == "__main__":
    if not os.path.exists(DB_FILE):
        print(f"❌ Error: Database file '{DB_FILE}' not found!")
        print("   Please run 'python3 api/init_db.py' first.")
        exit(1)

    update_credentials()
