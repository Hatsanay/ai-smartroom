import requests
import yt_dlp
from ddgs import DDGS
from ddgs.exceptions import DDGSException

# สร้างครั้งเดียวใช้ซ้ำทุก request แทนสร้างใหม่ทุกครั้งที่ค้น (server เป็น process เดียวรันยาว)
_ddgs = DDGS()


def search_web(query: str) -> str:
    """ค้นหาข้อมูลบนอินเทอร์เน็ตแบบเรียลไทม์ ใช้เมื่อ user ถามเรื่องที่ต้องการข้อมูลล่าสุด
    เช่น ข่าว ราคาสินค้า สภาพอากาศ หรือเรื่องที่ไม่แน่ใจว่าข้อมูลในตัวเองยังทันสมัยอยู่ไหม

    Args:
        query: คำค้นหา ภาษาไทยหรืออังกฤษก็ได้

    Returns:
        สรุปผลการค้นหา 5 อันดับแรก (หัวข้อ, เนื้อหาย่อ, ลิงก์)
    """
    try:
        results = _ddgs.text(query, max_results=5)
    except DDGSException:
        # ddgs (ตั้งแต่รุ่นที่ใช้อยู่) ยิง exception ตอนไม่เจอผลลัพธ์/โดน rate-limit/timeout แทนที่จะคืน
        # list ว่างเหมือนที่โค้ดเดิมคาดไว้ — เจอจริงตอนทดสอบ (DDGSException: No results found.)
        # ไม่ครอบ try/except ไว้ตรงนี้ = Gemini function calling เจอ exception ดิบ ตอบลูกค้าแบบกำกวม
        return "ไม่พบผลการค้นหาสำหรับคำนี้ค่ะ (หรือระบบค้นหาอาจติดขัดชั่วคราว)"

    if not results:
        return "ไม่พบผลการค้นหาสำหรับคำนี้"

    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}\n   {r['body']}\n   {r['href']}")
    return "\n".join(lines)


# Open-Meteo (open-meteo.com) — พยากรณ์อากาศฟรี ไม่ต้องขอ API key เหมือน ddgs/yt-dlp (ตัดสินใจเลือก
# ตัวนี้แทน OpenWeatherMap/WeatherAPI ที่ต้องสมัครขอ key ก่อนถึงจะใช้ได้) ใช้ geocoding API แปลงชื่อ
# สถานที่เป็นพิกัดก่อน แล้วค่อยยิง forecast API ด้วยพิกัดนั้นอีกที (คนละ endpoint กัน)
_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# แปลรหัสสภาพอากาศ WMO (มาตรฐานที่ Open-Meteo ใช้) เป็นคำอธิบายไทย + emoji ไอคอน + หมวด "fx" (สำหรับ
# เลือก animation พื้นหลังใน UI: sunny/cloudy/fog/rain/snow/storm) — คำนวณครั้งเดียวฝั่ง server แล้วส่ง
# ค่าที่พร้อมแสดงผลไปให้ทั้งข้อความตอบและ UI เลย กัน mapping ชุดเดียวกันต้องเขียนซ้ำสองที่ (Python ฝั่งนี้
# กับ JS ฝั่ง client) ซึ่งเสี่ยงหลุดไม่ตรงกันในระยะยาว — animation จริงอิงจากสภาพอากาศจริงเสมอ ไม่ใช่ของสุ่ม
_WMO_WEATHER = {
    0: ("ท้องฟ้าโปร่ง", "☀️", "sunny"),
    1: ("มีเมฆบางส่วน", "🌤️", "sunny"),
    2: ("เมฆเป็นบางส่วน", "⛅", "cloudy"),
    3: ("เมฆมาก", "☁️", "cloudy"),
    45: ("หมอก", "🌫️", "fog"),
    48: ("หมอกน้ำแข็งเกาะ", "🌫️", "fog"),
    51: ("ฝนตกปรอยๆ เบา", "🌦️", "rain"),
    53: ("ฝนตกปรอยๆ ปานกลาง", "🌦️", "rain"),
    55: ("ฝนตกปรอยๆ หนัก", "🌦️", "rain"),
    56: ("ฝนตกปรอยๆ เยือกแข็ง", "🌧️", "rain"),
    57: ("ฝนตกปรอยๆ เยือกแข็งหนัก", "🌧️", "rain"),
    61: ("ฝนตกเบา", "🌧️", "rain"),
    63: ("ฝนตกปานกลาง", "🌧️", "rain"),
    65: ("ฝนตกหนัก", "🌧️", "rain"),
    66: ("ฝนเยือกแข็งเบา", "🌧️", "rain"),
    67: ("ฝนเยือกแข็งหนัก", "🌧️", "rain"),
    71: ("หิมะตกเบา", "🌨️", "snow"),
    73: ("หิมะตกปานกลาง", "🌨️", "snow"),
    75: ("หิมะตกหนัก", "🌨️", "snow"),
    77: ("เกล็ดหิมะ", "🌨️", "snow"),
    80: ("ฝนซู่เบา", "🌦️", "rain"),
    81: ("ฝนซู่ปานกลาง", "🌦️", "rain"),
    82: ("ฝนซู่หนักมาก", "⛈️", "storm"),
    85: ("หิมะซู่เบา", "🌨️", "snow"),
    86: ("หิมะซู่หนัก", "🌨️", "snow"),
    95: ("พายุฝนฟ้าคะนอง", "⛈️", "storm"),
    96: ("พายุฝนฟ้าคะนองมีลูกเห็บ", "⛈️", "storm"),
    99: ("พายุฝนฟ้าคะนองมีลูกเห็บหนัก", "⛈️", "storm"),
}
_DEFAULT_WEATHER_DESC = ("ไม่ทราบสภาพอากาศ", "❓", "cloudy")


