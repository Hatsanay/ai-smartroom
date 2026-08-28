import yt_dlp

from . import _state

# open_youtube()/control_youtube() แค่ "สั่ง" ผ่านคำ — app.js เป็นคนลงมือจริงกับ YT.Player ที่ฝังในหน้าเว็บ
# (แท็บแยกคุมไม่ได้). วิดีโอมาจาก yt-dlp ค้นจริงเท่านั้น. คำสั่งเก็บใน _state.pending_action ให้ server.py
# ดึงผ่าน pop_pending_action() หลัง chat.send_message() แล้วส่งกลับไปให้ app.js สั่ง player จริง

_YT_SEARCH_COUNT = 8  # โหลดคิวไว้ล่วงหน้าพอให้ "เปลี่ยนเพลง/เพลงต่อไป" สั่งได้หลายรอบโดยไม่ต้องค้นซ้ำ
_youtube_queue: list[dict] = []  # [{"id": ..., "title": ...}, ...] จากผลค้นหาล่าสุด
_youtube_queue_index: int = -1  # index ของเพลงที่กำลังเล่นอยู่ในคิว (-1 = ยังไม่มีอะไรเล่นอยู่)

# ต้อง sync ค่านี้ให้ตรงกับ YT_VOLUME_STEP ใน app.js เอง (คนละไฟล์คนละภาษา ไม่มีทางแชร์ constant
# เดียวกันได้ตรงๆ) — เก็บระดับเสียงไว้ฝั่ง server ด้วยเพราะ LLM ไม่มีทางรู้ระดับเสียงปัจจุบันเลยถ้าไม่บอก
# ในข้อความตอบ/ประวัติการคุย ผู้ใช้ feedback ว่า "สั่งลดเสียงแล้วรู้สึกเหมือนเพิ่มเอง" เลยให้ตอบระดับ
# เสียงปัจจุบันกลับไปด้วยเสมอ ให้ จัสมิน มี context จริงมาอ้างอิงในบทสนทนาถัดไป ไม่ใช่เดามั่วๆ
_YT_VOLUME_STEP = 25
_YT_DEFAULT_VOLUME = 25  # ผู้ใช้ขอ: เปิด YouTube ใหม่ทุกครั้งเริ่มที่ 25% (ต้องตรงกับ YT_DEFAULT_VOLUME ใน youtube.js)
_youtube_volume = _YT_DEFAULT_VOLUME  # % ปัจจุบัน (ตามที่สั่งผ่าน tool นี้) — reset กลับค่าเริ่มต้นตอนเปิดเพลงใหม่/next/stop เหมือนฝั่ง client


