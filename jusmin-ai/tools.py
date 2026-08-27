import json
import os
import shutil
from datetime import datetime, timedelta

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


# ทิศลม 8 ทิศ (Open-Meteo คืน wind_direction_10m เป็นองศา 0-360 = ทิศที่ลม "พัดมาจาก")
_WIND_DIRS = (
    "เหนือ", "ตะวันออกเฉียงเหนือ", "ตะวันออก", "ตะวันออกเฉียงใต้",
    "ใต้", "ตะวันตกเฉียงใต้", "ตะวันตก", "ตะวันตกเฉียงเหนือ",
)


def _wind_dir_label(deg):
    if deg is None:
        return None
    return _WIND_DIRS[round(deg / 45) % 8]


def _uv_label(uv):
    if uv is None:
        return None
    if uv < 3:
        return "ต่ำ"
    if uv < 6:
        return "ปานกลาง"
    if uv < 8:
        return "สูง"
    if uv < 11:
        return "สูงมาก"
    return "อันตราย"


# --- "โฟกัส" ของการ์ดอากาศ: LLM เลือกตามชนิดคำถาม แล้ว UI ปรับ layout + ข้อความตอบให้ตรงคำถาม ---
# ทุกโฟกัสยิง Open-Meteo ก้อนเดียวกัน (1 request) แค่หยิบ/สรุปคนละมุม
_FOCUS_ALIASES = {
    "": "now", "now": "now", "current": "now", "general": "now", "overview": "now", "summary": "now",
    "rain": "rain", "precip": "rain", "precipitation": "rain", "umbrella": "rain", "shower": "rain",
    "temp": "temperature", "temperature": "temperature", "heat": "temperature", "cold": "temperature", "hot": "temperature",
    "wind": "wind", "gust": "wind",
    "uv": "uv", "sunscreen": "uv", "sun_strength": "uv", "sunburn": "uv",
    "sun": "sun", "sunrise": "sun", "sunset": "sun", "daylight": "sun", "golden_hour": "sun",
    "forecast": "forecast", "week": "forecast", "days": "forecast", "multiday": "forecast", "weekly": "forecast",
}

_THAI_WEEKDAYS = ("จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์")
_THAI_MONTHS_ABBR = (
    "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.",
)
_RAIN_PROB_THRESHOLD = 45  # % ขึ้นไปถือว่า "ช่วงนี้มีฝน" ตอนหาช่วงเวลาฝนตก


def _day_label(date_str, day):
    if day == 0:
        return "วันนี้"
    if day == 1:
        return "พรุ่งนี้"
    if day == 2:
        return "มะรืนนี้"
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return f"วัน{_THAI_WEEKDAYS[d.weekday()]}ที่ {d.day} {_THAI_MONTHS_ABBR[d.month - 1]}"
    except (ValueError, TypeError):
        return f"อีก {day} วัน"


def _plus_hour(hhmm):
    try:
        h, m = hhmm.split(":")
        return f"{(int(h) + 1) % 24:02d}:{m}"
    except (ValueError, AttributeError):
        return hhmm


def _day_hour_indices(h_times, day, now_prefix):
    """คืน index ของ hourly array ที่อยู่ในวัน day (0=วันนี้..6) — วันนี้เอาเฉพาะตั้งแต่ชั่วโมงปัจจุบันไป"""
    if not h_times:
        return []
    today = (now_prefix[:10] or h_times[0][:10])
    try:
        target = (datetime.strptime(today, "%Y-%m-%d") + timedelta(days=day)).strftime("%Y-%m-%d")
    except ValueError:
        return []
    idxs = [i for i, t in enumerate(h_times) if t[:10] == target]
    if day == 0:
        idxs = [i for i in idxs if h_times[i][:13] >= now_prefix]
    return idxs


def _rain_windows(labels, probs, threshold=_RAIN_PROB_THRESHOLD):
    """หาช่วงเวลาต่อเนื่องที่ prob >= threshold — คืน list ของ {start,end,peak,peak_time} (end = ชั่วโมงสุดท้ายที่ยังเปียก + 1)"""
    windows = []
    cur = None
    for lb, p in zip(labels, probs):
        wet = p is not None and p >= threshold
        if wet:
            if cur is None:
                cur = {"start": lb, "end": lb, "peak": p, "peak_time": lb}
            else:
                cur["end"] = lb
                if p > cur["peak"]:
                    cur["peak"], cur["peak_time"] = p, lb
        elif cur is not None:
            windows.append(cur)
            cur = None
    if cur is not None:
        windows.append(cur)
    for w in windows:
        w["end"] = _plus_hour(w["end"])
    return windows