def _describe_weather_code(code) -> tuple[str, str, str]:
    return _WMO_WEATHER.get(code, _DEFAULT_WEATHER_DESC)


def get_weather(location: str) -> str:
    """เช็คสภาพอากาศปัจจุบันและพยากรณ์ 4 วันข้างหน้าของสถานที่ที่ระบุ ใช้เมื่อผู้ใช้ถามเรื่องอากาศ/
    อุณหภูมิ/ฝนจะตกไหม/ร้อนไหม/หนาวไหม ฯลฯ

    Args:
        location: ชื่อสถานที่ เช่น ชื่อจังหวัด/เมือง/ประเทศ (ภาษาไทยหรืออังกฤษก็ได้) ถ้าผู้ใช้ไม่ได้
            ระบุที่มาก่อนเลยและไม่มีบริบทให้เดา ให้ถามผู้ใช้กลับว่าอยากรู้อากาศที่ไหนแทนการเรียก tool นี้

    Returns:
        สรุปสภาพอากาศปัจจุบันเป็นข้อความสั้นๆ
    """
    global _pending_action
    location = location.strip()
    if not location:
        return "บอกชื่อสถานที่ที่อยากรู้สภาพอากาศด้วยนะคะ"

    try:
        geo_resp = requests.get(
            _GEOCODE_URL,
            params={"name": location, "count": 1, "language": "th", "format": "json"},
            timeout=8,
        )
        geo_resp.raise_for_status()
        geo_results = geo_resp.json().get("results") or []
    except Exception:
        return f'ค้นหาตำแหน่ง "{location}" ไม่สำเร็จค่ะ ระบบอาจติดขัดชั่วคราว'

    if not geo_results:
        return f'ไม่พบสถานที่ชื่อ "{location}" ค่ะ ลองพิมพ์ชื่อให้ชัดเจนขึ้นได้ไหมคะ'

    place = geo_results[0]
    lat, lon = place["latitude"], place["longitude"]
    display_name = place.get("name", location)
    admin = place.get("admin1")
    if admin and admin != display_name:
        display_name = f"{display_name}, {admin}"

    try:
        wx_resp = requests.get(
            _FORECAST_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,is_day",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min",
                "timezone": "auto",
                "forecast_days": 4,
            },
            timeout=8,
        )
        wx_resp.raise_for_status()
        wx = wx_resp.json()
    except Exception:
        return f"เช็คสภาพอากาศของ{display_name}ไม่สำเร็จค่ะ ระบบพยากรณ์อากาศอาจติดขัดชั่วคราว"

    current = wx.get("current") or {}
    temp = current.get("temperature_2m")
    feels_like = current.get("apparent_temperature")
    humidity = current.get("relative_humidity_2m")
    wind = current.get("wind_speed_10m")
    condition_text, emoji, fx = _describe_weather_code(current.get("weather_code"))
    is_day = bool(current.get("is_day", 1))

    daily = wx.get("daily") or {}
    dates = daily.get("time") or []
    codes = daily.get("weather_code") or []
    highs = daily.get("temperature_2m_max") or []
    lows = daily.get("temperature_2m_min") or []
    forecast = []
    for i in range(min(len(dates), 4)):
        day_condition, day_emoji, _day_fx = _describe_weather_code(codes[i]) if i < len(codes) else _DEFAULT_WEATHER_DESC
        forecast.append(
            {
                "date": dates[i],
                "max": round(highs[i]) if i < len(highs) and highs[i] is not None else None,
                "min": round(lows[i]) if i < len(lows) and lows[i] is not None else None,
                "condition": day_condition,
                "emoji": day_emoji,
            }
        )

    _pending_action = {
        "type": "show_weather",
        "data": {
            "location": display_name,
            "temperature": round(temp) if temp is not None else None,
            "feels_like": round(feels_like) if feels_like is not None else None,
            "humidity": humidity,
            "wind_speed": wind,
            "condition": condition_text,
            "emoji": emoji,
            "fx": fx,
            "is_day": is_day,
            "forecast": forecast,
        },
    }

    return (
        f"ตอนนี้ที่{display_name} {condition_text} {emoji} อุณหภูมิ {round(temp) if temp is not None else '-'}"
        f"°C (รู้สึกเหมือน {round(feels_like) if feels_like is not None else '-'}°C) "
        f"ความชื้น {humidity}% ลมแรง {wind} กม./ชม.ค่ะ"
    )


