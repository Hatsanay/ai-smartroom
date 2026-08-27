import json
import os
import shutil
from datetime import datetime

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

# พิกัดเบราว์เซอร์ของผู้ใช้ (navigator.geolocation) — server.py เซ็ตค่านี้ก่อนเรียก chat.send_message()
# ทุกครั้งแล้วล้างทิ้ง (None) หลังจบ เหมือน _pending_action — โครงเดียวกัน: ข้อมูลอยู่ฝั่ง browser แต่
# tool รันฝั่ง server เลยต้องให้ client แนบมากับ request ใช้ตอนผู้ใช้ถามอากาศโดยไม่ระบุสถานที่
_client_location: dict | None = None

# คำที่สื่อว่า "ตำแหน่งปัจจุบัน" ไม่ใช่ชื่อสถานที่เจาะจง — เจอคำพวกนี้ (หรือ location ว่าง) แล้วมีพิกัด
# จากเบราว์เซอร์ ให้ใช้พิกัดนั้นแทนการ geocode ชื่อ
_HERE_ALIASES = {
    "", "ที่นี่", "ตรงนี้", "แถวนี้", "แถบนี้", "รอบตัว", "ปัจจุบัน", "ตำแหน่งปัจจุบัน", "ตำแหน่งของฉัน",
    "ตำแหน่งของผม", "ที่ฉันอยู่", "ที่ผมอยู่", "ที่อยู่ปัจจุบัน", "here", "current", "current location", "my location",
}


def set_client_location(geo: dict | None) -> None:
    """server.py เรียกก่อน chat.send_message() ทุกครั้ง (แล้วล้างด้วย None หลังจบ) — เก็บพิกัดเบราว์เซอร์
    ผู้ใช้ไว้ให้ get_weather() หยิบไปใช้ รับเฉพาะ dict ที่มี lat/lon เป็นตัวเลขจริง นอกนั้นถือว่าไม่มีพิกัด"""
    global _client_location
    if isinstance(geo, dict):
        try:
            lat = float(geo["lat"])
            lon = float(geo["lon"])
        except (KeyError, TypeError, ValueError):
            _client_location = None
            return
        label = geo.get("label")
        _client_location = {
            "lat": lat,
            "lon": lon,
            "label": label.strip() if isinstance(label, str) and label.strip() else None,
        }
    else:
        _client_location = None


def _describe_weather_code(code) -> tuple[str, str, str]:
    return _WMO_WEATHER.get(code, _DEFAULT_WEATHER_DESC)


def _build_weather_reply(lat, lon, display_name: str) -> str:
    """ยิง forecast API ด้วยพิกัดที่ได้มา แล้วประกอบทั้งข้อความตอบ + _pending_action สำหรับ UI —
    แยกออกมาเป็นฟังก์ชันต่างหากเพราะพิกัดมาได้ 2 ทาง: geocoding จากชื่อสถานที่ที่ผู้ใช้บอก หรือ
    navigator.geolocation ของเบราว์เซอร์ (ตอนผู้ใช้ถามอากาศ 'ที่นี่' โดยไม่ระบุชื่อเมือง)"""
    global _pending_action
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