def _search_youtube(query: str, count: int = _YT_SEARCH_COUNT) -> list[dict]:
    ydl_opts = {"quiet": True, "no_warnings": True, "extract_flat": True, "skip_download": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch{count}:{query}", download=False)
    entries = info.get("entries") or []
    return [{"id": e["id"], "title": e.get("title") or "วิดีโอไม่มีชื่อ"} for e in entries if e.get("id")]


def open_youtube(query: str = "") -> str:
    """ค้นหาและเล่นวิดีโอ/เพลงจาก YouTube ให้ผู้ใช้แบบเล่นอัตโนมัติทันที (ไม่ใช่แค่เปิดหน้าค้นหา)
    ใช้เมื่อผู้ใช้ขอให้เปิด/ค้นหา/เล่นเพลงหรือวิดีโอใน YouTube — ถ้าไม่มี query (แค่อยากเปิด YouTube
    เฉยๆ ไม่ได้ระบุเพลง) จะเปิดหน้าแรกของ YouTube แทน เล่นอัตโนมัติไม่ได้เพราะไม่รู้จะเล่นอะไร

    Args:
        query: สิ่งที่อยากฟัง/ดู เช่นชื่อเพลง ศิลปิน หรือชื่อวิดีโอ ปล่อยว่างได้ถ้าแค่อยากเปิด YouTube เฉยๆ

    Returns:
        ข้อความยืนยันสั้นๆ สำหรับตอบผู้ใช้
    """
    global _youtube_queue, _youtube_queue_index, _youtube_volume
    query = query.strip()
    _youtube_volume = _YT_DEFAULT_VOLUME  # เปิด YouTube ใหม่ = เสียงกลับไปที่ค่าเริ่มต้น 25%
    if not query:
        _youtube_queue = []
        _youtube_queue_index = -1
        _state.pending_action = {"type": "open_url", "url": "https://www.youtube.com/"}
        return "เปิด YouTube ให้แล้วค่ะ"

    try:
        results = _search_youtube(query)
    except Exception:
        # yt-dlp พังได้จากหลายสาเหตุ (เน็ตหลุด, YouTube เปลี่ยนโครงหน้าเว็บ ฯลฯ) ไม่ใช่ควรพังทั้ง request
        return f'หาเพลง/วิดีโอ "{query}" ไม่สำเร็จค่ะ ระบบค้นหา YouTube อาจติดขัดชั่วคราว'

    if not results:
        _youtube_queue = []
        _youtube_queue_index = -1
        return f'ไม่พบผลลัพธ์สำหรับ "{query}" ใน YouTube ค่ะ'

    _youtube_queue = results
    _youtube_queue_index = 0
    first = results[0]
    # reset_volume=True -> app.js ตั้งเสียงกลับไป 25% (เปิดใหม่เท่านั้น ไม่ใช่ตอน "เปลี่ยนเพลง")
    _state.pending_action = {
        "type": "play_youtube",
        "video_id": first["id"],
        "title": first["title"],
        "reset_volume": True,
    }
    return f'เปิดเพลง "{first["title"]}" ให้แล้วค่ะ'


def control_youtube(action: str) -> str:
    """สั่งควบคุมวิดีโอ/เพลง YouTube ที่กำลังเล่นอยู่ (ต้องเปิดผ่าน open_youtube() มาก่อนแล้วเท่านั้น)
    เรียกเฉพาะตอนผู้ใช้ขอชัดเจนจริงๆ เท่านั้นว่าอยากหยุดชั่วคราว/เล่นต่อ/ปิด/เปลี่ยนเพลงถัดไป/
    เพิ่มหรือลดเสียง/เปิดเต็มจอ/ออกจากเต็มจอ — ห้ามเรียกเองเดาเอาว่าผู้ใช้อาจต้องการ (เช่น ห้ามเพิ่ม/
    ลดเสียงเองโดยผู้ใช้ไม่ได้พูดถึงเรื่องเสียงเพลงเลย แม้จะเพิ่งคุยเรื่องเพลงกันมาก่อนหน้านี้ก็ตาม)

    Args:
        action: หนึ่งใน "pause" (หยุดชั่วคราว), "resume" (เล่นต่อ), "stop" (ปิดเลย),
            "next" (เปลี่ยนเป็นผลลัพธ์ถัดไปจากการค้นหาล่าสุด),
            "volume_up" (เพิ่มเสียงเพลง), "volume_down" (ลดเสียงเพลง),
            "fullscreen" (เปิดวิดีโอเต็มจอ), "exit_fullscreen" (ออกจากโหมดเต็มจอ) —
            ถ้าผู้ใช้ขอเปิดเพลงใหม่พร้อมเต็มจอในประโยคเดียว ให้เรียก open_youtube() ก่อน แล้วบอกผู้ใช้
            ว่าเปิดให้แล้ว สั่ง "เต็มจอ" ต่อได้เลย (เรียก 2 อย่างในเทิร์นเดียวไม่ได้ ตัวหลังจะทับตัวแรก)

    Returns:
        ข้อความยืนยันสั้นๆ สำหรับตอบผู้ใช้ — สำหรับ volume_up/volume_down จะบอกเปอร์เซ็นต์เสียงปัจจุบัน
        ไว้ในข้อความด้วยเสมอ ให้มี context จริงไว้อ้างอิงต่อได้ในบทสนทนาถัดไป (ไม่ใช่เดาระดับเสียงเอาเอง)
    """
    global _youtube_queue, _youtube_queue_index, _youtube_volume
    action = action.strip().lower()

    if action == "next":
        if _youtube_queue_index < 0 or _youtube_queue_index + 1 >= len(_youtube_queue):
            return "หมดคิวเพลงที่ค้นไว้แล้วค่ะ ลองสั่งเปิดเพลงใหม่ได้เลยค่ะ"
        _youtube_queue_index += 1
        track = _youtube_queue[_youtube_queue_index]
        # เปลี่ยนเพลง = คงระดับเสียงเดิมไว้ (reset_volume ไม่ส่ง / False) — ผู้ใช้ขอชัดเจน
        _state.pending_action = {
            "type": "play_youtube",
            "video_id": track["id"],
            "title": track["title"],
            "reset_volume": False,
        }
        return f'เปลี่ยนเป็นเพลง "{track["title"]}" ให้แล้วค่ะ'

    if action in {"pause", "resume", "stop", "volume_up", "volume_down", "fullscreen", "exit_fullscreen"}:
        if action == "stop":
            _youtube_queue = []
            _youtube_queue_index = -1
            _youtube_volume = _YT_DEFAULT_VOLUME
        elif action == "volume_up":
            _youtube_volume = min(100, _youtube_volume + _YT_VOLUME_STEP)
        elif action == "volume_down":
            _youtube_volume = max(0, _youtube_volume - _YT_VOLUME_STEP)
        _state.pending_action = {"type": "youtube_control", "action": action}
        return {
            "pause": "หยุดเพลงไว้ชั่วคราวให้แล้วค่ะ",
            "resume": "เล่นเพลงต่อให้แล้วค่ะ",
            "stop": "ปิดเพลงให้แล้วค่ะ",
            "volume_up": f"เพิ่มเสียงเพลงให้แล้วค่ะ ตอนนี้อยู่ที่ {_youtube_volume}%",
            "volume_down": f"ลดเสียงเพลงให้แล้วค่ะ ตอนนี้อยู่ที่ {_youtube_volume}%",
            "fullscreen": "เปิดวิดีโอเต็มจอให้แล้วค่ะ (กด Esc เพื่อออก)",
            "exit_fullscreen": "ออกจากโหมดเต็มจอให้แล้วค่ะ",
        }[action]

    return "ไม่เข้าใจคำสั่งควบคุมเพลงนี้ค่ะ"
