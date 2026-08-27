"""เสียงพูดภาษาไทยฝั่ง server — 2 engine สลับกันได้ (ดู VALID_ENGINES):

- 'vachana' (ค่าเริ่มต้น) — VachanaTTS (VITS) เรียก Voice/SpeechConfig ระดับล่างตรงๆ แทนที่จะผ่าน
  wrapper ของ pythaitts/vachanatts.main เพราะ wrapper ไม่เปิดช่องให้ปิด normalize_audio ได้
  (ดูเหตุผลด้านล่าง) และไม่คั่นช่วงเงียบระหว่างประโยคเลย รันในเครื่องล้วนๆ ไม่ต้องมีเน็ต คุณภาพดีสุด
- 'google' — Google Translate TTS (ผ่าน gTTS) ทางเลือกสำรอง/สำหรับสลับเล่นดู ต้องมีเน็ต
  ปรับแต่งเสียง (speed/noise) ไม่ได้เหมือน vachana และเป็น endpoint ไม่เป็นทางการ อาจโดน
  rate-limit ถ้าเรียกถี่มาก

ทดสอบเทียบหลายค่าของ vachana แล้วพบ 3 จุดที่ทำให้เสียงฟังเพี้ยน/เว้นวรรคไม่เป็นธรรมชาติ:

1. noise_w_scale/noise_scale ค่าเริ่มต้นของไลบรารี (0.8/0.667) สุ่มจังหวะคำมากเกินไป
   ลดค่าลงแล้วฟังเป็นธรรมชาติขึ้นชัดเจน (ยืนยันจากการเทียบเสียงจริงหลายแบบ)
2. SpeechConfig.normalize_audio=True (ค่า default) ดันทุกประโยคให้ดังสุด (peak=1.0) เท่ากันหมด
   ทั้งที่แต่ละประโยคมีความดังตามธรรมชาติไม่เท่ากัน (วัดจริงพบ RMS ต่างกันถึง ~30% ระหว่างประโยค)
   ทำให้ได้ยินเสียงดัง-เบาสลับกันกระโดดไปมาระหว่างประโยค ฟังเหมือนเสียงเพี้ยน/ไม่สม่ำเสมอ
3. Voice.synthesize_wav() ต่อเสียงแต่ละประโยคติดกันตรงๆ ไม่มีช่วงเงียบคั่นเลย ฟังดูรวบรัดเกินไป
   เลยแทรกช่วงเงียบสั้นๆ เองระหว่างประโยค (SENTENCE_GAP_MS)
"""
import io
import wave

import numpy as np
from gtts import gTTS
from vachanatts.config import SpeechConfig
from vachanatts.main import load_voice
from vachanatts.voice import Voice

VALID_VOICES = {"th_f_1", "th_m_1", "th_f_2", "th_m_2"}
DEFAULT_VOICE = "th_f_1"
VALID_ENGINES = {"vachana", "google"}
DEFAULT_ENGINE = "vachana"

# ค่าที่ปรับจนฟังเป็นธรรมชาติที่สุดจากการเทียบเสียงจริง (ค่าเริ่มต้นของไลบรารีคือ 0.667/0.8)
NOISE_SCALE = 0.4
NOISE_W_SCALE = 0.3

# ความเร็วพูด: 1.0 = ปกติ, ต่ำกว่า 1.0 = ช้าลง (เช็คซอร์ส vachanatts/main.py แล้วว่า
# length_scale = 1/speed ตรงตามสัญชาตญาณ ไม่ใช่กลับด้าน)
SPEED = 0.9

# ช่วงเงียบคั่นระหว่างประโยค กันเสียงรวบรัดเกินไปตอนต่อหลายประโยคเข้าด้วยกัน
SENTENCE_GAP_MS = 180

_voice_cache: dict[str, Voice] = {}


def _get_voice(voice_id: str) -> Voice:
    if voice_id not in _voice_cache:
        _voice_cache[voice_id] = load_voice(voice_id)  # แคชเอง กันโหลดโมเดลซ้ำทุก request
    return _voice_cache[voice_id]


def synthesize(text: str, voice: str = DEFAULT_VOICE, engine: str = DEFAULT_ENGINE) -> tuple[bytes, str]:
    """แปลงข้อความเป็นเสียงพูด คืนค่าเป็น (ไบต์เสียง, media_type) — engine 'vachana' คืน WAV
    (เสียงคุณภาพสูง รันในเครื่อง ปรับแต่งเองได้), engine 'google' คืน MP3 (ทางเลือกผ่าน Google
    Translate TTS แบบไม่เป็นทางการ ต้องมีเน็ต ปรับแต่งไม่ได้ ไว้ใช้เป็น fallback/ทางเลือก)"""
    if engine not in VALID_ENGINES:
        engine = DEFAULT_ENGINE
    if engine == "google":
        return _synthesize_google(text), "audio/mpeg"
    return _synthesize_vachana(text, voice), "audio/wav"


def _synthesize_google(text: str) -> bytes:
    buf = io.BytesIO()
    gTTS(text=text, lang="th").write_to_fp(buf)
    return buf.getvalue()


def _synthesize_vachana(text: str, voice: str) -> bytes:
    if voice not in VALID_VOICES:
        voice = DEFAULT_VOICE

    v = _get_voice(voice)
    cfg = SpeechConfig(
        volume=1.0,
        length_scale=1 / SPEED,
        noise_scale=NOISE_SCALE,
        noise_w_scale=NOISE_W_SCALE,
        normalize_audio=False,  # ปิด กันแต่ละประโยคถูกดันไปดังสุดเท่ากันหมดจนฟังเพี้ยน (ดูหมายเหตุบนสุด)
    )

    sample_rate = None
    sample_width = None
    channels = None
    pcm_parts: list[bytes] = []

    for i, chunk in enumerate(v.synthesize(text, cfg)):
        if sample_rate is None:
            sample_rate = chunk.sample_rate
            sample_width = chunk.sample_width
            channels = chunk.sample_channels
        elif i > 0 and SENTENCE_GAP_MS > 0:
            gap_samples = int(sample_rate * SENTENCE_GAP_MS / 1000)
            pcm_parts.append(np.zeros(gap_samples, dtype=np.int16).tobytes())
        pcm_parts.append(chunk.audio_int16_bytes)

    if sample_rate is None:
        # สังเคราะห์ไม่ได้เลย (เช่นข้อความว่าง) คืน WAV เงียบสั้นๆ กันฝั่ง client พังตอนเล่น
        sample_rate, sample_width, channels = 22050, 2, 1
        pcm_parts = [b""]

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        wav_file.setframerate(sample_rate)
        wav_file.setsampwidth(sample_width)
        wav_file.setnchannels(channels)
        wav_file.writeframes(b"".join(pcm_parts))
    return buf.getvalue()