def get_weather(location: str = "") -> str:
    """เช็คสภาพอากาศปัจจุบันและพยากรณ์ 4 วันข้างหน้า ใช้เมื่อผู้ใช้ถามเรื่องอากาศ/อุณหภูมิ/ฝนจะตกไหม/
    ร้อนไหม/หนาวไหม ฯลฯ

    Args:
        location: ชื่อสถานที่ เช่น จังหวัด/เมือง/ประเทศ (ภาษาไทยหรืออังกฤษก็ได้) — **ถ้าผู้ใช้ถามอากาศ
            "ที่นี่" หรือไม่ได้ระบุสถานที่ ให้ปล่อยว่างไว้ (หรือใส่ "ปัจจุบัน")** ระบบจะใช้พิกัดจาก
            เบราว์เซอร์ของผู้ใช้เองอัตโนมัติ ไม่ต้องถามชื่อเมืองกลับก่อน — ยกเว้น tool ตอบกลับมาว่า
            เข้าถึงตำแหน่งไม่ได้ ค่อยถามผู้ใช้ว่าอยากรู้อากาศที่ไหน

    Returns:
        สรุปสภาพอากาศปัจจุบันเป็นข้อความสั้นๆ
    """
    location = (location or "").strip()

    # ไม่ระบุสถานที่ หรือบอกว่า "ที่นี่"/"ปัจจุบัน" -> ใช้พิกัดจากเบราว์เซอร์ (server.py เซ็ตไว้ก่อนเรียก LLM)
    if location.lower() in _HERE_ALIASES:
        if _client_location:
            label = _client_location.get("label") or "ตำแหน่งปัจจุบัน"
            return _build_weather_reply(_client_location["lat"], _client_location["lon"], label)
        return (
            "ยังเข้าถึงตำแหน่งปัจจุบันไม่ได้ค่ะ (เบราว์เซอร์ยังไม่ได้อนุญาตให้เข้าถึงตำแหน่ง) "
            "บอกชื่อเมือง/จังหวัดที่อยากรู้อากาศมาได้เลยค่ะ"
        )

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

    return _build_weather_reply(lat, lon, display_name)


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
# เสียงปัจจุบันกลับไปด้วยเสมอ ให้ จัสมิน มี context จริงมาอ้างอิงในบทสนทนาถัดไป ไม่ใช่เดามั่วๆ
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
    global _pending_action, _youtube_queue, _youtube_queue_index, _youtube_volume
    action = action.strip().lower()

    if action == "next":
        if _youtube_queue_index < 0 or _youtube_queue_index + 1 >= len(_youtube_queue):
            return "หมดคิวเพลงที่ค้นไว้แล้วค่ะ ลองสั่งเปิดเพลงใหม่ได้เลยค่ะ"
        _youtube_queue_index += 1
        track = _youtube_queue[_youtube_queue_index]
        _pending_action = {"type": "play_youtube", "video_id": track["id"], "title": track["title"]}
        return f'เปลี่ยนเป็นเพลง "{track["title"]}" ให้แล้วค่ะ'

    if action in {"pause", "resume", "stop", "volume_up", "volume_down", "fullscreen", "exit_fullscreen"}:
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
            "fullscreen": "เปิดวิดีโอเต็มจอให้แล้วค่ะ (กด Esc เพื่อออก)",
            "exit_fullscreen": "ออกจากโหมดเต็มจอให้แล้วค่ะ",
        }[action]

    return "ไม่เข้าใจคำสั่งควบคุมเพลงนี้ค่ะ"


def pop_pending_action() -> dict | None:
    """ดึง action ที่ tool ล่าสุดสั่งไว้ (ถ้ามี) ออกมาแล้วเคลียร์ทิ้ง กันหลงเหลือข้ามไปโผล่ใน request ถัดไป"""
    global _pending_action
    action, _pending_action = _pending_action, None
    return action


# เข้าถึงไฟล์ในคอม — ผู้ใช้ขอชัดเจนว่าต้อง "จำกัดแค่โฟลเดอร์ที่กำหนดไว้" เท่านั้น (ไม่ใช่ทั้งเครื่อง)
# เลือกโฟลเดอร์ผ่านปุ่มใน UI (native folder picker ของ Windows ผ่าน tkinter — ใช้ได้เพราะ server กับ
# browser รันอยู่บนเครื่องเดียวกัน ถ้าย้ายไป Pi ในอนาคตกลไกนี้ใช้ไม่ได้แล้ว ต้องคิดใหม่) เก็บ path ไว้ใน
# _allowed_folder ตัวเดียว (personal use คนเดียวเหมือน state อื่นๆ ในไฟล์นี้)
#
# **จุด security ที่สำคัญที่สุดของ tool ชุดนี้**: ทุก path ที่ LLM ส่งมาต้อง resolve เป็น absolute path
# จริงแล้วเช็คด้วย os.path.commonpath() ว่าอยู่ใต้ _allowed_folder จริงๆ เท่านั้น — ไม่ใช้ str.startswith()
# เทียบ prefix ตรงๆ เพราะพลาดง่าย (เช่น "/allowed" จะ match ผิดกับ "/allowed-secret" ที่จริงเป็นคนละ
# โฟลเดอร์กันเลย) กัน LLM ใช้ "../" หรือ absolute path หลอกให้อ่านไฟล์นอกขอบเขตที่ผู้ใช้อนุญาตไว้
_allowed_folder: str | None = None

_ALLOWED_TEXT_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".csv", ".json", ".py", ".log", ".yaml", ".yml", ".xml", ".ini", ".cfg",
}
_MAX_FILE_READ_BYTES = 200_000  # ~200KB กันไฟล์ใหญ่เกินไปจนบวม context ของ Gemini

