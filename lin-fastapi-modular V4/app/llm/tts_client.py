"""
封装对 ElevenLabs Text-to-Speech API 的调⽤。
免费额度：10,000 字/⽉、非商⽤（私⼈⽤不影响）、只能⽤现成⾳⾊库不能克隆声⾳。
⽤量⼩⼼：⼀条语⾳消息就可能吃掉不少额度，所以这个模块不会⾃动帮每条回覆都⽣语⾳，
只在前端你主动点了"播放语⾳"那颗按钮才会呼叫。
"""
import requests
from app import config
def synth_speech(text):
"""
"""
传⽂字，回传 mp3 的原始 bytes；没设key/没选⾳⾊/呼叫失败都回传 None。
if not config.ELEVENLABS_API_KEY or not config.ELEVENLABS_VOICE_ID:
print("[tts_client] 没有设置 ELEVENLABS_API_KEY 或 ELEVENLABS_VOICE_ID，跳过")
return None
if not text:
return None
if len(text) > config.TTS_MAX_CHARS:
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
print(f"[tts_client] 呼叫失败: {response.status_code} {response.text[:200]}")
return None
return response.content
except Exception as e:
print(f"[tts_client] 呼叫失败: {e}")
return None