def _extremum(labels, values, want_max=True):
    """คืน (value, label) ของค่ามาก/น้อยสุดในซีรีส์ ข้าม None"""
    best_v, best_l = None, None
    for lb, v in zip(labels, values):
        if v is None:
            continue
        if best_v is None or (v > best_v if want_max else v < best_v):
            best_v, best_l = v, lb
    return best_v, best_l


def _build_weather_reply(lat, lon, display_name: str, focus: str = "now", day: int = 0) -> str:
    """ยิง forecast API ด้วยพิกัดที่ได้มา แล้วประกอบทั้งข้อความตอบ + _pending_action สำหรับ UI —
    แยกออกมาเป็นฟังก์ชันต่างหากเพราะพิกัดมาได้ 2 ทาง: geocoding จากชื่อสถานที่ที่ผู้ใช้บอก หรือ
    navigator.geolocation ของเบราว์เซอร์ (ตอนผู้ใช้ถามอากาศ 'ที่นี่' โดยไม่ระบุชื่อเมือง)

    focus = มุมที่ผู้ใช้ถาม (now/rain/temperature/wind/uv/sun/forecast) -> UI ปรับ layout + ข้อความตอบให้ตรง
    day  = 0 วันนี้ .. 6 (ใช้กับ focus ที่ระบุวันได้ เช่น "ฝนพรุ่งนี้ตกช่วงไหน")"""
    global _pending_action
    view = _FOCUS_ALIASES.get((focus or "").strip().lower(), "now")
    try:
        day = max(0, min(6, int(day)))
    except (TypeError, ValueError):
        day = 0
    try:
        wx_resp = requests.get(
            _FORECAST_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": (
                    "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,"
                    "wind_speed_10m,wind_direction_10m,wind_gusts_10m,is_day"
                ),
                "hourly": (
                    "temperature_2m,apparent_temperature,precipitation,precipitation_probability,"
                    "weather_code,wind_speed_10m,wind_gusts_10m,uv_index"
                ),
                "daily": (
                    "weather_code,temperature_2m_max,temperature_2m_min,"
                    "precipitation_probability_max,sunrise,sunset,uv_index_max"
                ),
                "timezone": "auto",
                "forecast_days": 7,
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
    wind_dir = current.get("wind_direction_10m")
    wind_gusts = current.get("wind_gusts_10m")
    condition_text, emoji, fx = _describe_weather_code(current.get("weather_code"))
    is_day = bool(current.get("is_day", 1))

    daily = wx.get("daily") or {}
    dates = daily.get("time") or []
    codes = daily.get("weather_code") or []
    highs = daily.get("temperature_2m_max") or []
    lows = daily.get("temperature_2m_min") or []
    pops = daily.get("precipitation_probability_max") or []
    sunrises = daily.get("sunrise") or []
    sunsets = daily.get("sunset") or []
    uvs = daily.get("uv_index_max") or []
    forecast = []
    for i in range(min(len(dates), 7)):
        day_condition, day_emoji, _day_fx = _describe_weather_code(codes[i]) if i < len(codes) else _DEFAULT_WEATHER_DESC
        forecast.append(
            {
                "date": dates[i],
                "max": round(highs[i]) if i < len(highs) and highs[i] is not None else None,
                "min": round(lows[i]) if i < len(lows) and lows[i] is not None else None,
                "precip": pops[i] if i < len(pops) and pops[i] is not None else None,
                "condition": day_condition,
                "emoji": day_emoji,
            }
        )

    # ข้อมูลรายชั่วโมง (hourly time เป็นเวลาท้องถิ่นเพราะ timezone=auto) — array เต็ม 7 วัน หยิบช่วงตาม focus/day
    hourly = wx.get("hourly") or {}
    h_times = hourly.get("time") or []
    h_temps = hourly.get("temperature_2m") or []
    h_app = hourly.get("apparent_temperature") or []
    h_precip = hourly.get("precipitation") or []
    h_pops = hourly.get("precipitation_probability") or []
    h_codes = hourly.get("weather_code") or []
    h_wspd = hourly.get("wind_speed_10m") or []
    h_wgust = hourly.get("wind_gusts_10m") or []
    h_uv = hourly.get("uv_index") or []
    now_prefix = (current.get("time") or "")[:13]  # "YYYY-MM-DDTHH" — ISO เทียบ string ได้ = เรียงตามเวลา
    start = next((i for i, t in enumerate(h_times) if t[:13] >= now_prefix), 0)
    hourly_out = []
    for i in range(start, min(start + 12, len(h_times))):
        _hc, h_emoji, _hfx = _describe_weather_code(h_codes[i]) if i < len(h_codes) else _DEFAULT_WEATHER_DESC
        hourly_out.append(
            {
                "time": h_times[i][11:16],  # "14:00"
                "temp": round(h_temps[i]) if i < len(h_temps) and h_temps[i] is not None else None,
                "precip": h_pops[i] if i < len(h_pops) and h_pops[i] is not None else None,
                "emoji": h_emoji,
            }
        )

    sunrise = sunrises[0][11:16] if sunrises and isinstance(sunrises[0], str) else None
    sunset = sunsets[0][11:16] if sunsets and isinstance(sunsets[0], str) else None
    uv_today = uvs[0] if uvs and uvs[0] is not None else None
    precip_today = pops[0] if pops and pops[0] is not None else None

    day_date = dates[day] if day < len(dates) else (dates[0] if dates else "")
    day_label = _day_label(day_date, day)

    # header + payload "ตอนนี้" ที่ทุก view ใช้ร่วมกัน (การ์ดโชว์หัวเสมอ) แล้วค่อยเติมบล็อกเฉพาะ view
    data = {
        "view": view,
        "day": day,
        "day_label": day_label,
        "location": display_name,
        "temperature": round(temp) if temp is not None else None,
        "feels_like": round(feels_like) if feels_like is not None else None,
        "humidity": humidity,
        "wind_speed": wind,
        "wind_direction": wind_dir,
        "wind_direction_label": _wind_dir_label(wind_dir),
        "wind_gusts": round(wind_gusts) if wind_gusts is not None else None,
        "condition": condition_text,
        "emoji": emoji,
        "fx": fx,
        "is_day": is_day,
        "sunrise": sunrise,
        "sunset": sunset,
        "uv_index": round(uv_today, 1) if uv_today is not None else None,
        "uv_label": _uv_label(uv_today),
        "precip_today": precip_today,
        "hourly": hourly_out,
        "forecast": forecast,
    }

    idxs = _day_hour_indices(h_times, day, now_prefix)
    labels = [h_times[i][11:16] for i in idxs]

    def _val(arr, i, nd=None):
        v = arr[i] if i < len(arr) else None
        if v is None:
            return None
        return round(v, nd) if nd is not None else round(v)

    if view == "rain":
        series = [
            {"time": h_times[i][11:16], "prob": _val(h_pops, i) if i < len(h_pops) else None,
             "mm": round(h_precip[i], 1) if i < len(h_precip) and h_precip[i] is not None else None}
            for i in idxs
        ]
        probs = [s["prob"] for s in series]
        windows = _rain_windows(labels, probs)
        max_prob, max_prob_time = _extremum(labels, probs, want_max=True)
        data["rain_series"] = series
        data["rain_windows"] = windows
        data["rain_max_prob"] = max_prob
        if windows:
            parts = [
                f"{w['start']}–{w['end']} น. (โอกาสสูงสุด {w['peak']}% ตอน {w['peak_time']})"
                for w in windows
            ]
            data["headline"] = "ฝน " + " · ".join(f"{w['start']}–{w['end']}" for w in windows)
            reply = f"{day_label}น่าจะมีฝนช่วง " + " และ ".join(parts) + " ค่ะ นอกช่วงนั้นน่าจะแห้ง"
        elif max_prob is not None and max_prob >= 20:
            data["headline"] = f"ฝนโอกาสต่ำ · สูงสุด {max_prob}%"
            reply = f"{day_label}โอกาสมีฝนไม่มากค่ะ สูงสุดแค่ {max_prob}% ตอน {max_prob_time} ยังไม่ต้องพกร่มก็ได้"
        else:
            data["headline"] = "แทบไม่มีฝน"
            reply = f"{day_label}แทบไม่มีโอกาสฝนเลยค่ะ ท้องฟ้าน่าจะแห้งทั้งวัน"

    elif view == "temperature":
        series = [
            {"time": h_times[i][11:16], "temp": _val(h_temps, i),
             "feels": _val(h_app, i) if i < len(h_app) else None}
            for i in idxs
        ]
        temps = [s["temp"] for s in series]
        tmax, tmax_t = _extremum(labels, temps, want_max=True)
        tmin, tmin_t = _extremum(labels, temps, want_max=False)
        data["temp_series"] = series
        data["temp_max"], data["temp_max_time"] = tmax, tmax_t
        data["temp_min"], data["temp_min_time"] = tmin, tmin_t
        if tmax is not None:
            data["headline"] = f"{tmin}–{tmax}° · ร้อนสุด {tmax_t}"
            now_part = f"ตอนนี้ {round(temp)}° " if day == 0 and temp is not None else ""
            reply = (
                f"{now_part}{day_label}อุณหภูมิราว {tmin}–{tmax}°C ค่ะ ร้อนสุด {tmax}° ตอน {tmax_t} "
                f"เย็นสุด {tmin}° ตอน {tmin_t}"
            )
        else:
            data["headline"] = "ไม่มีข้อมูลรายชั่วโมง"
            reply = f"ยังไม่มีข้อมูลอุณหภูมิรายชั่วโมงของ{day_label}ค่ะ"

    elif view == "wind":
        series = [
            {"time": h_times[i][11:16], "speed": _val(h_wspd, i) if i < len(h_wspd) else None,
             "gust": _val(h_wgust, i) if i < len(h_wgust) else None}
            for i in idxs
        ]
        gmax, gmax_t = _extremum(labels, [s["gust"] for s in series], want_max=True)
        data["wind_series"] = series
        data["wind_gust_max"], data["wind_gust_max_time"] = gmax, gmax_t
        data["headline"] = f"{round(wind)} กม./ชม." + (f" · กระโชก {gmax}" if gmax is not None else "")
        when = "ตอนนี้" if day == 0 else day_label
        bits = [f"ลม{when} {round(wind)} กม./ชม."]
        if wind_dir is not None:
            bits.append(f"จากทิศ{_wind_dir_label(wind_dir)}")
        if gmax is not None:
            bits.append(f"กระโชกได้ถึง {gmax} กม./ชม. ตอน {gmax_t}")
        reply = " ".join(bits) + " ค่ะ"

    elif view == "uv":
        series = [
            {"time": h_times[i][11:16], "uv": _val(h_uv, i, 1) if i < len(h_uv) else None}
            for i in idxs
        ]
        uvmax, uvmax_t = _extremum(labels, [s["uv"] for s in series], want_max=True)
        if uvmax is None:
            uvmax = uvs[day] if day < len(uvs) and uvs[day] is not None else uv_today
        lbl = _uv_label(uvmax)
        data["uv_series"] = series
        data["uv_max"], data["uv_max_time"], data["uv_max_label"] = (
            round(uvmax, 1) if uvmax is not None else None, uvmax_t, lbl,
        )
        if uvmax is not None:
            data["headline"] = f"UV สูงสุด {round(uvmax, 1)} ({lbl})" + (f" · {uvmax_t}" if uvmax_t else "")
            advice = " ควรทาครีมกันแดดและหลบแดดช่วงเที่ยง" if uvmax >= 6 else " ไม่แรงมาก ทากันแดดบางๆ ก็พอ"
            at = f" ช่วง {uvmax_t}" if uvmax_t else ""
            reply = f"{day_label} UV สูงสุดราว {round(uvmax, 1)} ({lbl}){at} ค่ะ{advice}"
        else:
            data["headline"] = "ไม่มีข้อมูล UV"
            reply = f"ยังไม่มีข้อมูล UV ของ{day_label}ค่ะ"

    elif view == "sun":
        sr = sunrises[day][11:16] if day < len(sunrises) and isinstance(sunrises[day], str) else None
        ss = sunsets[day][11:16] if day < len(sunsets) and isinstance(sunsets[day], str) else None
        dl_h = dl_m = None
        try:
            d1 = datetime.fromisoformat(sunrises[day])
            d2 = datetime.fromisoformat(sunsets[day])
            total_m = int((d2 - d1).total_seconds() // 60)
            dl_h, dl_m = divmod(total_m, 60)
        except (ValueError, IndexError, TypeError):
            pass
        data["sun_sunrise"], data["sun_sunset"] = sr, ss
        data["day_length_h"], data["day_length_m"] = dl_h, dl_m
        data["sun_next"] = [
            {"date": dates[i], "label": _day_label(dates[i], i),
             "sunrise": sunrises[i][11:16] if i < len(sunrises) and isinstance(sunrises[i], str) else None,
             "sunset": sunsets[i][11:16] if i < len(sunsets) and isinstance(sunsets[i], str) else None}
            for i in range(min(len(dates), 5))
        ]
        dl_part = f" กลางวันยาว {dl_h} ชั่วโมง {dl_m} นาที" if dl_h is not None else ""
        data["headline"] = f"ขึ้น {sr} · ตก {ss}" + (f" · {dl_h}ชม {dl_m}น" if dl_h is not None else "")
        reply = f"{day_label}พระอาทิตย์ขึ้น {sr} น. ตก {ss} น.{dl_part} ค่ะ"

    elif view == "forecast":
        data["headline"] = f"พยากรณ์ 7 วันข้างหน้า · {display_name}"
        bits = []
        for f in forecast:
            wd = _day_label(f["date"], 0)
            try:
                wd = "วัน" + _THAI_WEEKDAYS[datetime.strptime(f["date"], "%Y-%m-%d").weekday()]
            except ValueError:
                pass
            rp = f" ฝน {f['precip']}%" if f.get("precip") else ""
            bits.append(f"{wd} {f['emoji']} {f['min']}-{f['max']}°{rp}")
        reply = f"พยากรณ์ 7 วันข้างหน้าที่{display_name}: " + " / ".join(bits)

    else:  # "now"
        rain_part = f" โอกาสมีฝนวันนี้ {precip_today}%" if precip_today is not None else ""
        reply = (
            f"ตอนนี้ที่{display_name} {condition_text} {emoji} อุณหภูมิ {round(temp) if temp is not None else '-'}"
            f"°C (รู้สึกเหมือน {round(feels_like) if feels_like is not None else '-'}°C) "
            f"ความชื้น {humidity}% ลมแรง {wind} กม./ชม.{rain_part}ค่ะ"
        )

    _pending_action = {"type": "show_weather", "data": data}
    return reply


def get_weather(location: str = "", focus: str = "", day: int = 0) -> str:
    """เช็คสภาพอากาศจริง (Open-Meteo) แล้ว **ปรับการ์ด UI + คำตอบให้ตรงกับสิ่งที่ผู้ใช้ถาม** ใช้เมื่อผู้ใช้
    ถามเรื่องอากาศ/อุณหภูมิ/ฝน/ลม/แดด/พระอาทิตย์ขึ้น-ตก/พยากรณ์หลายวัน ทุกกรณี

    Args:
        location: ชื่อสถานที่ (จังหวัด/เมือง/ประเทศ ไทยหรืออังกฤษ) — **ถ้าผู้ใช้ถามอากาศ "ที่นี่" หรือ
            ไม่ได้ระบุสถานที่ ให้ปล่อยว่าง** ระบบจะใช้พิกัดจากเบราว์เซอร์อัตโนมัติ ไม่ต้องถามกลับ ยกเว้น
            tool ตอบว่าเข้าถึงตำแหน่งไม่ได้ ค่อยถาม
        focus: มุมที่ผู้ใช้ถาม — เลือกให้ตรงคำถาม:
            "now" (ค่าเริ่มต้น) = ถามอากาศตอนนี้/วันนี้ทั่วไป
            "rain" = ถามว่าฝนจะตกไหม/ตกช่วงไหน/ต้องพกร่มไหม/ตากผ้าได้ไหม
            "temperature" = ถามร้อน/หนาว/อุณหภูมิช่วงเช้า-บ่าย-กลางคืน
            "wind" = ถามลมแรงไหม/ลมทิศไหน/ลมกระโชก
            "uv" = ถามแดดแรงไหม/UV/ต้องทาครีมกันแดดไหม
            "sun" = ถามพระอาทิตย์ขึ้น-ตกกี่โมง/ฟ้าสว่าง-มืดกี่โมง/กลางวันยาวแค่ไหน
            "forecast" = ถามภาพรวมหลายวัน/สัปดาห์นี้/สุดสัปดาห์
        day: 0 = วันนี้, 1 = พรุ่งนี้, 2 = มะรืน ... สูงสุด 6 — ใส่ตามวันที่ผู้ใช้ถาม (ใช้กับ focus
            rain/temperature/wind/uv/sun) เช่น "พรุ่งนี้ฝนตกช่วงไหน" -> focus="rain", day=1

    Returns:
        คำตอบที่ตรงกับคำถาม (พูด/แชท) — เอาไปเรียบเรียงต่อได้
    """
    location = (location or "").strip()

    # ไม่ระบุสถานที่ หรือบอกว่า "ที่นี่"/"ปัจจุบัน" -> ใช้พิกัดจากเบราว์เซอร์ (server.py เซ็ตไว้ก่อนเรียก LLM)
    if location.lower() in _HERE_ALIASES:
        if _client_location:
            label = _client_location.get("label") or "ตำแหน่งปัจจุบัน"
            return _build_weather_reply(_client_location["lat"], _client_location["lon"], label, focus, day)
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

    return _build_weather_reply(lat, lon, display_name, focus, day)


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
