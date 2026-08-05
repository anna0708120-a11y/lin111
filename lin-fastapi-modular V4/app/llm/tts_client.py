"""ElevenLabs Text-to-Speech client used only by the on-demand voice endpoint."""
import requests

from app import config


def synth_speech(text):
    if not config.ELEVENLABS_API_KEY or not config.ELEVENLABS_VOICE_ID:
        print("[tts_client] ElevenLabs credentials are not configured")
        return None
    if not text:
        return None
    text = text[:config.TTS_MAX_CHARS]
    try:
        response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{config.ELEVENLABS_VOICE_ID}",
            headers={
                "xi-api-key": config.ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "text": text,
                "model_id": config.ELEVENLABS_MODEL,
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
            },
            timeout=30,
        )
        if response.status_code != 200:
            print(f"[tts_client] ElevenLabs API returned {response.status_code}")
            return None
        return response.content
    except Exception as e:
        print(f"[tts_client] request failed: {e}")
        return None