# LLM เรียก open_youtube()/control_youtube() ได้แค่ "สั่ง" ผ่านคำ (มือที่เชื่อถือได้คือโค้ดข้างล่างนี้
# ไม่ใช่ LLM แปะ URL/สั่งเล่นเองตรงๆ) — วิดีโอที่เล่นได้มาจาก yt-dlp ค้นหาจริงเท่านั้น (ฟรี ไม่ต้องขอ
# API key ต่างจาก YouTube Data API) ส่วนการเล่นจริงต้องฝัง YouTube IFrame Player ในหน้าเว็บ (ไม่ใช่
# เปิดแท็บแยก) ถึงจะสั่งหยุด/เล่นต่อ/เปลี่ยนเพลงจากโค้ดเราได้จริง (แท็บแยกคุมจากภายนอกไม่ได้เลย)
# เก็บ "คำสั่งที่ต้องทำจริง" ไว้ใน _pending_action แทนการลงมือเองฝั่ง server เพราะ server รันบน
# เครื่อง/process ที่อาจคนละเครื่องกับเบราว์เซอร์ผู้ใช้ (โดยเฉพาะแผนย้ายไป Pi ในอนาคต) เลยต้องส่ง
# คำสั่งกลับไปให้ฝั่งเว็บ (app.js) เป็นคนสั่ง player จริงแทน — ดู pop_pending_action() ที่ server.py เรียก
_pending_action: dict | None = None

_YT_SEARCH_COUNT = 8  # โหลดคิวไว้ล่วงหน้าพอให้ "เปลี่ยนเพลง/เพลงต่อไป" สั่งได้หลายรอบโดยไม่ต้องค้นซ้ำ
_youtube_queue: list[dict] = []  # [{"id": ..., "title": ...}, ...] จากผลค้นหาล่าสุด
_youtube_queue_index: int = -1  # index ของเพลงที่กำลังเล่นอยู่ในคิว (-1 = ยังไม่มีอะไรเล่นอยู่)

# ต้อง sync ค่านี้ให้ตรงกับ YT_VOLUME_STEP ใน app.js เอง (คนละไฟล์คนละภาษา ไม่มีทางแชร์ constant
# เดียวกันได้ตรงๆ) — เก็บระดับเสียงไว้ฝั่ง server ด้วยเพราะ LLM ไม่มีทางรู้ระดับเสียงปัจจุบันเลยถ้าไม่บอก
# ในข้อความตอบ/ประวัติการคุย ผู้ใช้ feedback ว่า "สั่งลดเสียงแล้วรู้สึกเหมือนเพิ่มเอง" เลยให้ตอบระดับ
# เสียงปัจจุบันกลับไปด้วยเสมอ ให้ FRIDAY มี context จริงมาอ้างอิงในบทสนทนาถัดไป ไม่ใช่เดามั่วๆ
_YT_VOLUME_STEP = 25
_youtube_volume = 100  # % ปัจจุบัน (ตามที่สั่งผ่าน tool นี้เท่านั้น — reset กลับ 100 ตอน stop เหมือนฝั่ง client)


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
    global _pending_action, _youtube_queue, _youtube_queue_index
    query = query.strip()
    if not query:
        _youtube_queue = []
        _youtube_queue_index = -1
        _pending_action = {"type": "open_url", "url": "https://www.youtube.com/"}
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
    _pending_action = {"type": "play_youtube", "video_id": first["id"], "title": first["title"]}
    return f'เปิดเพลง "{first["title"]}" ให้แล้วค่ะ'