# ไฟล์ log กิจกรรมเกี่ยวกับข้อมูลในเครื่อง — ผู้ใช้ขอไว้เป็นกลไกความโปร่งใส เพราะตอนนี้ จัสมิน แก้ไข/
# ลบไฟล์ได้จริงแล้ว (ไม่ใช่แค่อ่าน) เก็บไว้ที่ jusmin-ai/logs/ (แยกจากโฟลเดอร์ที่ผู้ใช้เลือก ตั้งใจไม่
# เอาไปแปะปนกับไฟล์จริงของผู้ใช้) สร้างไฟล์ log **ใหม่** ทุกครั้งที่เลือกโฟลเดอร์ใหม่ (ตามที่ผู้ใช้ขอ) —
# ตั้งชื่อด้วย timestamp กันไฟล์เก่าถูกเขียนทับ เก็บประวัติทุกรอบการอนุญาตไว้ครบ
_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
_current_log_path: str | None = None

# จำโฟลเดอร์ที่อนุญาตไว้ข้าม restart — เก็บ path ลงไฟล์ config เล็กๆ (อยู่ใน .gitignore เพราะเป็น
# absolute path เฉพาะเครื่องของผู้ใช้ ไม่ใช่ค่าที่ควร commit) พอ server เริ่มใหม่แล้ว import module นี้
# จะอ่านกลับมาให้เอง ถ้าโฟลเดอร์นั้นยังมีอยู่จริง — ไม่ต้องกดปุ่มเลือกโฟลเดอร์ใหม่ทุกครั้งที่ restart
_FILE_ACCESS_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "file_access_config.json")


def _persist_allowed_folder(path: str | None) -> None:
    try:
        with open(_FILE_ACCESS_CONFIG, "w", encoding="utf-8") as f:
            json.dump({"allowed_folder": path}, f, ensure_ascii=False, indent=2)
    except OSError:
        pass  # เขียน config ไม่ได้ก็แค่ไม่จำข้าม restart ไม่ควรทำให้ feature หลักพังตาม


def _start_new_activity_log(folder: str, action: str = "folder_selected") -> None:
    global _current_log_path
    os.makedirs(_LOG_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    _current_log_path = os.path.join(_LOG_DIR, f"file_activity_{ts}.json")
    _write_log_entries([
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "action": action,
            "path": folder,
            "success": True,
            "detail": None,
        }
    ])


def _write_log_entries(entries: list[dict]) -> None:
    if not _current_log_path:
        return
    try:
        with open(_current_log_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
    except OSError:
        pass  # log เขียนไม่ได้ก็ไม่ควรทำให้ tool หลักพังตาม แค่เสียประวัติไปบรรทัดนั้น


def _log_activity(action: str, path: str, success: bool, detail: str | None = None) -> None:
    if not _current_log_path:
        return
    try:
        with open(_current_log_path, "r", encoding="utf-8") as f:
            entries = json.load(f)
    except (OSError, json.JSONDecodeError):
        entries = []
    entries.append(
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "action": action,
            "path": path,
            "success": success,
            "detail": detail,
        }
    )
    _write_log_entries(entries)


def set_allowed_folder(path: str) -> None:
    """เรียกจาก server.py หลังผู้ใช้เลือกโฟลเดอร์ผ่าน native folder picker ใน UI — เริ่ม log กิจกรรม
    รอบใหม่ทุกครั้งที่เรียก (ไฟล์ log เดิมของรอบก่อนหน้ายังอยู่ครบ ไม่ได้ถูกลบ) และจำ path ไว้ข้าม
    restart ผ่านไฟล์ config"""
    global _allowed_folder
    _allowed_folder = path
    _persist_allowed_folder(path)
    _start_new_activity_log(path)


def get_allowed_folder() -> str | None:
    return _allowed_folder


def _resolve_safe_path(subpath: str) -> tuple[bool, str]:
    """resolve subpath เทียบกับ _allowed_folder แล้วเช็คว่ายังอยู่ในขอบเขตจริง คืน (ปลอดภัยไหม, path เต็ม)"""
    if not _allowed_folder:
        return False, ""
    subpath = (subpath or "").strip().lstrip("/\\")
    try:
        allowed_root = os.path.realpath(_allowed_folder)
        target = os.path.realpath(os.path.join(allowed_root, subpath))
        common = os.path.commonpath([allowed_root, target])
    except (ValueError, OSError):
        # ValueError: คนละ drive กันบน Windows (เช่น C:\ vs D:\) ก็ถือว่าไม่ปลอดภัยเลย
        return False, ""
    return common == allowed_root, target


