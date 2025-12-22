#!/usr/bin/env python3
"""Check Gemini API quota and usage."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_radio.config import config

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("ERROR: google-genai package not installed")
    sys.exit(1)

if not config.gemini_api_key:
    print("ERROR: RADIO_GEMINI_API_KEY not configured")
    sys.exit(1)

print("Checking Gemini API quota...")
print(f"API Key: {config.gemini_api_key[:10]}...")
print(f"Model: {config.gemini_tts_model}")
print()

client = genai.Client(api_key=config.gemini_api_key)

# Try a simple request to see the quota headers
try:
    response = client.models.generate_content(
        model=config.gemini_tts_model,
        contents="Test",
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=config.gemini_tts_voice
                    )
                )
            )
        )
    )
    print("✅ Gemini TTS API is accessible")
    print(f"Response candidates: {len(response.candidates)}")

except Exception as e:
    error_str = str(e)
    print(f"❌ Gemini TTS API error: {e}")

    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
        print("\n📊 QUOTA EXHAUSTED")
        print("Your Gemini API key has exceeded its quota.")
        print("\nTo check your quota:")
        print("1. Visit: https://ai.google.dev/gemini-api/docs/quota")
        print("2. Monitor usage: https://ai.dev/usage?tab=rate-limit")
        print("\nQuota resets: Daily quotas reset at midnight Pacific Time")
        print("\nTo upgrade:")
        print("- Free tier: 15 requests/min, 1500 requests/day")
        print("- Pay-as-you-go: Higher limits")

print("\n💡 Current fallback: OpenAI TTS (active)")