def control_youtube(action: str) -> str:
    """สั่งควบคุมวิดีโอ/เพลง YouTube ที่กำลังเล่นอยู่ (ต้องเปิดผ่าน open_youtube() มาก่อนแล้วเท่านั้น)
    เรียกเฉพาะตอนผู้ใช้ขอชัดเจนจริงๆ เท่านั้นว่าอยากหยุดชั่วคราว/เล่นต่อ/ปิด/เปลี่ยนเพลงถัดไป/
    เพิ่มหรือลดเสียง — ห้ามเรียกเองเดาเอาว่าผู้ใช้อาจต้องการ (เช่น ห้ามเพิ่ม/ลดเสียงเองโดยผู้ใช้ไม่ได้พูดถึง
    เรื่องเสียงเพลงเลย แม้จะเพิ่งคุยเรื่องเพลงกันมาก่อนหน้านี้ก็ตาม)

    Args:
        action: หนึ่งใน "pause" (หยุดชั่วคราว), "resume" (เล่นต่อ), "stop" (ปิดเลย),
            "next" (เปลี่ยนเป็นผลลัพธ์ถัดไปจากการค้นหาล่าสุด),
            "volume_up" (เพิ่มเสียงเพลง), "volume_down" (ลดเสียงเพลง)

    Returns:
        ข้อความยืนยันสั้นๆ สำหรับตอบผู้ใช้ — สำหรับ volume_up/volume_down จะบอกเปอร์เซ็นต์เสียงปัจจุบัน
        ไว้ในข้อความด้วยเสมอ ให้มี context จริงไว้อ้างอิงต่อได้ในบทสนทนาถัดไป (ไม่ใช่เดาระดับเสียงเอาเอง)
    """
    global _pending_action, _youtube_queue, _youtube_queue_index, _youtube_volume
    action = action.strip().lower()

    if action == "next":
        if _youtube_queue_index < 0 or _youtube_queue_index + 1 >= len(_youtube_queue):
            return "หมดคิวเพลงที่ค้นไว้แล้วค่ะ ลองสั่งเปิดเพลงใหม่ได้เลยค่ะ"
        _youtube_queue_index += 1
        track = _youtube_queue[_youtube_queue_index]
        _pending_action = {"type": "play_youtube", "video_id": track["id"], "title": track["title"]}
        return f'เปลี่ยนเป็นเพลง "{track["title"]}" ให้แล้วค่ะ'

    if action in {"pause", "resume", "stop", "volume_up", "volume_down"}:
        if action == "stop":
            _youtube_queue = []
            _youtube_queue_index = -1
            _youtube_volume = 100
        elif action == "volume_up":
            _youtube_volume = min(100, _youtube_volume + _YT_VOLUME_STEP)
        elif action == "volume_down":
            _youtube_volume = max(0, _youtube_volume - _YT_VOLUME_STEP)
        _pending_action = {"type": "youtube_control", "action": action}
        return {
            "pause": "หยุดเพลงไว้ชั่วคราวให้แล้วค่ะ",
            "resume": "เล่นเพลงต่อให้แล้วค่ะ",
            "stop": "ปิดเพลงให้แล้วค่ะ",
            "volume_up": f"เพิ่มเสียงเพลงให้แล้วค่ะ ตอนนี้อยู่ที่ {_youtube_volume}%",
            "volume_down": f"ลดเสียงเพลงให้แล้วค่ะ ตอนนี้อยู่ที่ {_youtube_volume}%",
        }[action]

    return "ไม่เข้าใจคำสั่งควบคุมเพลงนี้ค่ะ"


def pop_pending_action() -> dict | None:
    """ดึง action ที่ tool ล่าสุดสั่งไว้ (ถ้ามี) ออกมาแล้วเคลียร์ทิ้ง กันหลงเหลือข้ามไปโผล่ใน request ถัดไป"""
    global _pending_action
    action, _pending_action = _pending_action, None
    return action