def list_files(subpath: str = "") -> str:
    """แสดงรายชื่อไฟล์/โฟลเดอร์ในโฟลเดอร์ที่ผู้ใช้อนุญาตให้ จัสมิน เข้าถึงได้เท่านั้น (ตั้งค่าจากปุ่ม
    เลือกโฟลเดอร์ในหน้าเว็บ) ใช้เมื่อผู้ใช้ขอให้ดูว่ามีไฟล์อะไรบ้าง หรือหาไฟล์ในโฟลเดอร์ที่อนุญาตไว้

    Args:
        subpath: โฟลเดอร์ย่อยที่จะดู (ปล่อยว่างไว้ถ้าจะดูโฟลเดอร์หลักที่อนุญาตไว้เลย)

    Returns:
        รายชื่อไฟล์และโฟลเดอร์ย่อย
    """
    if not _allowed_folder:
        return "ยังไม่ได้ตั้งค่าโฟลเดอร์ที่อนุญาตให้เข้าถึงเลยค่ะ กดปุ่ม 📁 เลือกโฟลเดอร์ มุมขวาบนของหน้าเว็บก่อนนะคะ"

    ok, target = _resolve_safe_path(subpath)
    if not ok:
        _log_activity("list_files", subpath, False, "outside allowed scope")
        return "ไม่สามารถเข้าถึงโฟลเดอร์นี้ได้ค่ะ อยู่นอกขอบเขตที่อนุญาตไว้"
    if not os.path.isdir(target):
        return f'"{subpath}" ไม่ใช่โฟลเดอร์ค่ะ'

    try:
        entries = sorted(os.listdir(target))
    except OSError:
        _log_activity("list_files", subpath, False, "OSError listing directory")
        return "เปิดโฟลเดอร์นี้ไม่สำเร็จค่ะ"

    _log_activity("list_files", subpath, True)
    if not entries:
        return "โฟลเดอร์นี้ว่างเปล่าค่ะ"

    lines = []
    for name in entries[:200]:  # กันโฟลเดอร์ที่มีไฟล์เยอะมากจนตอบยาวเกินไป
        full = os.path.join(target, name)
        if os.path.isdir(full):
            lines.append(f"[โฟลเดอร์] {name}")
        else:
            try:
                size_kb = os.path.getsize(full) / 1024
                lines.append(f"[ไฟล์] {name} ({size_kb:.0f} KB)")
            except OSError:
                lines.append(f"[ไฟล์] {name}")
    return "\n".join(lines)


def read_file(path: str) -> str:
    """อ่านเนื้อหาไฟล์ข้อความ — จำกัดแค่ไฟล์ในโฟลเดอร์ที่ผู้ใช้อนุญาตให้ จัสมิน เข้าถึงได้เท่านั้น
    (ตั้งค่าจากปุ่มเลือกโฟลเดอร์ในหน้าเว็บ) ใช้เมื่อผู้ใช้ขอให้อ่าน/สรุปเนื้อหาไฟล์ในโฟลเดอร์ที่อนุญาตไว้
    รองรับเฉพาะไฟล์ข้อความเท่านั้น (.txt, .md, .csv, .json, .py ฯลฯ) ไม่รองรับรูปภาพ/วิดีโอ/ไฟล์ไบนารี

    Args:
        path: path ของไฟล์ นับจากโฟลเดอร์ที่อนุญาตไว้ (เช่น "notes.txt" หรือ "sub/data.csv")

    Returns:
        เนื้อหาไฟล์ (ตัดถ้ายาวเกินไป)
    """
    if not _allowed_folder:
        return "ยังไม่ได้ตั้งค่าโฟลเดอร์ที่อนุญาตให้เข้าถึงเลยค่ะ กดปุ่ม 📁 เลือกโฟลเดอร์ มุมขวาบนของหน้าเว็บก่อนนะคะ"

    ok, target = _resolve_safe_path(path)
    if not ok:
        _log_activity("read_file", path, False, "outside allowed scope")
        return "ไม่สามารถเข้าถึงไฟล์นี้ได้ค่ะ อยู่นอกขอบเขตที่อนุญาตไว้"
    if not os.path.isfile(target):
        return f'ไม่พบไฟล์ "{path}" ค่ะ'

    ext = os.path.splitext(target)[1].lower()
    if ext not in _ALLOWED_TEXT_EXTENSIONS:
        _log_activity("read_file", path, False, f"disallowed extension {ext}")
        return f"ไฟล์นามสกุล {ext or '(ไม่มีนามสกุล)'} นี้อ่านไม่ได้ค่ะ รองรับแค่ไฟล์ข้อความ (.txt, .md, .csv, .json, .py ฯลฯ)"

    try:
        size = os.path.getsize(target)
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(_MAX_FILE_READ_BYTES)
    except OSError:
        _log_activity("read_file", path, False, "OSError reading file")
        return "อ่านไฟล์นี้ไม่สำเร็จค่ะ"

    _log_activity("read_file", path, True)
    if size > _MAX_FILE_READ_BYTES:
        content += "\n\n...(เนื้อหายาวเกินไป ตัดไว้แค่นี้ค่ะ)"
    return content


def create_folder(path: str) -> str:
    """สร้างโฟลเดอร์ใหม่ (รวมถึงโฟลเดอร์แม่ที่ยังไม่มีด้วย) — จำกัดแค่ในโฟลเดอร์ที่ผู้ใช้อนุญาตให้
    จัสมิน เข้าถึงได้เท่านั้น ใช้เมื่อผู้ใช้ขอให้สร้างโฟลเดอร์ใหม่

    Args:
        path: path ของโฟลเดอร์ใหม่ นับจากโฟลเดอร์ที่อนุญาตไว้ (เช่น "งาน/โปรเจกต์ใหม่")

    Returns:
        ข้อความยืนยันสั้นๆ
    """
    if not _allowed_folder:
        return "ยังไม่ได้ตั้งค่าโฟลเดอร์ที่อนุญาตให้เข้าถึงเลยค่ะ กดปุ่ม 📁 เลือกโฟลเดอร์ มุมขวาบนของหน้าเว็บก่อนนะคะ"

    ok, target = _resolve_safe_path(path)
    if not ok:
        _log_activity("create_folder", path, False, "outside allowed scope")
        return "ไม่สามารถสร้างโฟลเดอร์นี้ได้ค่ะ อยู่นอกขอบเขตที่อนุญาตไว้"

    try:
        os.makedirs(target, exist_ok=True)
    except OSError:
        _log_activity("create_folder", path, False, "OSError creating directory")
        return "สร้างโฟลเดอร์นี้ไม่สำเร็จค่ะ"

    _log_activity("create_folder", path, True)
    return f'สร้างโฟลเดอร์ "{path}" ให้แล้วค่ะ'


def write_file(path: str, content: str) -> str:
    """สร้างไฟล์ข้อความใหม่ หรือแก้ไข (เขียนทับทั้งไฟล์) ไฟล์ที่มีอยู่แล้ว — จำกัดแค่ในโฟลเดอร์ที่
    ผู้ใช้อนุญาตให้ จัสมิน เข้าถึงได้เท่านั้น ใช้เมื่อผู้ใช้ขอให้สร้างไฟล์ใหม่หรือแก้ไขเนื้อหาไฟล์เดิม
    ถ้าจะแก้ไขไฟล์ที่มีอยู่แล้ว ให้เรียก read_file() อ่านเนื้อหาเดิมมาก่อนเสมอ แล้วค่อยส่งเนื้อหาฉบับ
    เต็มที่แก้ไขแล้วมาที่นี่ (tool นี้เขียนทับทั้งไฟล์เสมอ ไม่ใช่แค่ต่อท้ายหรือแก้บางส่วน) รองรับเฉพาะ
    ไฟล์ข้อความเท่านั้น

    Args:
        path: path ของไฟล์ นับจากโฟลเดอร์ที่อนุญาตไว้ (เช่น "notes.txt")
        content: เนื้อหาทั้งหมดของไฟล์ที่ต้องการให้เป็นหลังบันทึก

    Returns:
        ข้อความยืนยันสั้นๆ
    """
    if not _allowed_folder:
        return "ยังไม่ได้ตั้งค่าโฟลเดอร์ที่อนุญาตให้เข้าถึงเลยค่ะ กดปุ่ม 📁 เลือกโฟลเดอร์ มุมขวาบนของหน้าเว็บก่อนนะคะ"

    ok, target = _resolve_safe_path(path)
    if not ok:
        _log_activity("write_file", path, False, "outside allowed scope")
        return "ไม่สามารถเขียนไฟล์นี้ได้ค่ะ อยู่นอกขอบเขตที่อนุญาตไว้"

    ext = os.path.splitext(target)[1].lower()
    if ext not in _ALLOWED_TEXT_EXTENSIONS:
        _log_activity("write_file", path, False, f"disallowed extension {ext}")
        return f"ไฟล์นามสกุล {ext or '(ไม่มีนามสกุล)'} นี้เขียนไม่ได้ค่ะ รองรับแค่ไฟล์ข้อความ (.txt, .md, .csv, .json, .py ฯลฯ)"

    existed = os.path.isfile(target)
    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
    except OSError:
        _log_activity("write_file", path, False, "OSError writing file")
        return "เขียนไฟล์นี้ไม่สำเร็จค่ะ"

    _log_activity("write_file", path, True, "overwritten" if existed else "created")
    return f'{"แก้ไข" if existed else "สร้าง"}ไฟล์ "{path}" ให้แล้วค่ะ'


def delete_path(path: str) -> str:
    """ลบไฟล์หรือโฟลเดอร์ (ถ้าเป็นโฟลเดอร์จะลบของข้างในทั้งหมดด้วย) — จำกัดแค่ในโฟลเดอร์ที่ผู้ใช้
    อนุญาตให้ จัสมิน เข้าถึงได้เท่านั้น ใช้เมื่อผู้ใช้ขอให้ลบไฟล์/โฟลเดอร์ **อย่างชัดเจนเท่านั้น**
    การกระทำนี้ลบถาวร กู้คืนไม่ได้ — ห้ามเรียกเองถ้าไม่แน่ใจว่าผู้ใช้ต้องการลบจริงๆ ให้ถามยืนยันก่อน
    ถ้าคำสั่งของผู้ใช้ดูกำกวมหรือไม่ชัดเจนว่าจะลบอะไรแน่

    Args:
        path: path ของไฟล์หรือโฟลเดอร์ที่จะลบ นับจากโฟลเดอร์ที่อนุญาตไว้

    Returns:
        ข้อความยืนยันสั้นๆ
    """
    if not _allowed_folder:
        return "ยังไม่ได้ตั้งค่าโฟลเดอร์ที่อนุญาตให้เข้าถึงเลยค่ะ กดปุ่ม 📁 เลือกโฟลเดอร์ มุมขวาบนของหน้าเว็บก่อนนะคะ"

    ok, target = _resolve_safe_path(path)
    if not ok:
        _log_activity("delete_path", path, False, "outside allowed scope")
        return "ไม่สามารถลบสิ่งนี้ได้ค่ะ อยู่นอกขอบเขตที่อนุญาตไว้"

    # กันลบโฟลเดอร์หลักที่อนุญาตไว้ทั้งก้อนโดยไม่ตั้งใจ (path ว่าง/"." resolve กลับมาเป็น allowed_root เป๊ะ)
    if target == os.path.realpath(_allowed_folder):
        _log_activity("delete_path", path, False, "refused: target is the allowed root folder itself")
        return "ลบโฟลเดอร์หลักที่อนุญาตไว้ทั้งก้อนไม่ได้ค่ะ ต้องระบุไฟล์/โฟลเดอร์ย่อยข้างในแทนนะคะ"

    if not os.path.exists(target):
        return f'ไม่พบ "{path}" ค่ะ'

    try:
        if os.path.isdir(target):
            shutil.rmtree(target)
        else:
            os.remove(target)
    except OSError:
        _log_activity("delete_path", path, False, "OSError deleting")
        return "ลบไม่สำเร็จค่ะ"

    _log_activity("delete_path", path, True)
    return f'ลบ "{path}" ให้แล้วค่ะ'


def _restore_allowed_folder_from_config() -> None:
    """เรียกครั้งเดียวตอน import module (ตอน server เริ่ม) — คืนค่าโฟลเดอร์ที่เคยเลือกไว้รอบก่อน ถ้า
    ยังมีอยู่จริง แล้วเปิด activity log ไฟล์ใหม่ของรอบนี้ (action="folder_restored") ให้ audit trail
    ของแต่ละรอบการรัน server แยกไฟล์กันชัดเจน ถ้าโฟลเดอร์ถูกลบ/ย้าย/ถอด drive ไปแล้วก็ข้ามไปเงียบๆ
    (ผู้ใช้กดเลือกใหม่ผ่านปุ่ม 📁 ได้)"""
    global _allowed_folder
    try:
        with open(_FILE_ACCESS_CONFIG, "r", encoding="utf-8") as f:
            saved = json.load(f).get("allowed_folder")
    except (OSError, json.JSONDecodeError):
        return
    if isinstance(saved, str) and os.path.isdir(saved):
        _allowed_folder = saved
        _start_new_activity_log(saved, action="folder_restored")


_restore_allowed_folder_from_config()
