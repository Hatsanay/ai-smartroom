# จัสมิน — AI Assistant Project

> Context file สำหรับ Claude Code เอาไว้ปรับตัวให้เข้าใจเป้าหมายและขอบเขตของโปรเจกต์นี้

## เป้าหมาย

สร้าง AI agent สไตล์ Jarvis ชื่อ **จัสมิน** ที่:

- คุย / ตอบคำถาม / หาข้อมูลให้ได้
- สั่งควบคุมบ้าน (เปิด-ปิด TV, ไฟ, มอเตอร์, เครื่องเล่น) ผ่าน Home Assistant
- ต่อยอด tool อื่น ๆ เพิ่มทีหลังได้ (ปฏิทิน, memory, ค้นเว็บ ฯลฯ)

## สถาปัตยกรรม

เวลา AI agent ตอบคำถามหรือสั่งงาน ให้แยกบทบาทตามนี้:

- **สมอง (ยืดหยุ่น)** = LLM (Gemini) → คิดความหมาย + เลือก tool
- **มือ (เชื่อถือได้)** = Home Assistant → ลงมือคุมฮาร์ดแวร์จริงผ่าน REST API
- **Tool registry** = ชุดฟังก์ชันที่ agent เรียกใช้ได้ (control_home, search_web, memory, ...)

```
คุณ (เสียง/ข้อความ)
      │
┌─────────────────────────────┐
│   AI Agent (Python, บน Pi)   │  ← เขียนต่อ ณ จุดนี้เป็นหลัก
│  ┌─────────────────────────┐  │
│  │  Gemini (สมอง)          │  │  ← คิดความหมาย + เลือก tool
│  └─────────────────────────┘  │
│  ┌─────────────────────────┐  │
│  │  Tool Registry          │  │
│  │  • control_home()       │──┼──→ Home Assistant API → อุปกรณ์
│  │  • search_web()         │──┼──→ ค้นเว็บ
│  │  • remember()           │──┼──→ Memory (SQLite)
│  └─────────────────────────┘  │
└─────────────────────────────┘
```

**หลักการสำคัญ:** LLM ไม่แตะ GPIO เอง มันแค่เลือก tool และให้ argument ที่เหมาะสม แล้วโค้ดเราเป็นคนเรียก tool จริง — ตรงนี้คือจุดที่ใส่ safety check ได้

## Tech Stack

| ส่วน | เลือกใช้ | หมายเหตุ |
|------|---------|---------|
| ภาษา | **Python** | เหมาะกับ Pi + voice + hardware ที่สุด |
| LLM | **Gemini** (`gemini-3.5-flash-lite`) | มี free tier, ขอ key จาก AI Studio |
| SDK | `google-genai` | SDK ตัวใหม่ที่ Google ยัง maintain อยู่ (ตัวเก่า `google-generativeai` เลิกซัพพอร์ตแล้ว) |
| Web search | `ddgs` (DuckDuckGo) | ค้นเว็บฟรี ไม่ต้องขอ API key |
| ฟังเสียง (STT) | Web Speech API `SpeechRecognition` | ในตัวเบราว์เซอร์ ฟรี รองรับ Chrome/Edge เป็นหลัก |
| พูดตอบ (TTS) | `pythaitts` (engine `vachana`) รันฝั่ง server | เสียง Windows SAPI ฟังหุ่นยนต์เกินไป เปลี่ยนมาสร้างเสียงฝั่ง server แทน ดูรายละเอียดหัวข้อ "เสียงพูด TTS" ด้านล่าง |
| Smart Home | Home Assistant REST API | เป็น "มือ" คุมอุปกรณ์ |
| Memory | SQLite | เบา เหมาะกับ Pi |
| Config | `python-dotenv` | เก็บ secret ใน `.env` |

**หมายเหตุเรื่องชื่อรุ่น/โควตา:** Gemini เปลี่ยนชื่อรุ่นบ่อย ถ้า `gemini-3.5-flash-lite` ใช้ไม่ได้แล้ว ให้เช็กชื่อรุ่นล่าสุดจาก AI Studio — **สำคัญ:** รุ่น flagship อย่าง `gemini-3.6-flash` free tier ให้โควตาแค่ ~20 request/วัน (เจอ 429 RESOURCE_EXHAUSTED ตอนทดสอบ) ส่วนรุ่น `-flash-lite` มี quota pool แยกต่างหากที่สูงกว่ามาก เลยเลือกใช้ตัวนี้เป็นค่าเริ่มต้นแทน ถ้าเจอ error 429 อีกให้เช็ก quota ที่ https://ai.dev/rate-limit

## ฮาร์ดแวร์เป้าหมาย (Raspberry Pi)

รันทุกอย่างบน Pi ตัวเดียว 24/7 → ใช้ **จุดที่ทันสมัยของแต่ละองค์ประกอบ** (ในกรณีนี้ ย้ายไป Pi ที่แรงกว่าได้)

- Raspberry Pi 5 (8GB) — เผื่อ 8GB ไว้เพราะรัน HA + agent + DB พร้อมกัน
- Active Cooler — Pi 5 ร้อน ต้องระบายความร้อน
- NVMe SSD + M.2 HAT — อายุยาวกว่า SD และเร็วกว่า (เก็บ DB บ่อย ๆ ต้องทน)
- PSU 27W (5V/5A) ตัวจริง

## แผนการสร้าง (ทำทีละ Step)

- [x] **Step 0** — agent loop คุยกับ Gemini ได้เฉย ๆ (ยังไม่มี tool)
- [x] **เว็บ UI (Jarvis HUD)** — `server.py` (FastAPI) + `static/` หน้าเว็บ animation แบบ HUD วงกลม คุยกับ จัสมิน ผ่านเบราว์เซอร์ได้ พร้อม panel แสดงโควตา Gemini + คูลดาวน์แบบสด
- [x] **Step 1** — เพิ่ม tool แรก `search_web()` ผ่าน `ddgs` (DuckDuckGo, ฟรี ไม่ต้องขอ key)
  - **บั๊กจริงที่เจอตอนทดสอบครบทุกฟังก์ชัน**: `_ddgs.text()` (รุ่นที่ใช้อยู่) ยิง `DDGSException` ตอนไม่เจอผลลัพธ์/โดน rate-limit/timeout แทนที่จะคืน list ว่างตามที่โค้ดเดิมคาดไว้ (`if not results:` เลยเป็น dead code ที่ไม่เคยถูกเรียกถึง) — Gemini function calling เจอ exception ดิบแล้วรอดมาได้ (SDK จับเองแล้วบอกโมเดลว่า tool fail) แต่คำตอบจะกำกวมไม่ตรงประเด็น ("ระบบค้นหาขัดข้องชั่วคราว") ทั้งที่ query ไม่ได้ผิดอะไร — แก้โดยครอบ `try/except DDGSException` ใน `search_web()` คืนข้อความ graceful แทน
- [x] **Step 2** — เพิ่ม memory ถาวร (SQLite) ให้จำเรื่องเก่า-ใหม่ได้ข้ามเซสชัน — **ทำแล้ว** พร้อมกับกลุ่ม tool เลขาทั้งชุด (memory/tasks/reminders/email/briefing) ดูหัวข้อ "กลุ่ม tool เลขา" ด้านล่าง
- [ ] **Step 3** — ตั้ง Home Assistant + ESP32/รีเลย์ ให้คุมอุปกรณ์จริง
- [ ] **Step 4** — เพิ่ม `control_home()` เพื่อให้ agent เรียก HA สั่งอุปกรณ์ได้
- [ ] **Step 5** — ขยาย tool (คุม TV, เครื่องเล่น) ทีละอัน
- [x] **Step 6** — เสียงบนเว็บ: กดไมค์พูด (STT) + จัสมิน พูดตอบ (TTS) + **โหมดฟังตลอดพร้อม wake word "จัสมิน"** ทั้งหมดผ่าน Web Speech API ของเบราว์เซอร์ (ของเดิมที่วางแผนจะใช้ Whisper ยังไม่ได้ทำ เพราะย้ายมาทำเวอร์ชันเว็บก่อน)
- [x] **Tool: `open_youtube()` + `control_youtube()`** — ให้ จัสมิน ค้นหาแล้ว**เล่นเพลง/วิดีโอ YouTube อัตโนมัติจริง** (ไม่ใช่แค่เปิดหน้าค้นหา) พร้อมสั่งหยุด/เล่นต่อ/ปิด/เปลี่ยนเพลงด้วยเสียงได้
- [x] **Tool: `list_files()` + `read_file()`** — ให้ จัสมิน อ่านไฟล์ในคอมได้ **เฉพาะโฟลเดอร์ที่ผู้ใช้เลือกไว้เท่านั้น** (เลือกผ่านปุ่ม native folder picker บนหน้าเว็บ) รายละเอียด security/สถาปัตยกรรมดูหัวข้อ "เข้าถึงไฟล์ในคอม" ด้านล่าง
- [x] **Tool: `get_weather()`** — เช็คสภาพอากาศจริงผ่าน [Open-Meteo](https://open-meteo.com/) (ฟรี ไม่ต้องขอ API key เหมือน ddgs/yt-dlp) พร้อม UI การ์ดแสดงผล (ตำแหน่ง/อุณหภูมิ/รู้สึกเหมือน/ความชื้น/ลม+ทิศ/พระอาทิตย์ขึ้น-ตก/UV/โอกาสฝน/กราฟรายชั่วโมง/พยากรณ์ 7 วัน/animation) มุมขวากลางจอ (ล้อกับ `.yt-panel` ฝั่งซ้าย)
  - `_search_youtube`-style pattern เดิม: geocoding API (`geocoding-api.open-meteo.com/v1/search`) แปลงชื่อสถานที่เป็นพิกัดก่อน แล้วยิง forecast API (`api.open-meteo.com/v1/forecast`) ด้วยพิกัดนั้นอีกที ขอทั้ง current weather + พยากรณ์ 7 วันข้างหน้า (`forecast_days=7`) + hourly
  - แปลรหัสสภาพอากาศ WMO (มาตรฐานที่ Open-Meteo ใช้) เป็นคำอธิบายไทย + emoji + หมวด `fx` (สำหรับเลือก animation พื้นหลัง ดูด้านล่าง) ไว้ที่ `_WMO_WEATHER` dict ใน `tools.py` **คำนวณครั้งเดียวฝั่ง server** แล้วส่งค่าที่พร้อมแสดงผลไปให้ทั้งข้อความตอบ (พูด/แชท) และ `action.data` (สำหรับ UI) เลย — ตั้งใจไม่ทำ mapping ชุดเดียวกันซ้ำสองที่ (Python + JS) กัน mapping หลุดไม่ตรงกันในระยะยาว (ต่างจาก `_YT_VOLUME_STEP`/`YT_VOLUME_STEP` ที่จำเป็นต้อง sync มือเพราะเป็นค่าที่ทั้งสองฝั่งต้องใช้แยกกันจริงๆ)
  - `action.type = "show_weather"`, `action.data` มี `location`/`temperature`/`feels_like`/`humidity`/`wind_speed`/`condition`/`emoji`/`fx`/`is_day`/`forecast` — `app.js`'s `showWeather(data)` แค่เอาไปแปะแสดงผลตรงๆ ไม่มีเดา/เติมค่าเองเลย ตรงตามหลักการ "ห้ามใส่ panel ที่โชว์ข้อมูลปลอม"
  - **ขยาย UI สภาพอากาศ (ผู้ใช้ขอ) — ทุกค่าจาก Open-Meteo จริง อันไหนไม่มีข้อมูลก็ไม่โชว์ (ไม่เดา):**
    - request เพิ่ม: `current` +`wind_direction_10m,wind_gusts_10m`; `hourly=temperature_2m,precipitation_probability,weather_code`; `daily` +`precipitation_probability_max,sunrise,sunset,uv_index_max`; `forecast_days` 4→**7**
    - `data` เพิ่ม field: `wind_direction` (องศา)/`wind_direction_label` (ไทย 8 ทิศ `_wind_dir_label()`)/`wind_gusts` · `sunrise`/`sunset` (`"HH:MM"`) · `uv_index`/`uv_label` (ต่ำ/ปานกลาง/สูง/สูงมาก/อันตราย `_uv_label()`) · `precip_today` (%) · `hourly` (array ≤12 `{time,temp,precip,emoji}` เริ่มจากชั่วโมงปัจจุบัน — หา index ด้วยเทียบ ISO prefix `[:13]`) · `forecast` แต่ละวันเพิ่ม `precip` (%) และเป็น 7 วัน
    - UI (`showWeather` + `index.html` + `style.css`): `#weatherChips` = stat chip เล็ก (🌅🌇 UV 💧) · `#weatherWindRow` = ลูกศร `↑` หมุน `rotate(wind_direction+180)` (ชี้ทิศที่ลมพัดไป) + label + กระโชก · `#weatherHourly` = SVG กราฟเส้นอุณหภูมิ (`renderHourly()`, cyan polyline) + แท่งโอกาสฝนจางๆ ด้านหลัง + label ทุกจุดที่ 3 · `#weatherForecast` 7 คอลัมน์ (`flex:1 1 0`, ฟอนต์เล็กลง) + `.fc-precip` ใต้ min ถ้า >0
    - panel เปลี่ยนเป็น `overflow-y:auto; max-height:calc(100vh-24px)` กันสูงเกินจอเล็ก (`.weather-fx` เป็น `position:absolute` เลยค้างเป็น backdrop ตอน scroll ไม่ตามเนื้อหา — โอเค)
  - **การ์ดปรับตามคำถาม (ผู้ใช้ขอ — "ถามฝนตกช่วงไหนก็โชว์ UI ฝนรายชั่วโมง" ให้ครอบคลุมทุกถาม):**
    - `get_weather(location="", focus="", day=0)` — LLM เลือก `focus` ตามชนิดคำถาม (docstring map ให้ครบ): `now` (ทั่วไป) / `rain` (ฝนตกไหม/ช่วงไหน/พกร่มไหม/ตากผ้าได้ไหม) / `temperature` (ร้อน-หนาว/อุณหภูมิช่วง...) / `wind` (ลมแรง/ทิศ/กระโชก) / `uv` (แดดแรง/ครีมกันแดด) / `sun` (พระอาทิตย์ขึ้น-ตก/กลางวันยาว) / `forecast` (หลายวัน/สัปดาห์). `day` = 0 วันนี้..6 (เช่น "พรุ่งนี้ฝนช่วงไหน" → `focus="rain", day=1`). `_FOCUS_ALIASES` map คำพ้อง
    - **ยิง Open-Meteo ก้อนเดียว** (`hourly` เพิ่ม `apparent_temperature,precipitation,wind_speed_10m,wind_gusts_10m,uv_index`) แล้ว `_build_weather_reply()` สรุปคนละมุมตาม `view`: `data` ส่ง header "ตอนนี้" + `hourly`(12h) + `forecast`(7d) เสมอ (backward-compat), บวก block เฉพาะ view — `rain`: `rain_series[{time,prob,mm}]` + `rain_windows[{start,end,peak,peak_time}]` (`_rain_windows()` หาช่วง prob≥45% ต่อเนื่อง) · `temperature`: `temp_series` + `temp_max/min` + เวลา · `wind`: `wind_series[{speed,gust}]` + `wind_gust_max` · `uv`: `uv_series` + `uv_max` + เวลาพีค · `sun`: `sun_sunrise/sunset` + `day_length_h/m` + `sun_next[5]`. ทุก view คำนวณ `headline` (สรุปสั้นบนการ์ด) + **`reply` ที่ตอบคำถามตรงๆ** (เช่น "พรุ่งนี้น่าจะมีฝนช่วง 12:00–22:00 น. โอกาสสูงสุด 98% ตอน 16:00")
    - `_day_hour_indices(h_times, day, now_prefix)` = index รายชั่วโมงของวัน `day` (วันนี้เอาเฉพาะตั้งแต่ชั่วโมงปัจจุบันไป); เทียบ ISO string `[:10]`/`[:13]` = เรียงตามเวลาอยู่แล้ว
    - **UI** (`showWeather` switch บน `data.view`): `weatherPanel.dataset.view` → CSS `[data-view]` ซ่อน section ที่ view นั้นไม่ใช้. `view="now"` = การ์ดเต็ม (chips/stats/wind/hourly-12h/forecast-7d เหมือนเดิม). `view!="now"` = `#weatherFocus` (headline + กราฟโฟกัส); `forecast` = headline + แถว 7 วันใหญ่ขึ้น. **`renderSeriesChart(el, series, opts)` = กราฟ SVG อเนกประสงค์** (เส้นค่า + แท่งพื้นหลัง) ใช้ทั้ง `renderHourly()` และกราฟ rain/temp/wind/uv — series = `[{label,value,bar}]`
    - ข้อความพูดของ `get_weather()` = `reply` ต่อ view (ตรงคำถาม) ไม่ใช่สรุปทั่วไปตายตัวแล้ว
  - **animation พื้นหลังตามสภาพอากาศจริง** (ผู้ใช้ขอให้ "สวยกว่านี้ ใหญ่ขึ้น มี animation") — `renderWeatherFx(data.fx)` ใน `app.js` สร้าง DOM element ใน `#weatherFx` (layer ซ้อนอยู่หลังเนื้อหา, `overflow:hidden` ตัดขอบ) ตาม `fx` 6 หมวด: `sunny` (แสงเปล่งพัลส์ผ่าน CSS `::before` ล้วนๆ ไม่ต้องสร้าง element), `cloudy` (ก้อนเมฆเบลอ 3 ก้อนลอยผ่าน), `fog` (แถบหมอกไหลซ้ายขวา 3 แถบ), `rain` (เม็ดฝนตกจริง 16 เม็ด), `storm` (เหมือน rain + แสงฟ้าแลบเป็นจังหวะ), `snow` (เกล็ดหิมะโปรย 14 เกล็ด แกว่งซ้ายขวาผ่าน CSS var `--fx-drift`) — สุ่มแค่ `top`/`left`/`animation-duration`/`animation-delay` ต่อ element ให้ดูเป็นธรรมชาติ (ไม่ทับกันแข็งๆ) ตัว**หมวด**ยังคงมาจากข้อมูลจริงเสมอ ไม่ใช่สุ่มว่าจะโชว์ฝนหรือหิมะ
  - panel เข้าด้วย spring easing (`cubic-bezier(0.34, 1.56, 0.64, 1)`, ค่า overshoot เกิน 1 แล้วเด้งกลับ) แทน fade ธรรมดา ขยายขนาดจาก 220px เป็น 320px ตัวเลขอุณหภูมิ/ไอคอนใหญ่ขึ้นชัดเจน (52px/64px) ไอคอนมี animation ลอยขึ้นลงเบาๆ ตลอดเวลา (`weather-emoji-float`)
  - panel (`#weatherPanel`) ซ่อนไว้เป็นค่าเริ่มต้น โผล่มาเฉพาะตอนมีข้อมูลจริงจาก Open-Meteo แล้วเท่านั้น (เหมือน `.yt-panel`)
  - **ปิดตัวเองอัตโนมัติหลัง 30 วิ** (`WEATHER_AUTO_HIDE_MS`, ผู้ใช้ขอ) — นับเวลาจาก**เสียงพูดหยุดจริง** (ผ่าน `speak()`'s `onDone` callback) ไม่ใช่จากตอนได้ข้อมูลมา ใช้ pattern เดียวกับช่วงคุยต่อเนื่อง 15 วิเป๊ะ (`scheduleWeatherHide()` เรียกคู่กับ `startFollowUpWindow()` ใน `onDone`) — ถ้าถามอากาศที่ใหม่ระหว่างนับถอยหลังเดิมอยู่ `showWeather()` จะเคลียร์ตัวจับเวลาเก่าทิ้งแล้วเริ่มนับใหม่ ไม่ปิดกลางคันขณะกำลังโชว์ข้อมูลใหม่
  - เพิ่ม `requests` เป็น dependency ตรงๆ ใน `requirements.txt` (แม้จะมีอยู่แล้วแบบ transitive ผ่าน `gTTS` ก็ตาม) เพราะตอนนี้ `tools.py` เรียกใช้ตรงๆ เอง ไม่ควรพึ่ง transitive dependency ที่อาจหายไปได้ถ้า `gTTS` เปลี่ยนไปในอนาคต

**สถาปัตยกรรม tool ที่ต้อง "ทำอะไรบางอย่างในเบราว์เซอร์" (ไม่ใช่แค่คืนข้อความให้ LLM อ่าน):**
- ปัญหา: `google-genai`'s automatic function calling รัน Python function (`tools.py`) ฝั่ง **server** แต่ผู้ใช้ดู/คุมเบราว์เซอร์อยู่ฝั่ง **client** — ยิ่งมีแผนย้ายไป Pi ในอนาคต (`server` อาจรันคนละเครื่องกับเบราว์เซอร์ผู้ใช้เลย) เรียก `webbrowser.open()` ฝั่ง server ตรงๆ ไม่ได้
- แก้โดยให้ tool เก็บ "คำสั่งที่ต้องทำจริง" ไว้ในตัวแปร module-level `_pending_action` (dict) แทนที่จะลงมือเองฝั่ง server แล้ว `server.py`'s `chat_endpoint` เรียก `pop_pending_action()` หลัง `chat.send_message()` เสร็จ แนบมากับ `ChatResponse.action` — ฝั่ง `app.js` เช็ค `data.action.type` แล้วลงมือจริง (เป็นคนทำจริงตามหลัก "LLM เลือก tool, โค้ดเราลงมือจริง" เดียวกับที่ตั้งใจไว้ตอนแรกสำหรับ `control_home`)
- **`_pending_action` เป็น global ตัวเดียว ไม่ใช่ per-request** — ยอมรับได้เพราะโปรเจกต์นี้ตั้งใจไว้แต่แรกว่าเป็น personal use คนเดียว ไม่รองรับหลาย session พร้อมกันอยู่แล้ว — pop แล้วเคลียร์ทิ้งทุก path ที่ออกจาก `chat_endpoint` (ทั้งสำเร็จและ error) กัน action หลงเหลือไปโผล่ผิด request
- ตั้งใจไม่เพิ่ม tool พวกนี้ใน `jusmin.py` (CLI) เพราะ CLI ไม่มีกลไกไปทำอะไรจริงๆ ได้ (ไม่มี `pop_pending_action()` มาเรียกใช้) จะทำให้ จัสมิน โกหกว่าทำให้แล้วทั้งที่ไม่ได้ทำจริง

**`action.type` ที่มีตอนนี้ 3 แบบ (`server.py` ส่ง, `app.js` เป็นคนลงมือจริง):**
1. `open_url` — เปิดแท็บใหม่ด้วย `url` ที่กำหนด (ใช้ตอน `open_youtube()` ไม่มี query เลย แค่เปิดหน้าแรก youtube.com เฉยๆ)
2. `play_youtube` — โหลด+เล่นวิดีโอ `video_id`/`title` ในเครื่องเล่นที่ฝังในหน้าเว็บ (ไม่ใช่แท็บแยก) + `reset_volume` (bool: `open_youtube`=true รีเซ็ตเสียง 25%, `next`=false คงเสียงเดิม)
3. `youtube_control` — สั่ง `action` ("pause"/"resume"/"stop"/"volume_up"/"volume_down"/"fullscreen"/"exit_fullscreen") กับเครื่องเล่นที่กำลังเล่นอยู่

**เปิดวิดีโอเต็มจอ (`control_youtube('fullscreen')` / `'exit_fullscreen'`):**
- **กลไกหลัก = CSS ไม่ใช่ Fullscreen API** — `requestYoutubeFullscreen()` ใน `app.js` แค่ `ytPanel.classList.add('maximized')` แล้ว CSS `.yt-panel.maximized { position:fixed; inset:0; width:100vw; height:100vh; z-index:500 }` ขยายเครื่องเล่นเต็ม viewport ของเบราว์เซอร์ — **ไม่ต้องมี user gesture เลย เลยสั่งผ่านเสียงได้ทันที ไม่มีปุ่มให้ผู้ใช้กดเปิดเอง** (ผู้ใช้ขอชัดเจนว่าห้ามมีปุ่มกด). ตั้ง flag `ytMaximized` ไว้ track สถานะ
- **bonus real fullscreen**: หลัง add คลาสแล้ว ลอง `doRequestFullscreen(ytFullscreenTarget())` ต่อ **เฉพาะตอน `navigator.userActivation.isActive`** (มี transient activation จริง = พิมพ์คำสั่ง + Enter) เพื่อซ่อนแถบเบราว์เซอร์เพิ่ม — สั่งด้วยเสียง/auto-restore ไม่มี gesture เลยข้ามไปเลย (CSS `.maximized` เต็มจอเบราว์เซอร์ให้แล้ว) กัน Chrome log `requestFullscreen ... requires a user gesture` รก console. target = `ytPlayer.getIframe()` / fallback `document.getElementById('ytPlayerMount')` (YT API แทน `<div>` ด้วย `<iframe>` id เดิม ต้อง lookup ใหม่ ห้ามใช้ตัวแปรเก่าที่ค้าง node)
- **ออกจากเต็มจอ**: สั่ง "ออกจากเต็มจอ" (`exit_fullscreen`) / กด `Esc` (keydown handler — **bail ถ้า media viewer เปิดอยู่ ให้มันจัดการ Esc ก่อน ปิดทีละชั้น**) / กดปุ่ม `#ytExitFs` (✕ มุมขวาบน โผล่เฉพาะตอน `.maximized`) — `exitYoutubeFullscreen()` ลบคลาส + `document.exitFullscreen()` ถ้า real FS ทำงานอยู่ + เคลียร์ `ytWasMaximizedBeforeEngage` (ยกเลิกการเด้งกลับเต็มจอ).
- **z-index ชั้น overlay**: `.yt-panel.maximized` = 500 · `#mediaGridPanel` = **520** (เหนือ YT เต็มจอ ไม่งั้น grid โดนบัง) · `#mediaViewer` = 600 (ตัวดูรูป/วิดีโอ อยู่บนสุด) `fullscreenchange` listener: ถ้าผู้ใช้กด Esc ออกจาก real FS ให้ลบ `.maximized` ตามด้วย ไม่ให้ค้างเต็มจอครึ่งๆ. `control_youtube('stop')` เรียก `exitYoutubeFullscreen()` ด้วยเสมอ (ปิดเพลงแล้วไม่เด้งกลับ)

- **ย่อจอชั่วคราวตอนเรียก จัสมิน ระหว่างเต็มจอ (ผู้ใช้ขอ)** — เต็มจอ (`.maximized`) แล้วบัง HUD หลัก (เวฟ/สี/แชท z-index ต่ำกว่า 500) หมด เรียก จัสมิน ตอนนั้นเลยไม่เห็น feedback อะไร → แก้โดย **auto-ย่อจอชั่วคราว**: `renderWaveRing()` (loop ทุกเฟรมอยู่แล้ว) จับ **rising edge ของ `engagedActive`** → เรียก **`minimizeYoutubeForEngage()`** (ใน `youtube.js`) — helper atomic: `if (!S.ytMaximized) return; exitYoutubeFullscreen(); S.ytWasMaximizedBeforeEngage = true` (เดิม wave.js ทำ 2 บรรทัดเองแบบพึ่งลำดับ exit→ตั้ง flag — เปราะ ถ้าสลับบรรทัดพัง เงียบๆ; รวมเป็นฟังก์ชันเดียว). พอคุยจบ = `expireFollowUpWindow()` (จัสมิน พูดจบ + เงียบครบ 15 วิ ไม่มีถามต่อ — เป็น hook เดียวกับที่ปิดสีเขียว/แชท) → ถ้า `ytWasMaximizedBeforeEngage` และเพลงยังเล่นอยู่ (`ytPlayer && ytPanel.classList.contains('visible')`) → `requestYoutubeFullscreen()` กลับไปเต็มจอเอง. ถามต่อภายใน 15 วิ → timer reset (ผ่าน `startFollowUpWindow()` เดิม) → ยังย่อจออยู่จนกว่าจะเงียบจริง. สั่ง "ออกจากเต็มจอ"/`Esc`/ปิดเพลง ระหว่างช่วงนี้ → เคลียร์ `ytWasMaximizedBeforeEngage` ไม่เด้งกลับ. **ผลลัพธ์: ช่วงคุยกับ จัสมิน ได้ HUD หน้าหลักเต็มรูปแบบเป๊ะ ไม่ต้องทำ mini-overlay แยก**
- **ข้อจำกัดจาก `_pending_action` เป็น slot เดียว**: ขอ "เปิดเพลง X แบบเต็มจอ" ในประโยคเดียว LLM เรียก `open_youtube()` + `control_youtube('fullscreen')` ในเทิร์นเดียวไม่ได้ (อันหลังทับ `_pending_action` อันแรก เพลงเลยไม่โหลด) — docstring ของ `control_youtube` สั่งให้ LLM เปิดเพลงก่อน แล้วบอกผู้ใช้สั่ง "เต็มจอ" ต่ออีกที

**ทำไมต้อง "ฝัง player ในหน้าเว็บ" (`YT.Player`) แทนเปิดแท็บแยกด้วย `window.open()` เหมือนตอนแรก:**
- แท็บที่เปิดแยกเป็นคนละ browsing context กันเลย โค้ดเราคุม play/pause/stop จากภายนอกไม่ได้จริงๆ (ไม่มี API ให้เข้าถึง iframe ข้าม origin) — ต้องฝัง [YouTube IFrame Player API](https://developers.google.com/youtube/iframe_api_reference) (`https://www.youtube.com/iframe_api`, ฟรี ไม่ต้องขอ key) ไว้ในหน้าเว็บเราเองถึงจะเรียก `player.pauseVideo()`/`playVideo()`/`stopVideo()`/`loadVideoById()` ได้จริง
- โหลด script แบบ dynamic ผ่าน `loadYtApiScript()` ใน `app.js` (ไม่ใช่ `<script>` ตายตัวใน `index.html`) เพราะไม่จำเป็นต้องโหลดถ้าไม่เคยสั่งเปิดเพลงเลย
- **บั๊กจริงที่เจอตอนไล่หาความเสถียร (`ytPlayerReady`)**: เมธอดของ `YT.Player` (`setVolume`/`pauseVideo`/`playVideo`/`stopVideo`) **ใช้งานจริงไม่ได้ก่อน event `onReady`** แม้ `new YT.Player(...)` จะคืน object กลับมาแบบ synchronous ทันทีก็ตาม (iframe ข้างในยังไม่เชื่อมต่อ postMessage เสร็จ เป็นพฤติกรรมที่เอกสารทางการของ YouTube ระบุไว้) — เดิมโค้ดเช็คแค่ `ytPlayer !== null` ไม่ได้เช็ค ready จริง ถ้าผู้ใช้สั่ง "หยุดเพลง"/"เพิ่มเสียง" ไวมากทันทีหลัง "เปิดเพลง X" (ภายในเสี้ยววินาทีที่ iframe ยังโหลดไม่เสร็จ) คำสั่งนั้นจะเงียบหายไปเฉยๆ ไม่มีผลอะไรเลย
  - แก้โดยเพิ่ม `ytPlayerReady` (true เฉพาะหลัง `onReady` จริง ค้างจนกว่าจะโหลดหน้าใหม่ — ไม่รีเซ็ตตอนเปลี่ยนเพลงเพราะ `loadVideoById()` ไม่ยิง `onReady` ซ้ำ) `controlYoutube()` เช็ค flag นี้ก่อนเสมอ ถ้ายังไม่ ready จะเก็บ action ล่าสุดไว้ใน `ytPendingCommand` (คำสั่งล่าสุดชนะ ไม่สะสมเป็นคิว) แล้วให้ `onYtPlayerReady()` ทำให้ทันทีที่ ready จริง — `duckYoutubeVolume()`/`restoreYoutubeVolume()` เช็ค flag เดียวกันแต่ไม่คิว (ปล่อยผ่านเฉยๆ เพราะรอบพูดถัดไปจะ duck/restore ใหม่ให้เองอยู่แล้ว ไม่คุ้มจะเพิ่ม complexity)
- `#ytPlayerMount` ถูก YT API แทนที่ด้วย `<iframe>` จริงตอนสร้าง `new YT.Player(...)` — panel `#ytPanel` (มุมซ้ายกลางของจอ) ซ่อนไว้เป็นค่าเริ่มต้น (`opacity:0`) โผล่มาเฉพาะตอนกำลังเล่นเพลงจริงเท่านั้น ตรงกับหลักการ "ห้ามใส่ panel ที่โชว์ข้อมูลปลอม"
- **Audio ducking**: ตอน จัสมิน พูด (TTS) จะลดเสียงเพลง YouTube ลงชั่วคราวเหลือ `YT_DUCK_VOLUME = 15` (จาก `ytVolume` ปัจจุบัน) ผ่าน `ytPlayer.setVolume()` แล้วคืนกลับตอนพูดจบ (`ttsAudio`'s `play`/`ended`/`error` event — `duckYoutubeVolume()`/`restoreYoutubeVolume()` ใน `app.js`) กันเสียงพูดทับเพลงจนฟังไม่รู้เรื่อง ยังไม่ได้ทำ AEC จริงจัง (echo cancellation ระดับสัญญาณเสียง) แค่ลด volume ธรรมดา เพียงพอสำหรับ use case นี้แล้ว
- **สั่งเพิ่ม/ลดเสียงเพลงด้วยเสียงได้** (`control_youtube('volume_up'/'volume_down')`) — `ytVolume` (ตัวแปรใน `app.js`) เป็น "baseline" ที่ผู้ใช้ตั้งไว้ล่าสุด **แยกต่างหากจากค่าตอน duck ชั่วคราว** (`YT_DUCK_VOLUME`) เพิ่ม/ลดทีละ `YT_VOLUME_STEP = 25` (เดิม 20) clamp ไว้ที่ 0-100 เสมอ
- **ค่าเริ่มต้นเสียง = 25% เฉพาะตอน "เปิดใหม่" (ผู้ใช้ขอ)** — `YT_DEFAULT_VOLUME = 25` (JS) / `_YT_DEFAULT_VOLUME = 25` (`tools/youtube.py`, ต้อง sync มือ)
  - **"เปิด YouTube ใหม่" (`open_youtube`) → รีเซ็ตเป็น 25%**: `open_youtube` แนบ `"reset_volume": True` ใน `play_youtube` action; `main.js` ส่งต่อเป็น arg ที่ 3 ของ `playYoutubeVideo(id, title, resetVolume)`; JS `applyDefaultVolume()` ตั้ง `ytVolume=25` + `setVolume(25)` (ข้าม setVolume ถ้า TTS duck ค้างอยู่ — `restoreYoutubeVolume()` หยิบไปใช้ตอนพูดจบ). `onYtPlayerReady` (player แรกสุด = มาจาก `open_youtube` เสมอ) ก็เรียก `applyDefaultVolume()`. `stop` ก็รีเซ็ต `ytVolume`/`_youtube_volume` กลับ 25
  - **"เปลี่ยนเพลง / เพลงถัดไป" (`next`) → คงเสียงเดิมไว้**: `next` แนบ `"reset_volume": False`; JS ข้าม `applyDefaultVolume()` (loadVideoById ไม่แตะ volume ของ player อยู่แล้ว); server ไม่แตะ `_youtube_volume` — % ที่ตอบใน `volume_up/down` เลยยังตรง
  - **feedback จริงจากผู้ใช้**: สั่ง "ลดเสียง" แล้ว "รู้สึกว่าไม่ลดเลย" — ไล่ตรวจสอบด้วย `player.getVolume()` ของ real YT.Player (ไม่ใช่ mock) ยืนยันว่า**กลไกทำงานถูกต้อง 100%** (ค่าเปลี่ยนจาก 100 เป็น 80 จริงตามที่สั่ง 1 ครั้งที่ step เดิม 20) แต่หูมนุษย์รับรู้ความดังแบบ logarithmic ไม่ใช่ linear ทำให้ step 20 หน่วยจาก 100 รู้สึกถึงความต่างน้อยเกินไปจนเหมือนไม่ได้เปลี่ยน — เพิ่ม step เป็น 25 ให้รู้สึกถึงการเปลี่ยนแปลงชัดเจนขึ้นต่อ 1 คำสั่ง (ถ้ายังรู้สึกน้อยไปอีกปรับเพิ่มได้ตามใจ)
  - **feedback รอบ 2**: ผู้ใช้รายงานว่า "หลังถาม จัสมิน มันเพิ่มเสียงให้เอง" — ทดสอบจำลองสถานการณ์ (เปิดเพลง → ลดเสียง → ถามคำถามทั่วไปที่ไม่เกี่ยวกับเพลงเลย → เช็ค `player.getVolume()` จริงหลัง TTS duck/restore cycle) **ไม่พบว่า Gemini เรียก `volume_up` เองเลย** (`action: null` ตามคาด, volume คงที่ถูกต้อง) เป็นไปได้ว่าเป็นเคสเฉพาะ (STT ฟังผิดเป็นคำสั่งเพิ่มเสียง, หรือบทสนทนารูปแบบอื่นที่ไม่ได้ลองจำลอง) — แก้เชิงป้องกันไว้ก่อนตามที่ผู้ใช้ขอ: เพิ่ม `_youtube_volume` ให้ server (`tools.py`) ติดตามระดับเสียงปัจจุบันขนานไปกับฝั่ง client (`ytVolume` ใน `app.js`คนละตัวแปร คนละภาษา ต้อง sync `_YT_VOLUME_STEP`/`YT_VOLUME_STEP` มือเอง) ให้ข้อความตอบของ `volume_up`/`volume_down` บอกเปอร์เซ็นต์ปัจจุบันเสมอ (เช่น "ลดเสียงเพลงให้แล้วค่ะ ตอนนี้อยู่ที่ 75%") จะได้ปรากฏในประวัติบทสนทนาที่ Gemini เห็น มี context จริงอ้างอิงแทนเดามั่วๆ พร้อมเสริม docstring ของ `control_youtube()` ให้ชัดว่า**ห้ามเรียกเองเดาเอาว่าผู้ใช้อาจต้องการ** ต้องเป็นคำขอที่ชัดเจนจริงๆ เท่านั้น
  - **จุดที่ต้องระวัง**: `restoreYoutubeVolume()` ต้องคืนกลับไปที่ `ytVolume` ไม่ใช่ค่าคงที่ 100 เสมอ ไม่งั้นถ้าผู้ใช้เคยหรี่เสียงไว้ พอ จัสมิน พูดจบเสียงเพลงจะดังกลับไป 100% เองทุกครั้งที่พูด ผิดจากที่ผู้ใช้ตั้งไว้
  - **ถ้าสั่งปรับเสียงระหว่างที่ จัสมิน กำลังพูดอยู่พอดี** (`ttsSpeaking === true`, กำลัง duck ค้างอยู่) จะไม่เรียก `setVolume()` ทันที แค่จำค่า `ytVolume` ใหม่ไว้ก่อน กันเสียงเพลงดังแทรกขึ้นมากลางประโยคที่ จัสมิน กำลังพูด — พอ TTS จบจริง `restoreYoutubeVolume()` จะหยิบค่าล่าสุดไปใช้เอง
  - `control_youtube('stop')` รีเซ็ต `ytVolume` กลับ `YT_DEFAULT_VOLUME` (25) ด้วย (เริ่มฟังเพลงครั้งถัดไปที่ค่าเริ่มต้นเสมอ ไม่ค้างค่าที่เคยปรับไว้)
- **ระหว่างเพลงเล่นอยู่จริง ต้องพูด "จัสมิน" นำทุกครั้ง ห้ามข้ามช่วงคุยต่อเนื่อง 15 วิ** — ผู้ใช้ขอเพราะกลัวเนื้อเพลง/เสียงร้องถูก STT จับแล้วตีความเป็นคำสั่งมั่วๆ ระหว่างเพลงเล่น (ความเสี่ยงสูงกว่าเวลาปกติเพราะมีเสียงคนพูด/ร้องเพลงในห้องต่อเนื่องยาวกว่าประโยคสนทนาทั่วไป) — คุมด้วยตัวแปร `ytIsPlaying` ใน `app.js` ที่อัปเดตจาก **state จริงของ `YT.Player`** ผ่าน `onStateChange` event (ไม่ใช่เดาจากว่าเพิ่งสั่ง `playVideo()` ไปหรือยัง) แล้วเช็คเงื่อนไข `if (followUpActive && !ytIsPlaying)` ใน `wakeRecognition.onresult` — เพลงเล่นอยู่จริงจะบังคับให้ตกไปเช็ค `extractWakeCommand()` เสมอ ซึ่งต้องมีคำว่า "จัสมิน" อยู่จริงในประโยคถึงจะทำงาน
  - `controlYoutube('pause'/'stop')` ตั้ง `ytIsPlaying = false` ทันทีไม่รอ `onStateChange` async กลับมา (ฝั่ง `resume` ปล่อยให้รอ event จริงเพราะตั้ง `true` ทันทีเสี่ยงผิดถ้า buffering ช้า — ทิศทางที่ปลอดภัยกว่าคือรอให้แน่ใจก่อน)

**วิดีโอที่เล่นได้มาจาก `yt-dlp` ค้นหาจริงฝั่ง server (ไม่ใช่ YouTube Data API ที่ต้องขอ API key/มี quota):**
- `_search_youtube(query)` ใน `tools.py` ใช้ `yt_dlp.YoutubeDL` กับ virtual URL `ytsearch{N}:{query}` (`extract_flat=True` เร็ว ไม่โหลดข้อมูลวิดีโอเต็ม แค่ list ผลค้นหา) — ทดสอบจริงแล้วใช้เวลา ~2 วิ/ครั้ง สำหรับ 5-8 ผลลัพธ์
- `open_youtube(query)` เก็บผลค้นหา (`_YT_SEARCH_COUNT = 8` รายการ) ไว้ใน `_youtube_queue` module-level list + `_youtube_queue_index` ชี้ตำแหน่งปัจจุบัน แล้วส่ง `play_youtube` action ให้เล่นตัวแรก
- `control_youtube("next")` เลื่อน index ไปข้างหน้าในคิวเดิม (ไม่ค้นใหม่) ส่ง `play_youtube` action สำหรับเพลงถัดไป — ถ้าหมดคิวแล้วตอบกลับบอกให้เปิดเพลงใหม่แทน ไม่ error
- `control_youtube("stop")` เคลียร์คิวทิ้งด้วย (กด "next" หลัง stop จะได้ข้อความ "หมดคิว" ไม่ใช่เล่นเพลงเก่าที่ปิดไปแล้วต่อ)
- **เจอบั๊กจริงตอนพัฒนา**: `yt_dlp` เองก็ throw exception ได้เหมือน `ddgs` (เน็ตหลุด, YouTube เปลี่ยนโครงหน้าเว็บ ฯลฯ) — ครอบ `try/except Exception` กว้างๆ ใน `open_youtube()` (ไม่แคบเท่า `search_web()`'s `DDGSException` เพราะ `yt_dlp` ไม่มี exception class เฉพาะให้ import เหมือน `ddgs`) คืนข้อความ graceful แทนปล่อยให้พังดิบๆ

**Safety**: โดเมน/วิดีโอที่เล่นมาจากผลค้นหา `yt-dlp` จริงเท่านั้น LLM คุมได้แค่คำค้นหา (ส่งเป็น query string ไปยัง `ytsearch{N}:`) ไม่สามารถสั่งเล่น video_id ที่ไม่มีอยู่จริงหรือเปิดโดเมนอื่นได้ ไม่ต้องมี whitelist แยกเหมือน `control_home` เพราะ risk ต่ำกว่ามาก (ไม่ใช่ฮาร์ดแวร์จริง)

**popup blocker + fallback link (ยังมีผลกับ `open_url` action เท่านั้น — ตอนไม่มี query เลย):**
- `window.open()` ต้องเรียกใกล้ๆ กับ user gesture ถึงจะไม่โดนเบราว์เซอร์บล็อก — โค้ดเลยเรียกทันทีที่ได้ reply กลับมา (ก่อน `speak()`/TTS ซึ่งกินเวลาเพิ่ม) เพื่อให้ยังอยู่ในช่วง "transient activation" ถ้าสั่งผ่าน**พิมพ์แล้วกด Enter**โอกาสเปิดสำเร็จสูง แต่ถ้าสั่งผ่าน**เสียง (wake mode)**ไม่มี user gesture จริงเลย เบราว์เซอร์จริงมีโอกาสบล็อก — **ยืนยันจากการทดสอบจริงว่านี่คือสาเหตุจริงที่ผู้ใช้เจอ** ("ยังใช้ไม่ได้" ทั้งที่ backend ทำงานถูกต้อง 100% ยืนยันด้วย curl กับ Gemini จริง)
  - `window.open()` คืนค่า `null` เงียบๆ ตอนโดนบล็อก (ไม่ throw) — `openUrlWithFallback()` ใน `app.js` เช็คค่านี้ ถ้า blocked จะเพิ่มลิงก์ให้กดเองใน chat log (`addLinkLine()`, คลาส CSS `.จัสมิน-link`) แทนที่จะปล่อยให้ดูเหมือน "ใช้ไม่ได้" เฉยๆ
  - **สำคัญ**: ต้องเรียก `window.open(url, '_blank')` แบบ**ไม่ใส่** `'noopener'`/`'noreferrer'` ถึงจะเช็คผลลัพธ์ได้ — ทดสอบยืนยันแล้วว่าถ้าใส่ 2 อันนี้ (ปกติควรใส่เพื่อความปลอดภัย กัน tabnabbing) `window.open()` จะคืนค่า `null` เสมอไม่ว่าจะเปิดสำเร็จหรือไม่ก็ตาม เลยแยกแยะไม่ได้เลย — ยอมข้ามไปเพราะ url ตายตัวที่ youtube.com ไม่ใช่ url จากภายนอกที่ควบคุมไม่ได้
  - `play_youtube`/`youtube_control` ไม่เจอปัญหานี้เลยเพราะไม่ได้เปิดแท็บ/popup ใหม่ แค่โหลด/สั่ง player ที่ฝังอยู่ในหน้าเดิม

**เรื่องต้องรู้เกี่ยวกับ wake word:**
- **โหมดฟังตลอดเปิดเป็นค่าเริ่มต้น** (auto-start ทันทีที่โหลดหน้าเว็บ, ปุ่ม 👂 จะติดไฟทันที) — เบราว์เซอร์จะขอสิทธิ์ไมค์เองถ้ายังไม่เคยอนุญาต
- เปิดแล้ว browser จะส่งเสียงไมค์ไปประมวลผลที่ cloud ของ Google (Web Speech API) **ตลอดเวลา** ไม่ใช่แค่ตอนกดพูด มีผลเรื่อง privacy/แบตเตอรี่/data ที่ควรรู้ไว้
- "จัสมิน" คล้ายคำทั่วไป (jasmine ดอกมะลิ / ชื่อคน / เพลงแจ๊ส) เสี่ยง false trigger ได้ถ้าทีวี/พอดแคสต์พูดผ่าน ๆ ในห้อง — `WAKE_WORD_PATTERNS` ตั้งใจกว้าง (ผู้ใช้ขอ "เรียกง่ายขึ้น") ยอมรับ false trigger จาก "แจ๊ส/jasmine" บ้าง แลกกับการเรียกติดง่าย; ปรับแคบลงได้ที่ list เดียวในไฟล์ `voice.js`
- **กัน feedback loop โดยปิดไมค์จริงตอน จัสมิน พูด** — `pauseWakeListening()` เรียก `recognition.stop()` จริง ๆ ตอน audio element ยิง event `play` (ไม่ใช่แค่เช็ค flag) แล้ว `resumeWakeListeningAfterDelay()` เปิดกลับมาหลัง event `ended`/`error` + หน่วง 500ms กันหางเสียง/เสียงสะท้อนในห้อง ข้อแลกเปลี่ยนที่ยอมรับ: **แทรกกลางประโยคไม่ได้** ต้องรอ จัสมิน พูดจบก่อน (ชดเชยด้วยช่วงคุยต่อเนื่อง 15 วิด้านล่าง)
  - เคยลองอีกวิธี (ไม่ปิดไมค์ เทียบข้อความที่ได้ยินกับสิ่งที่ จัสมิน กำลังพูดอยู่แทน เพื่อให้แทรกได้ทันที) แต่ไม่น่าเชื่อถือพอในการใช้งานจริง เพราะเสียงสะท้อนที่ผ่าน STT กลับมามักเพี้ยนจากต้นฉบับเยอะ เทียบไม่ติด — **แผนอนาคต**: ทำ Acoustic Echo Cancellation จริงผ่าน `getUserMedia({echoCancellation:true})` + STT backend เอง (เช่น Whisper ตามแผนเดิม) ถึงจะแทรกกลางประโยคได้แบบเชื่อถือได้จริง
- ใช้ปุ่มไมค์กดพูดปกติไม่ได้พร้อมกับโหมดนี้ (ปิดปุ่มไมค์ไว้อัตโนมัติตอนเปิดโหมดฟังตลอด)
- **คุยต่อเนื่องได้ 15 วิ** — หลัง จัสมิน ตอบเสร็จ (ไมค์เปิดกลับมาแล้ว) พูดคำถามต่อได้เลยโดยไม่ต้องพูด "จัสมิน" ซ้ำ (สถานะใต้ core จะขึ้น "STANDBY · ฟังต่อเนื่อง") ถ้าเงียบเกิน 15 วิ ต้องพูด "จัสมิน" นำใหม่ กันไม่ให้จับเสียงอื่นในห้องมั่ว ๆ — **นับ 15 วิเริ่มตั้งแต่เสียงพูดหยุดจริง** (ผ่าน `speak(text, onDone)` callback ตอน TTS `onend`) ไม่ใช่นับตั้งแต่ได้คำตอบมา เพื่อไม่ให้คำตอบยาวๆ ที่พูดนานโดนกินเวลาช่วงคุยต่อเนื่องไปตั้งแต่ยังพูดไม่จบ
- **เรียกชื่อเฉยๆ ไม่มีคำสั่งตาม** (พูดแค่ "จัสมิน" คำเดียว) — จัสมิน จะ**ตอบรับด้วยเสียงจริง** (สุ่มจาก `WAKE_ACK_PHRASES` กันซ้ำจำเจ) ไม่ใช่แค่เสียง beep เหมือนก่อนหน้านี้ พอตอบรับเสร็จ (ไมค์เปิดกลับมาเอง) จะเข้าสู่ช่วงคุยต่อเนื่อง 15 วิทันที (`startFollowUpWindow()`) ให้พูดคำถามจริงต่อได้เลยโดยไม่ต้องพูด "จัสมิน" ซ้ำอีกรอบ
- **บั๊กจริงที่เจอ: พูด "จัสมิน" คำเดียวแล้วติดบ้างไม่ติดบ้าง** — สาเหตุคือ `wakeRecognition.onend` restart session ใหม่ทุกครั้งที่ session เดิมจบ (Chrome ตัด `continuous:true` session เองเป็นระยะ**แม้ไม่มี error เลย** ไม่ใช่แค่ตอน error เท่านั้น) โค้ดเดิมหน่วง 250ms ก่อน restart ทุกรอบ — ระหว่าง 250ms นั้นไมค์ "หูหนวก" สนิท ถ้าจังหวะพูดคำสั้นๆ อย่าง "จัสมิน" (~300-500ms) ดันตรงกับช่วงรีสตาร์ทพอดี คำนั้นจะหายไปเงียบๆ โดยไม่มี error ให้เห็นเลย — ยิ่งพูดคำเดียวสั้นๆ ยิ่งเสี่ยงกว่าประโยคยาว (มีโอกาสถูก "ตัด" มากกว่า) ตรงกับ pattern ที่ผู้ใช้เจอ แก้โดยลดหน่วงเหลือ `WAKE_RESTART_DELAY_MS = 30` (จาก 250) ลดหน้าต่างที่พลาดได้ลงไปมาก (ทดสอบวัดจริง gap ลดจาก 250ms เหลือ ~31ms) ยังเหลือกันชนเล็กน้อยกัน Chrome โยน "recognition already started" ถ้า restart เร็วเกินไป
  - เพิ่ม retry ใน `catch` ของ `wakeRecognition.start()` ด้วย (เดิมถ้า `start()` throw จะไม่มีอะไรมา restart ให้เลยเพราะ session นั้นไม่เคย start จริง `onend` เลยไม่มีทางยิง) — ป้องกันโหมดฟังตลอดค้างเงียบไปเฉยๆ แบบไม่มี error ให้เห็น
  - `console.log('[wake] missed:', transcript)` ตอน STT ได้ยินอะไรมาแต่ไม่ตรงกับ `WAKE_WORD_PATTERNS` เลย (ใช้ `console.log` ไม่ใช่ `debug` จะได้เห็นใน console โดยไม่ต้องเปิด Verbose) — เปิด F12 ดูว่า STT ถอด "จัสมิน" เป็นคำว่าอะไรตอนเรียกไม่ติด แล้วเอามาเพิ่มใน pattern list
  - `WAKE_WORD_PATTERNS` (ใน `voice.js`) ตอนนี้กว้างมาก: โรมัน (jusmin/jasmine/yasmin/jazmin/`\bjustin\b`/chmin...) + ไทยสลับ จ↔ย↔ญ↔ช, ส↔ด↔ซ↔ช↔ท, เติม/ตัดสระ, มีวรรณยุกต์แทรก (`T = [็-๎]?` คั่นทุกพยางค์), เว้นวรรคกลางคำ, หาง "ทร์/์", ตัว จ นำหล่น (รัสมิน/อัสมิน), และ fallback สั้น "จัส/จัสมิ" (lookbehind `(?<=^|\s)`). ตั้งใจ **ไม่** จับ "จัด" เดี่ยวๆ + "แจ๊ส" เดี่ยวๆ (jazz) + "justin" ที่เป็น substring (adjusting). `extractWakeCommand()` เลือก match ต้นประโยคสุด แล้ว slice ส่วนที่เหลือเป็นคำสั่ง

- **รื้อความเสถียร wake mode (ผู้ใช้บ่น "เรียกไม่ค่อยติด") — `runWakeRecognition()` เขียนใหม่:**
  - **`interimResults: true`** (เดิม false) — จับคำปลุกจาก interim ได้เร็วขึ้น 300–800ms + รอด session-end ที่ยังไม่ทันได้ `isFinal`
  - **`maxAlternatives = 3`** — วน `result[0..2]` เช็ค pattern ทุก alternative (Google มัก transcribe "จัสมิน" เป็นตัวเลือก #2 ตอน #1 เพี้ยน) ใช้ alternative ที่เจอคำปลุกเป็น transcript
  - **per-utterance state** (`curUtterIdx`/`utterWakeSeen`/`utterHandled`/`lastInterim`) — interim ที่เจอคำปลุก → `S.engagedActive = true` ทันที (feedback) แต่รอ `isFinal` ถึงประมวลผลจริง (ใช้ text final ที่สะอาด ไม่ต่อ interim ซ้ำ) · `utterHandled` กันยิงซ้ำ
  - **`onend` fallback** — ถ้า session ตายก่อนได้ final แต่ interim เคยเจอคำปลุก → `handleWakeFinal(lastInterim)` (กู้ "จัสมิน" คำเดียวสั้นๆ ที่หายบ่อยสุด) · ระหว่างคุยต่อเนื่องก็ flush `lastInterim` เข้า `queueWakeCommand`
  - **`killWakeRecognition()`** (`abort()` + ถอด handler) เรียกก่อนสร้าง instance ใหม่ทุกครั้ง + flag `wakeStarting` กัน `start()` ซ้อน — ตัดปัญหา instance เก่ายังฟัง/`onend` เก่าสั่ง restart ทับจน instance ทวีคูณ (pause/stopWakeMode ใช้ตัวนี้ด้วย)
  - **watchdog** `setInterval(3000)` — ถ้าเรียก `start()` เกิน 5 วิแต่ `onstart` ไม่มา + ไม่มี restart รอ = session ตายเงียบ → force `runWakeRecognition()` + status "ไมค์หลุด · กำลังต่อใหม่"
  - **`flashHeard(transcript)`** — `onresult` ที่ได้ยินแต่ไม่ตรงคำปลุก → status เด้ง `STANDBY · ได้ยิน "..."` 1.8 วิ (บอกผู้ใช้ว่าไมค์ทำงาน เป็นปัญหา match ไม่ใช่ไมค์ตาย)
  - `TTS_RESUME_DELAY_MS` 500 → **200** (ไมค์กลับมาไวขึ้นหลัง จัสมิน พูดจบ)
  - **ที่ยังแก้ไม่ได้** (ข้อจำกัด Web Speech API): `start()` latency ภายในเบราว์เซอร์, session cutoff, พึ่งเน็ต/Google — หายจริงต้องย้าย STT server-side (openWakeWord + faster-whisper) ตาม ROADMAP Phase 2
- **Debounce 5 วิก่อนส่งคำสั่งจริง (`COMMAND_DEBOUNCE_MS`)** — ผู้ใช้ขอเพราะเดิม `wakeRecognition.onresult` ส่งคำสั่งทันทีที่ recognition ตัดจบประโยค (isFinal) ซึ่งเกิดขึ้นเร็วกว่าที่คิด ถ้าหยุดพูดแป๊บนึงเพื่อคิดคำต่อ ท่อนแรกจะถูกตัดส่งไปเป็นคำสั่งที่ยังพูดไม่จบเลย — แก้ด้วย `queueWakeCommand(text)`/`flushWakeCommand()`: แทนที่จะ `form.requestSubmit()` ทันที จะต่อท้อความเข้ากับ `pendingCommandText` แล้วรีเซ็ตนาฬิกา 5 วิใหม่ทุกครั้งที่ได้ยินเสียงเพิ่ม จนกว่าจะเงียบจริงๆ ครบ 5 วิถึงส่งเป็นข้อความเดียว
  - ระหว่างรอ debounce (`isAccumulatingCommand = true`) พูดต่อได้โดย**ไม่ต้องพูด "จัสมิน" ซ้ำ** — เงื่อนไขใน `onresult` เปลี่ยนจาก `if (followUpActive && !ytIsPlaying)` เป็น `if ((followUpActive || isAccumulatingCommand) && !ytIsPlaying)` ไม่งั้นท่อนพูดต่อ (ที่ไม่มีคำว่า จัสมิน แน่นอนเพราะเป็นประโยคเดียวกัน) จะหลุดไปเช็ค `extractWakeCommand()` แล้วโดนทิ้งเป็น "missed" ไปเฉยๆ
  - **ผลข้างเคียงที่ตั้งใจยอมรับ**: ทุกคำสั่งเสียง (ไม่ว่าจะหยุดคิดหรือพูดรวดเดียวจบ) จะช้าลง 5 วิเทียบกับก่อนหน้านี้เสมอ เพราะระบบรอดูก่อนว่าจะพูดต่อไหมทุกครั้ง ไม่ใช่แค่ตอนตรวจจับว่าหยุดกลางคัน — เป็น trade-off ที่ผู้ใช้ยอมรับเพื่อแลกกับไม่ให้ประโยคถูกตัดกลางคัน
  - `queueWakeCommand()` เคลียร์ `followUpTimer` เดิมทุกครั้งด้วย (เหมือน `consumeFollowUpWindow()`) กันช่วงคุยต่อเนื่อง 15 วิเดิมหมดอายุกลางคันระหว่างรอ debounce แล้วค่อยเรียก `consumeFollowUpWindow()` จริงตอน `flushWakeCommand()` ก่อนส่ง
  - `stopWakeMode()` เคลียร์ `pendingCommandText`/`commandDebounceTimer`/`isAccumulatingCommand` ด้วย กันคำสั่งที่กำลังรอ debounce อยู่หลุดไปส่งทีหลังทั้งที่ปิดโหมดฟังตลอดไปแล้ว

## เสียงพูด TTS: เปลี่ยนจาก browser มาเป็น server-side (vachanatts)

เดิมใช้ `speechSynthesis` ของเบราว์เซอร์ (ฟรี ไม่ต้องตั้งอะไร) แต่เสียง Windows SAPI ที่มีในเครื่องฟังดูหุ่นยนต์เกินไป ไล่หาทางเลือกแล้วสรุปได้ดังนี้:
- **Piper TTS** — เช็คตรงจากซอร์สทางการ (GitHub `VOICES.md`, Hugging Face repo) ยืนยันแล้วว่า**ไม่มีเสียงภาษาไทยเลย** ทั้ง catalog ทางการและโมเดลชุมชน ตัดออก
- **ThonburianTTS / F5-TTS-THAI** — คุณภาพน่าจะดีสุด แต่เป็น diffusion model ไม่มี GPU จะช้ามาก (หลายวิ/ประโยค) ไม่เหมาะกับ voice assistant ที่ต้องตอบไว
- **`facebook/mms-tts-tha`** — VITS เบา (36M params) แต่เป็นโมเดลรวม 1000+ ภาษา ไม่ได้เน้นภาษาไทยโดยเฉพาะ
- **เลือกใช้ `vachanatts` (engine `vachana` ของ PyThaiNLP/`pythaitts`) เรียก `Voice`/`SpeechConfig` ระดับล่างตรงๆ** — Thai-specific, ONNX/VITS, เบา, รองรับข้อความปนอังกฤษ/ตัวเลขได้ (ทดสอบคำว่า "จัสมิน", "Gemini API", "27" แล้วผ่าน) — engine เริ่มต้นของ pythaitts (`lunarlist_onnx`) ใช้ไม่ได้เพราะช้ากว่ามากและ error ทันทีถ้ามีตัวอักษรอังกฤษปน
- **ปรับ `noise_scale=0.4`, `noise_w_scale=0.3`** (ค่าเริ่มต้นของ VITS คือ 0.667/0.8) — ค่าเริ่มต้นทำให้จังหวะ/การเว้นวรรคคำฟังดูสุ่มเกินไป ทดสอบเทียบเสียงจริงหลายแบบ (ค่าเดิม vs เติมวรรคตอน vs ลด noise vs เปลี่ยนเสียง) แล้วลด noise ชนะชัดเจน
- **แก้เสียงเพี้ยน/เว้นวรรคไม่เป็นธรรมชาติรอบ 2** — feedback หลังใช้งานจริง (ประโยคหลายประโยคต่อกัน) พบว่ายัง "เพี้ยน" อยู่ ไล่เช็คซอร์ส `vachanatts` เจอ 2 จุด:
  - `SpeechConfig.normalize_audio=True` (default ของไลบรารี) ดันทุกประโยคให้ดังสุด (peak=1.0) เท่ากันหมด ทั้งที่แต่ละประโยคดังไม่เท่ากันตามธรรมชาติ (วัดจริง RMS ต่างกันถึง ~30% ระหว่างประโยค) ทำให้ได้ยินเสียงดัง-เบาสลับกันกระโดดตอนต่อประโยค ฟังเหมือนเพี้ยน — **ปิดแล้ว** (`normalize_audio=False`)
  - `Voice.synthesize_wav()` ต่อเสียงแต่ละประโยคติดกันตรงๆ ไม่มีช่วงเงียบคั่นเลย — **เพิ่ม `SENTENCE_GAP_MS=180`** แทรกความเงียบสั้นๆ ระหว่างประโยคเอง
  - `pythaitts`/`vachanatts.main.TTS()` wrapper ไม่เปิดช่องให้ปิด `normalize_audio` หรือคุมช่วงเงียบได้เลย เลย**เปลี่ยนมาเรียก `Voice`/`SpeechConfig`/`voice.synthesize()` ของ `vachanatts` ตรงๆ** ใน `tts.py` แทนผ่าน wrapper
- **บอนัสเรื่องความเร็ว**: การเปลี่ยนมาเขียนเสียงลง `io.BytesIO()` ในหน่วยความจำแทนที่จะเขียนไฟล์ชั่วคราวจริงแล้วอ่านกลับ (`tempfile.mkstemp` แบบเดิม) ทำให้เร็วขึ้นจริงโดยไม่ได้ตั้งใจ — วัดจริง: เดิม ~3.5–3.9 วิ/คำตอบ (3 ประโยค) → ตอนนี้ ~2.0–2.2 วิ (ลดลง ~45%) ทดสอบผ่าน `/api/tts` จริงยืนยันตัวเลขนี้ด้วย ไม่ใช่แค่วัด function เดี่ยวๆ
  - ลองปรับ ONNX Runtime threading (`intra_op_num_threads`, `execution_mode`) ดูด้วย แต่ผลออกมา**แย่กว่าเดิม**ทุกค่าที่ลอง (thread เยอะเกิน = overhead จากการซิงค์ thread สำหรับโมเดลเล็กแบบนี้) เลยไม่ใช้ ปล่อยให้ ONNX Runtime auto-detect ตามเดิม
  - ยังไม่ได้ทำ streaming (ส่งเสียงทีละประโยคให้เล่นได้ก่อนประโยคหลังจะ synth เสร็จ) แม้ไลบรารีจะรองรับ (`voice.synthesize()` เป็น generator ทีละประโยคอยู่แล้ว) — เป็นตัวเลือกต่อไปถ้าอยากได้เร็วขึ้นอีกแบบ perceived latency แต่ต้องแก้ playback pipeline ฝั่ง client พอสมควร (คิวเล่นเสียงหลายชิ้น, sync กับกลไก mic-pause/follow-up window เดิม)
- Logic อยู่ที่ `tts.py` (`synthesize(text, voice, engine)` คืน `(ไบต์เสียง, media_type)`) เรียกผ่าน `POST /api/tts` ใน `server.py` — แคช `Voice` เองใน `_voice_cache` ต่อเสียง โหลดครั้งแรกที่ถูกเรียกใช้เท่านั้น (ไม่ใช่ทุก request)
- เสียงให้เลือก 4 แบบ: `th_f_1` (ค่าเริ่มต้น), `th_m_1`, `th_f_2`, `th_m_2` — เลือกได้จากเมนูมุมขวาบนของหน้าเว็บ จำค่าไว้ใน localStorage
- โมเดล ONNX ที่โหลดมาแคชไว้ที่โฟลเดอร์ `voices/` (ไม่ commit, อยู่ใน `.gitignore`) กับ `~/.cache/huggingface`
- **Dependency**: `vachanatts` (ตรงๆ ไม่ใช่ `pythaitts` แล้ว) — ดู `requirements.txt`
- **License**: Apache-2.0 (ใช้ได้อิสระ)

**Engine เสียงตัวที่ 2 (ทางเลือก): Google Translate TTS ผ่าน `gTTS`**
- ผู้ใช้ขอให้เพิ่มเป็น**ทางเลือกที่สลับไปมาได้** ไม่ใช่แทนที่ `vachana` — `tts.py`'s `synthesize()` รับพารามิเตอร์ `engine` (`"vachana"` ค่าเริ่มต้น หรือ `"google"`) คืน media_type ต่างกันตามจริง (`audio/wav` vs `audio/mpeg`) ฝั่ง client ไม่ต้องแก้อะไรเพิ่มเพราะ `res.blob()` เอา Content-Type จาก response header มาใช้ตรงๆ อยู่แล้ว
- UI: dropdown `#engineSelect` มุมขวาบน (เหนือ `#voiceSelect`) จำค่าไว้ใน `localStorage` key `jusmin_tts_engine` — ตอนเลือก `google` จะซ่อน `#voiceSelect` อัตโนมัติ (คลาส `.hidden`) เพราะรายชื่อเสียง `th_f_1` ฯลฯ มีความหมายเฉพาะ `vachana` เท่านั้น
- **ปัจจุบัน (ผู้ใช้ขอ): ค่าเริ่มต้นเป็น `google`** — `app.js` ตั้ง `let selectedEngine = localStorage.getItem('jusmin_tts_engine') || 'google'` (default google แต่สลับกลับ `vachana` ได้ + จำค่า)

## Sidebar (เมนู ⚙ ตั้งค่า)

ผู้ใช้ขอให้ย้ายเมนูที่เคยลอยมุมจอ (`#folderBtn` / `#engineSelect` / `#voiceSelect`) เข้ามาเป็น **เมนูย่อยของ "ตั้งค่า" ใน sidebar** แทน — เดิมเคยขอซ่อนทั้งหมด รอบนี้เอากลับมาแต่จัดใหม่

- **HTML** (`index.html`): ปุ่ม `#settingsBtn` (⚙, มุมขวาล่าง ที่ slot เดิมของ voice-select `bottom:212px right:24px` เหนือปุ่ม mute) + `<aside class="sidebar" id="sidebar">` สไลด์เข้าจากขวา + `<div class="sidebar-scrim">` ฉากหลังจางๆ กดปิด ข้างในเป็น `<details class="sidebar-group" open><summary>ตั้งค่า</summary>` ครอบ `.setting-item` 3 อัน (แต่ละอันมี `<label>` + control) — **id ของ control 3 ตัวเหมือนเดิมเป๊ะ** `app.js` เลยไม่ต้องแก้ตรรกะเดิม (`folderBtn`/`engineSelect`/`voiceSelect` ยัง `getElementById` เจอ)
- **CSS** (`style.css`): ลบ `display:none !important` + absolute positioning เดิมของ 3 control ออก เปลี่ยนเป็น `width:100%` block ใน `.setting-item`. เพิ่ม `.settings-btn` / `.sidebar` (`transform: translateX(100%)` → `.open` เป็น `0`) / `.sidebar-scrim` (`.visible`) / `.sidebar-group summary` (ซ่อน default marker ใช้ `▸` หมุน 90° ตอน `[open]`) — ธีมเดียวกับ HUD (cyan mono, พื้นโปร่งเบลอ)
- **JS** (`app.js`): `setSidebar(open)` toggle คลาส `.open`/`.visible`/`.active` + `aria-*` — เปิดด้วยปุ่ม ⚙, ปิดด้วยปุ่ม ✕ / คลิก scrim / กด `Escape`. `applyEngineUI()` เปลี่ยนจาก toggle `.hidden` บน `voiceSelect` เป็นบน `#voiceField` (ทั้งแถว label+select) ตอน engine ≠ vachana
- ตั้งโฟลเดอร์ file-access กลับมาทำผ่านหน้าเว็บได้แล้ว (ปุ่มอยู่ใน sidebar) — คู่กับ persistence ที่ทำไว้ ตั้งครั้งเดียวจำข้าม restart
- ข้อเสียของ Google engine (บอกผู้ใช้ไปแล้ว): endpoint ไม่เป็นทางการ ต้องมีเน็ต ปรับ noise/speed ผ่าน API ไม่ได้เหมือน vachana (Google TTS API มีแค่ normal/slow ไม่มี "เร็วขึ้น") และเสี่ยงโดน rate-limit ถ้าเรียกถี่ — เหมาะเป็น fallback/ของเล่นเปรียบเทียบมากกว่าใช้หลัก
- **ความเร็วพูดของ Google engine ช้ากว่า vachana มาก** — วัดจริงประโยคเดียวกัน: vachana ~3.66 วิ vs google ~6.79 วิ (ช้ากว่าเกือบ 2 เท่า) เพราะ Google TTS API ไม่มีพารามิเตอร์ปรับความเร็วแบบ vachana's `length_scale` แก้โดยเร่ง `ttsAudio.playbackRate = 1.4` ใน `app.js` เฉพาะตอน `selectedEngine === 'google'` เท่านั้น (vachana ยังคง 1.0 เหมือนเดิมเพราะปรับ SPEED ที่ต้นทางอยู่แล้ว) เบราว์เซอร์คง pitch อัตโนมัติเลยไม่ใช่เสียงเร่งเทปแบบตลก ไม่ต้องประมวลผลเสียงเพิ่มฝั่ง server เลย
- ติดตั้ง `gTTS` ดันให้ `click` conflict กับ `huggingface-hub` (ที่ `vachanatts` ใช้โหลดโมเดล) เล็กน้อยตาม pip resolver warning แต่ทดสอบจริงแล้วทั้งคู่ import/ทำงานได้ปกติไม่มีปัญหา (อัปเกรด `click` เป็น `>=8.4.2` ให้ `huggingface-hub` พอใจ แล้ว `gTTS` ก็ยังใช้ได้)

**บทเรียนตอน debug feature นี้ — อย่าเชื่อ error ที่มาจาก curl -d ข้อความไทยตรงๆ ใน Bash tool บน Windows:**
ตอนทดสอบเจอ `/api/tts` ตอบ 500 ทุกครั้งที่ส่งข้อความไทยสั้นๆ (เช่น "สวัสดี") ผ่าน `curl -d '{"text":"...ภาษาไทย..."}'` พร้อม traceback ลึกไปถึง `vachanatts/TH_G2P.py` (`IndexError: list index out of range` เพราะ `word_tokenize()` คืนลิสต์ว่าง) — ไล่หาสาเหตุอยู่นานมาก (ลอง thread lock ป้องกัน race ก็ยังไม่หาย) สุดท้ายพิสูจน์ได้ว่า **ต้นเหตุคือ Git Bash/Windows เข้ารหัสอาร์กิวเมนต์ `-d` ที่มีอักษรไทยผิดเพี้ยนเป็น `?` ล้วนๆ ก่อนถึง curl.exe เลย** (เหมือนปัญหา mojibake ที่เจอตอนต้น session แต่รอบนี้ไปทำ **request body ที่ส่งจริงพัง** ไม่ใช่แค่ปัญหาแสดงผลที่ console) ยืนยันได้ชัดโดยเขียน JSON body ลงไฟล์ UTF-8 ด้วย Write tool ก่อน แล้วยิงด้วย `curl --data-binary @file.json` แทน — หายขาดทันที เบราว์เซอร์จริง (`fetch()` + `JSON.stringify()`) เข้ารหัส UTF-8 ถูกต้องอยู่แล้ว ไม่เจอปัญหานี้เลย
**บทเรียน**: ทดสอบ API ที่รับข้อความไทยผ่าน `curl` บน Windows/Git Bash เสมอต้องส่งผ่าน `--data-binary @ไฟล์.json` (เขียนไฟล์ผ่าน Write tool ที่เป็น UTF-8 แท้) ห้ามใส่ข้อความไทยเป็น inline `-d '...'` ตรงๆ เด็ดขาด ไม่งั้นจะเจอ error ปลอมที่ดูเหมือนบั๊กจริงจังของ backend/library ทั้งที่จริงๆ แค่ shell เข้ารหัสอาร์กิวเมนต์พัง

## คลื่นเสียงรอบวง (wave-ring)

Bar 40 อันรอบ core ขยับตามข้อมูลจริง 2 แหล่งต่างกันตามสถานะ (ไม่ใช่ animation สุ่มเล่นๆ):
- **ตอนไมค์เปิดฟัง** (`isMicOpen()` true) — amplitude จริงจากไมค์ผ่าน `getUserMedia` + Web Audio `AnalyserNode` (`ensureMicAnalyser()`) แม่นยำเต็มที่
- **ตอน จัสมิน กำลังพูด** (`ttsSpeaking` true) — ตั้งแต่เปลี่ยนมาเล่นเสียงผ่าน `<audio>` element จริง (จาก `/api/tts`) เลยต่อ Web Audio `AnalyserNode` เข้ากับ `createMediaElementSource(ttsAudio)` ได้ตรงๆ (`ensureTtsAnalyser()`) — เป็น **amplitude จริงเหมือนฝั่งไมค์เป๊ะ** ไม่ใช่ของประมาณแบบตอนใช้ `speechSynthesis` (ที่ต้องอาศัย `onboundary` event มาขับคลื่นแทนเพราะดึง waveform จริงไม่ได้)

**สีของ core/wave/glow** — ผูกกับ `engagedActive` (ไม่ใช่แค่ไมค์เปิดหรือเปล่า และกว้างกว่า `followUpActive`):
- ตอนแค่เปิดไมค์รอฟังคำว่า "จัสมิน" เฉยๆ (ยังไม่ได้เรียก) → สีฟ้า (cyan) เดิม
- **พอได้ยินคำว่า "จัสมิน" ปุ๊บ** → เปลี่ยนเป็น**สีเขียว** (`--active-color`) ทันที ไม่ต้องรอคำตอบมาก่อน — ครอบคลุมช่วงกำลังประมวลผลและกำลังตอบด้วย
- ค้างเขียวต่อเนื่องได้ข้ามหลายรอบคุยต่อ (follow-up) โดยไม่กระพริบกลับ ตราบใดที่ยังคุยกันต่อภายใน 15 วิ
- ต่อเมื่อ**เงียบครบ 15 วิจริงๆ**หลัง จัสมิน ตอบครั้งล่าสุด (ไม่มีการคุยต่อ) ถึงจะกลับเป็นฟ้า ต้องพูด "จัสมิน" นำใหม่

`followUpActive` (ตัวเดิม) ยังใช้แยกต่างหากสำหรับคุมว่า "ไม่ต้องพูด จัสมิน ซ้ำไหม" ส่วน `engagedActive` คุมสีอย่างเดียว เริ่มไวกว่าและครอบคลุมกว้างกว่า

**แชท (`.log`) ก็ผูกกับ `engagedActive` ตัวเดียวกัน** — ซ่อนไว้เป็นค่าเริ่มต้น (`opacity:0` ใน `style.css`) โชว์เฉพาะตอนกำลังเรียก/คุยกับ จัสมิน จริง (`.chat-active` ถูก toggle ทุกเฟรมใน `renderWaveRing()`) หรือตอนเอาเมาส์ไปชี้ (`:hover` ล้วนๆ ฝั่ง CSS ไม่พึ่ง JS) เพื่อให้ hover ใช้ได้แม้ตอนซ่อนอยู่เลยไม่ใช้ `pointer-events:none`
- `engagedActive` ไม่ได้จำกัดแค่ voice/wake mode แล้ว — `form.addEventListener('submit', ...)` ตั้งเป็น `true` ทันทีตอนส่งข้อความ ไม่ว่าจะพิมพ์, กดพูด (push-to-talk), หรือสั่งผ่าน wake mode ก็ตาม แชทเลยโผล่มาให้เห็นทันทีที่เริ่มคุย ไม่ใช่แค่ตอนพูดคำว่า "จัสมิน" เท่านั้น
- `startFollowUpWindow()` ถูกเรียกไม่มีเงื่อนไข (`if (wakeMode)` เดิม) หลัง `speak()` จบทุกเส้นทาง รวมถึง error path (`catch` ใน submit handler) ด้วย — กันแชท/สีเขียวค้างตลอดไปถ้า request ล้มเหลว แต่ `followUpActive` (ข้อความ "ฟังต่อเนื่อง" + ไม่ต้องพูด "จัสมิน" ซ้ำ) ยังคงมีความหมายเฉพาะตอน `wakeMode` เปิดจริงเท่านั้น (`followUpActive = wakeMode` ใน `startFollowUpWindow()`) เพราะ text นั้นสื่อว่า STT กำลังฟังต่อเนื่องอยู่จริง ซึ่งเป็นจริงเฉพาะตอน wake mode เปิด
- **บั๊กจริงที่เจอ**: error handler ของ `recognition.onerror`/`wakeRecognition.onerror` (เช่น ไม่ได้สิทธิ์ไมค์ `not-allowed`) เรียก `addLine('จัสมิน', ...)` ตรงๆ โดยไม่ได้ตั้ง `engagedActive = true` ก่อน — ข้อความเลยถูกเพิ่มเข้า DOM จริงแต่ **มองไม่เห็น** (แชทซ่อนอยู่) ผู้ใช้เจอว่า "เรียก จัสมิน แล้วไม่มีอะไรเกิดขึ้นเลย" ทั้งที่จริงๆ จัสมิน พยายามแจ้ง error (เช่นสิทธิ์ไมค์หลุด) อยู่ แค่มองไม่เห็น — แก้โดยเพิ่มฟังก์ชัน `announceSystemNotice(text)` (`engagedActive = true` + `addLine()` + `startFollowUpWindow()`) แล้วเปลี่ยน error handler ทั้งหมดให้เรียกผ่านนี้แทน `addLine()` ตรงๆ — **บทเรียน**: ทุกจุดที่เพิ่มข้อความลง `.log` ต้องเช็คว่าตั้ง `engagedActive` ไว้ก่อนเสมอ ไม่งั้นข้อความจะถูกซ่อนแบบเงียบๆ โดยไม่มี error ให้เห็นเลย

## เข้าถึงไฟล์ในคอม (`list_files()` / `read_file()` / `create_folder()` / `write_file()` / `delete_path()`) + ตำแหน่งที่ตั้ง

ผู้ใช้ขอให้ จัสมิน "เข้าถึงข้อมูลในคอมได้" ชัดเจนว่า**ต้องจำกัดแค่โฟลเดอร์ที่กำหนดไว้เท่านั้น** ไม่ใช่ทั้งเครื่อง — ถามต่อว่าจะเลือกโฟลเดอร์ยังไง ผู้ใช้ตอบว่า "เลือกผ่าน UI เลย" ไม่ใช่พิมพ์ path เอง

**สถาปัตยกรรม — native folder picker ผ่าน server (ไม่ใช่ browser File System Access API):**
- ปัญหา: เบราว์เซอร์ไม่มีทางให้เว็บเพจรู้ **absolute path จริง** ของโฟลเดอร์ที่ผู้ใช้เลือกได้เลย (ทั้ง `<input type="file" webkitdirectory>` ที่ให้แค่ path ปลอม `C:\fakepath\...` และ `window.showDirectoryPicker()` ที่ให้แค่ handle ใช้อ่านไฟล์ผ่าน JS ได้ แต่ไม่บอก path จริง) — เป็นข้อจำกัดด้าน privacy ของเบราว์เซอร์เอง ไม่ใช่บั๊ก
- แก้โดยใช้ **`tkinter.filedialog.askdirectory()`** (มากับ Python อยู่แล้ว ไม่ต้องลง lib เพิ่ม) เปิด native "Browse for Folder" dialog ของ **Windows จริงๆ** ผ่าน endpoint ใหม่ `POST /api/browse_folder` ใน `server.py` — ใช้ได้เพราะตอนนี้ server กับเบราว์เซอร์ของผู้ใช้รันอยู่บนเครื่องเดียวกัน **ถ้าย้ายไป Pi ในอนาคตกลไกนี้ใช้ไม่ได้แล้ว** (Pi ไม่มีจอ/ไม่ได้เห็น dialog ที่ popup) ต้องคิดใหม่ตอนนั้น (เช่น list โฟลเดอร์ที่ Pi เข้าถึงได้ให้เลือกจาก dropdown แทน)
- เป็น blocking call (`askdirectory()` รอ user โต้ตอบ) — ฝั่ง `app.js` disable ปุ่มไว้ระหว่างรอ ไม่กระทบ request อื่นเพราะ FastAPI รัน sync endpoint ผ่าน threadpool คนละ thread กัน
- ทดสอบแล้วว่า `tkinter.Tk()` สร้าง/ทำลายจาก background thread (จำลอง thread ที่ FastAPI ใช้จริง) ไม่ throw error บน Windows เครื่องนี้ — ส่วนตัว dialog ที่ popup จริงต้องให้ผู้ใช้กดทดสอบเองเพราะ automate ไม่ได้ (ต้องมีคนคลิกจริง)
- path ที่เลือกเก็บไว้ที่ `_allowed_folder` (ตัวแปร module-level เดียวใน `tools.py` เหมือน state อื่นๆ — personal use คนเดียว)
- **จำข้าม restart แล้ว**: `set_allowed_folder()` เขียน path ลง `jusmin-ai/file_access_config.json` (`{"allowed_folder": "..."}`, อยู่ใน `.gitignore` เพราะเป็น absolute path เฉพาะเครื่อง ไม่ใช่ค่าที่ควร commit) — พอ `tools.py` ถูก import ตอน server เริ่ม `_restore_allowed_folder_from_config()` จะอ่านกลับมาให้ **ถ้าโฟลเดอร์นั้นยังมีอยู่จริง** (`os.path.isdir()`); ถ้าโดนลบ/ย้าย/ถอด drive ไปแล้วก็ข้ามเงียบๆ (ผู้ใช้กดปุ่ม 📁 เลือกใหม่ได้) ตอน restore จะเปิด activity log ไฟล์ใหม่ด้วย `action="folder_restored"` (แยกไฟล์ต่อรอบการรัน server เหมือน `folder_selected`) — ปุ่มบนหน้าเว็บอัปเดตเองอยู่แล้วเพราะ `refreshFolderStatus()` ยิง `/api/file_access_status` ทุกครั้งที่โหลดหน้า

**Security — จุดสำคัญที่สุดของ tool ชุดนี้:**
- ทุก path จาก LLM ต้อง resolve เป็น absolute path จริงก่อน (`os.path.realpath`) แล้วเช็คด้วย **`os.path.commonpath()`** ว่ายังอยู่ใต้ `_allowed_folder` เป๊ะๆ — **ห้ามใช้ `str.startswith()` เทียบ prefix ตรงๆ เด็ดขาด** เพราะมีบั๊กคลาสสิก: โฟลเดอร์ `C:\allowed` จะ match ผิดกับ `C:\allowed-secret` (คนละโฟลเดอร์กันเลยแต่ชื่อขึ้นต้นเหมือนกัน) — ทดสอบสถานการณ์นี้จริงแล้วยืนยันว่า `commonpath()` บล็อกถูกต้อง ส่วน `startswith()` จะหลุด
- ทดสอบ path traversal (`../`, `../../`) และ absolute path นอกขอบเขตแล้ว บล็อกถูกต้องหมด
- `read_file()` จำกัดนามสกุลไฟล์ที่อ่านได้แค่ text-based เท่านั้น (`.txt`, `.md`, `.csv`, `.json`, `.py` ฯลฯ ดู `_ALLOWED_TEXT_EXTENSIONS`) กันอ่านไฟล์ไบนารี/รูปภาพ/exe ออกมาเป็นขยะหรือเสี่ยงข้อมูลผิดปกติ และจำกัดขนาดอ่านไว้ที่ `_MAX_FILE_READ_BYTES = 200_000` (~200KB) กันไฟล์ใหญ่บวม context ของ Gemini
- `list_files()` จำกัดจำนวนรายการที่แสดงไว้ 200 รายการ กันโฟลเดอร์ใหญ่มากตอบยาวเกินไป
- ก่อนตั้งค่าโฟลเดอร์ (`_allowed_folder` เป็น `None`) ทั้งสอง tool ตอบข้อความบอกให้ไปกดปุ่มเลือกโฟลเดอร์ก่อน ไม่ error ดิบๆ

**UI**: ปุ่ม `📁 เลือกโฟลเดอร์` มุมขวาบน (เหนือ engine-select) โชว์ชื่อโฟลเดอร์ปัจจุบันถ้าตั้งค่าแล้ว (ตัด path เหลือแค่ชื่อโฟลเดอร์สุดท้าย, ดู path เต็มได้จาก tooltip) sync สถานะจริงจาก `/api/file_access_status` ทุกครั้งที่โหลดหน้าเว็บ (ไม่ใช่จำไว้ฝั่ง browser เฉยๆ เพราะ server คือคนตรวจ path จริงตอนถูกเรียกใช้งาน ต้องตรงกับสิ่งที่ server ใช้งานจริงเสมอ)

**เขียน/แก้ไข/ลบไฟล์ (`create_folder()` / `write_file()` / `delete_path()`)** — ต่อยอดจาก `list_files()`/`read_file()` เดิม ใช้ `_resolve_safe_path()` (containment check ด้วย `commonpath()`) ตัวเดียวกันเป๊ะๆ เลยได้ security guarantee เดียวกันฟรีๆ (traversal, sibling-prefix folder ฯลฯ):
- `write_file(path, content)` **เขียนทับทั้งไฟล์เสมอ** ไม่มีโหมด append/patch บางส่วน — ถ้า LLM จะแก้ไฟล์เดิม docstring สั่งให้ `read_file()` อ่านเนื้อหาเดิมมาก่อนเสมอ แล้วส่งเนื้อหาฉบับเต็มที่แก้แล้วมาเขียนทับ (ไม่ใช่ diff) จำกัดนามสกุลไฟล์ที่เขียนได้ด้วย whitelist เดียวกับ `read_file()` (`_ALLOWED_TEXT_EXTENSIONS`) กันเขียนไฟล์ไบนารี/exe
- `create_folder(path)` ใช้ `os.makedirs(..., exist_ok=True)` สร้างโฟลเดอร์แม่ที่ยังไม่มีให้อัตโนมัติด้วย
- `delete_path(path)` **ลบถาวร กู้คืนไม่ได้** (`shutil.rmtree` ถ้าเป็นโฟลเดอร์, `os.remove` ถ้าเป็นไฟล์) — docstring เขียนกำกับชัดว่าห้ามเรียกเองถ้าไม่แน่ใจว่าผู้ใช้ตั้งใจจะลบจริงๆ ให้ถามยืนยันก่อนถ้าคำสั่งกำกวม (ไม่มี confirmation flow แยกต่างหากในโค้ด — docstring คือกลไกคุมพฤติกรรม LLM ตัวเดียวที่มี เหมือน `control_youtube`) และ**ปฏิเสธการลบโฟลเดอร์หลักที่อนุญาตไว้ทั้งก้อนเสมอ** (เทียบ `target == os.path.realpath(_allowed_folder)`) กันลบขอบเขตทั้งหมดทิ้งโดยไม่ตั้งใจ
- ทดสอบ adversarial ครบชุดเดียวกับของเดิม (traversal, sibling-prefix folder, disallowed extension) บวกเคสใหม่เฉพาะกลุ่มนี้ (ลบไฟล์, ลบโฟลเดอร์ไม่ว่างแบบ recursive, ปฏิเสธลบ root, ลบ path ที่ไม่มีอยู่จริง) รวม 35 เคส ผ่านหมด

**Audit log (JSON)** — ทุกครั้งที่เลือกโฟลเดอร์ใหม่ผ่านปุ่ม 📁 (`set_allowed_folder()` ใน `tools.py`) จะสร้างไฟล์ log ใหม่ **แยกไฟล์ต่อรอบ** ที่ `logs/file_activity_<YYYYMMDD_HHMMSS>.json` (ไม่ทับของเดิม — เลือกโฟลเดอร์ใหม่กี่ครั้งก็มีไฟล์ log สะสมไว้ครบทุกรอบ) แต่ละ entry บันทึก `timestamp`, `action` (`list_files`/`read_file`/`create_folder`/`write_file`/`delete_path`/`folder_selected`), `path`, `success`, `detail` (เหตุผลตอน fail เช่น "outside allowed scope", "disallowed extension .exe") — บันทึกทั้งเคสสำเร็จและล้มเหลว ไม่ใช่แค่ที่ทำสำเร็จ เพื่อให้ตรวจสอบย้อนหลังได้ว่า จัสมิน เคยพยายามทำอะไรบ้าง ไฟล์ log เก็บเป็น array เดียวเขียนทับทั้งไฟล์ทุกครั้งที่มี entry ใหม่ (ไม่ใช่ append แบบ NDJSON) เพราะไฟล์เล็ก (การใช้งานส่วนตัวคนเดียว ไม่ได้ concurrent เขียนพร้อมกันหลาย request) — โฟลเดอร์ `logs/` อยู่ใน `.gitignore` แล้ว ไม่ commit ขึ้น git

## กลุ่ม tool เลขา (memory / tasks / reminders / email / daily_briefing)

ผู้ใช้ขอให้ จัสมิน เป็น "เลขาสมบูรณ์" — เริ่มจาก **กลุ่ม A**: ความจำถาวร + ตารางงาน + การเตือน + อีเมล + สรุปวัน
ทั้งหมด server-side ล้วน (คืน string ให้ LLM เรียบเรียง) ยกเว้น "การเตือนเด้ง" ที่ใช้ notification channel แยก

**DB — `jusmin-ai/jusmin.db` (SQLite, `tools/db.py`)**
- path คิดจาก project dir แบบเดียวกับ `tools/files.py` (`_PROJECT_DIR = dirname(dirname(abspath(__file__)))`) — อยู่ใน `.gitignore`
- `connect()` เปิด connection ใหม่ทุก operation (`timeout=5`, `row_factory = sqlite3.Row`) — personal use คนเดียว ไม่ต้อง pool
- `query(sql, params)` → `fetchall()`; `execute(sql, params)` → `(lastrowid, rowcount)` + commit
- `_init()` รัน `executescript(_SCHEMA)` ตอน import — 3 ตาราง `CREATE TABLE IF NOT EXISTS`: `memory`, `tasks`, `reminders`
- ลบไฟล์ `jusmin.db` ทิ้ง = ล้างความจำ/งาน/การเตือนทั้งหมด (สร้างใหม่อัตโนมัติรอบ import ถัดไป)

**`tools/memory.py`** — `remember(fact, tag="")` / `recall(query="")` / `forget(query)`
- ค้นด้วย `LIKE` (fact น้อย ไม่ต้อง FTS5), `recall` LIMIT 40, `forget` = `DELETE ... LIKE` คืนจำนวนที่ลบ
- **`memory_preamble()`** (ไม่ใช่ tool) — คืน block สั้นๆ ของ fact ทั้งหมด หรือ `""` ถ้าไม่มี — `server.py`'s `chat_endpoint`
  เอาไป **prepend หน้า `req.message` ทุกเทิร์น** ก่อน `chat.send_message()` → จัสมิน เห็น fact เสมอ + fact ที่เพิ่ง
  `remember()` มีผลทันทีในเซสชันเดียวกัน (ยอม redundant ใน history เล็กน้อย แลกกับไม่ต้อง restart) — `system_instruction` เดิมไม่แตะ
- **`_now_preamble()`** (ใน `server.py`) — prepend หน้า `req.message` ทุกเทิร์นเหมือนกัน คืนบรรทัด "เวลาปัจจุบัน..."
  (Thai date + ISO). **จำเป็น** เพราะ Gemini ไม่รู้เวลาจริงเอง ถ้าไม่บอกจะเดา (มักอิงยุค training data → เพี้ยนเป็นปีก่อน)
  ทั้งตอนตอบ "กี่โมงแล้ว" และตอนแปลง "อีก 15 นาที" / "พรุ่งนี้ 9 โมง" เป็น ISO ให้ `add_reminder`/`add_task`.
  ใช้ `datetime.now()` = เวลาเครื่องที่รัน server (ตอนนี้ = เครื่องผู้ใช้ ถูกต้อง); HUD clock ฝั่งเว็บใช้ `new Date()` แยกต่างหาก
- ล้าง `tools.set_client_location(None)` ใน `finally` ทำเหมือนเดิม — preamble ไม่ต้องล้างเพราะ prepend ใหม่ทุกเทิร์นอยู่แล้ว

**`tools/tasks.py`** — `add_task(text, due="", priority="normal")` / `list_tasks(which="open")` / `complete_task(query)`
- `due` = ISO string หรือ `""` (docstring สั่ง LLM แปลงเวลาที่ผู้ใช้พูดกำกวมเป็น ISO ก่อน); `priority` ∈ {low, normal, high}
- `which` ∈ open / today / done / all — `today` = `done=0 AND due_at!='' AND substr(due_at,1,10)<=?`
- `complete_task(query)` = ถ้า `#<เลข>` ใช้ id ตรงๆ ไม่งั้น LIKE match; **ปฏิเสธถ้า match >1 แถว** (ให้ผู้ใช้ระบุให้ชัด)

**`tools/reminders.py`** — `add_reminder(text, when_iso)` / `list_reminders()` / `cancel_reminder(query)` + `check_due()`
- `_parse(when_iso)` = `datetime.fromisoformat` (fallback แทน `" "` เป็น `"T"`), คืน `None` ถ้า parse ไม่ได้
- `add_reminder` ปฏิเสธเวลาที่ parse ไม่ได้ / เป็นอดีต (คืน error ให้ LLM ถามใหม่)
- **`check_due()`** (scheduler เรียก ไม่ใช่ tool) : `WHERE fired=0 AND remind_at<=now` → mark `fired=1` → `notify.push(text, "reminder")`

**scheduler thread (`server.py`, module scope)**
```python
def _scheduler_loop():
    while True:
        try: tools.reminders.check_due()
        except Exception: pass
        time.sleep(20)
threading.Thread(target=_scheduler_loop, daemon=True, name="jusmin-scheduler").start()
```
- `daemon=True` ตายพร้อม process, วนทุก ~20 วิ — ไม่มี persistence ของ timer เอง (state อยู่ใน DB ทั้งหมด) restart server แล้ว reminder ที่เลยเวลายังเด้งอยู่ (เพราะ `remind_at<=now` ยังจริง)

**notification channel (reminder เด้งเฉพาะตอนเปิดหน้าเว็บ — ผู้ใช้เลือกเอง ไม่ทำ Windows toast)**
- `tools/notify.py` = queue + `threading.Lock`. `push(text, kind="reminder")` เก็บ `{text, kind, at}`; `drain()` คืนทั้งหมด + เคลียร์
- `GET /api/notifications` (`server.py`) → `{"items": tools.notify.drain()}` + `Cache-Control: no-store`
- `static/js/notify.js` — poll ทุก 10 วิ, แต่ละ item เรียก `announceSystemNotice('⏰ ' + text)` (reuse ของเดิม — ตั้ง `engagedActive` ให้แชทโผล่),
  แล้ว `speak()` ตัวสุดท้าย. import ใน `main.js` แบบ side-effect (`import './notify.js';`)
- เหตุผลที่ **ไม่ใช้ `_state.pending_action`** — reminder เด้งมาจาก scheduler thread คนละ context กับ chat turn เลย
  ส่งผ่าน queue แยกเหมาะกว่า (pending_action เป็น slot เดียวผูกกับ response ของ `chat_endpoint`)

**`tools/mail.py`** (ห้ามชื่อ `email.py` — ชน stdlib) — `check_email(n=5, folder="inbox")` / `read_email(query, folder="")` / `search_email(query, folder="all", limit=10)` / `save_attachment(query, name="", dest="")` / `send_email(to, subject, body, attachments="", confirm=False)`
- imaplib/smtplib + `email` stdlib ล้วน ไม่ต้อง API key — config จาก `.env`: `EMAIL_ADDRESS` / `EMAIL_APP_PASSWORD` (Gmail App Password)
  / `EMAIL_IMAP_HOST` (default imap.gmail.com) / `EMAIL_SMTP_HOST` (default smtp.gmail.com) / `EMAIL_SMTP_PORT` (default 587, STARTTLS)
- **`_cfg()` อ่าน `os.environ` ตอนเรียกใช้ ไม่ใช่ตอน import** — เพราะ `tools/` ถูก import ก่อน `load_dotenv()` ใน `server.py`;
  ไม่ตั้งค่า → ทุก tool คืนข้อความ `_NOT_SET` ไม่ error. `_cfg()` `"".join(...split())` ตัดช่องว่างใน App Password (Google โชว์เป็น 4 กลุ่ม)
- **ครอบคลุมทุกกล่อง** — `folder` รับได้ inbox/sent/drafts/all/spam/trash/starred + คำไทย (`_ALIAS`: "ที่ส่ง"→sent, "ถังขยะ"→trash, ...).
  หากล่องจริงจาก **IMAP SPECIAL-USE flag** (`\Sent \Drafts \All \Junk \Trash \Flagged`) ผ่าน `m.list()` → localization-proof
  (ไม่ยึดชื่อ `[Gmail]/Sent Mail` ที่เปลี่ยนตามภาษาบัญชี); fallback = ชื่ออังกฤษ `_GMAIL_NAME`
- **ค้นหา** `_search_seqs()` — Gmail (`_is_gmail()`) ใช้ **`X-GM-RAW`** = พิมพ์ `from: to: in:sent subject: after: has:attachment` ได้เต็มรูปแบบ
  (ascii → quoted string, ไทย → `m.literal` + `CHARSET UTF-8`); ไม่ใช่ Gmail → `(OR OR OR FROM TO CC SUBJECT)` หรือ `TEXT` literal สำหรับไทย
- `check_email`: inbox = `UNSEEN` + `BODY.PEEK` (**ไม่ mark read**); กล่องอื่น = `_newest_seqs(count, n)` เอา n ฉบับท้ายจาก EXISTS count (ไม่ SEARCH ALL)
- แถวลิสต์ (`_fmt_row`) โชว์ **"ถึง <ผู้รับ>" ถ้าเป็นเมลที่เราส่งเอง** (`my_addr in From` หรือ folder=sent/drafts) ไม่งั้น "จาก <ผู้ส่ง>"
- `read_email` = ลำดับจาก `_last_uids` (ต้องกล่องเดียวกับ `_last_mailbox`) หรือ search; folder ว่าง + อ้างด้วยคำ → ค้น All Mail (Gmail); `RFC822` fetch **mark read**; `_plain_body()` text/plain ก่อน, ตัด 4000.
  ต่อท้ายด้วยบรรทัด "ไฟล์แนบ: ..." ถ้ามี (`_iter_attachments()`)
- `_last_uids` + `_last_mailbox` (module global) — seq number ผูกกับกล่อง ต้อง track คู่กัน
- **ไฟล์แนบ ผูกกับ tool ไฟล์ในคอม** (`from . import files`) — เข้า/ออกได้เฉพาะในโฟลเดอร์ที่ผู้ใช้อนุญาต (ปุ่ม 📁), ผ่าน `files._resolve_safe_path()` (containment ด้วย `commonpath()`) + `files._log_activity("save_attachment"/"email_attach", ...)` ลง audit log เดียวกัน. เพดาน 25MB/ไฟล์
  - `save_attachment(query, name, dest)` — fetch RFC822 → `_iter_attachments()` (part ที่มี filename/`Content-Disposition: attachment`) → `_safe_name()` (basename, ตัด `..`/อักขระต้องห้าม Windows) → `_uniq()` (เติม " (2)" กันทับ) → เขียน bytes. `name` = filter substring, `dest` = โฟลเดอร์ย่อยปลายทาง
  - `send_email(..., attachments="a.pdf, ง/b.png")` — `_resolve_attachments()` resolve แต่ละ path → อ่าน bytes → เดา MIME (`mimetypes`) → `em.add_attachment()`. ไฟล์หาไม่เจอ/นอกขอบเขต/ใหญ่เกิน → พรีวิวโชว์ ⚠️ + **confirm ไม่ผ่าน** (ต้องแก้ก่อน). `att_key` (tuple paths sorted) รวมอยู่ใน `_pending_send` เทียบ `same` ด้วย
- **ลายเซ็นอัตโนมัติ** (ผู้ใช้ขอ) — `_with_signature()` ต่อท้าย `body` ทุกฉบับก่อนพรีวิว/เทียบ/ส่ง:
  `"—\nนี่คือการส่งอีเมลจาก J.U.S.M.I.N ผู้ช่วย AI ของคุณ\n<ชื่อ>"` โดย `<ชื่อ>` = `EMAIL_SENDER_NAME` ใน `.env` หรือ `cfg["addr"]`.
  กันต่อซ้ำด้วยการเช็ค `_SIG_MARKER` ในตัว body (LLM อาจ echo ลายเซ็นจากพรีวิวกลับมาตอน confirm). docstring บอก LLM ว่าไม่ต้องเขียนลายเซ็นเอง
- `send_email(to, subject, body, confirm=False)` — **บังคับ 2 ขั้นในโค้ดจริง ไม่ใช่แค่ docstring**: เก็บร่างใน
  `_pending_send` (module global, TTL 600 วิ) ตอนพรีวิว → "ส่งจริง" ได้ต่อเมื่อเรียกซ้ำด้วย `confirm=True` **และ**
  to/subject/body ตรงกับร่างที่เพิ่งทวนเป๊ะ (`_norm_to()` sort ผู้รับก่อนเทียบ). ยิง `confirm=True` มาแต่ครั้งแรก
  (ไม่มีร่างค้าง) → ยังเป็นพรีวิว ไม่ส่ง; เนื้อหา drift จากร่าง → พรีวิวใหม่ ไม่ส่ง; ส่งเสร็จเคลียร์ `_pending_send`
  กันส่งซ้ำ. validate `"@" in to`. Gmail เซฟลง Sent เอง; ผู้ให้บริการอื่นทำ `IMAP APPEND` ลง `\Sent` เอง (best-effort)
- **`unread_count()`** (ไม่ใช่ tool) — คืน `int` (inbox UNSEEN) หรือ `None` ให้ `daily_briefing` ใช้

**`tools/briefing.py`** — `daily_briefing()`
- ประกอบ string ก้อนเดียว: วันที่ไทย (`_THAI_WD`/`_THAI_MONTH`) + งานครบกำหนดวันนี้/เลยกำหนด + งาน priority=high ที่ค้าง
  + การเตือนที่เหลือวันนี้ + `mail.unread_count()` (ข้ามถ้า `None`)
- docstring สั่ง LLM **หลังได้ผลให้เรียก `get_weather()` เพิ่มแล้วเรียบเรียงรวมเป็นบทพูดสั้นๆ** (อย่าอ่านเป็นลิสต์แข็งๆ)

**การ wire เข้า `server.py`**
- `from tools import (... add_reminder, add_task, cancel_reminder, check_email, complete_task, daily_briefing, forget,
  list_reminders, list_tasks, read_email, recall, remember, search_email, send_email ...)`
- `chat = client.chats.create(tools=[... + remember, recall, forget, add_task, list_tasks, complete_task,
  add_reminder, list_reminders, cancel_reminder, check_email, read_email, search_email, send_email, daily_briefing])`
  → รวมเป็น **23 tools** (tools list ยาวขึ้น Gemini อาจช้าลงนิด — เฝ้าดู)
- `tools/__init__.py` re-export ทุกชื่อ + `from . import notify, reminders` (submodule ให้ `server.py` เรียก `tools.notify` / `tools.reminders`)
- **ไม่แตะ `requirements.txt`** — sqlite3 / imaplib / smtplib / email / threading เป็น stdlib ทั้งหมด
- **ไม่เพิ่ม tool กลุ่มนี้ใน `jusmin.py` (CLI)** — เหตุผลเดียวกับ youtube/weather: memory/tasks/email ใช้ได้ แต่ reminder เด้งต้องมีหน้าเว็บ poll ถึงจะครบ ทำครึ่งๆ ใน CLI จะสับสน

**personality.py** — เติมย่อหน้าใน `SYSTEM_PROMPT` บอก persona ว่าจำเรื่องผู้ใช้ได้ / จดงาน / ตั้งเตือน / เช็ค-ส่งเมล / สรุปวันได้
+ ให้ `remember()` ข้อมูลส่วนตัวที่น่าจะใช้ภายหลังเอง + แปลงเวลากำกวมเป็น ISO ก่อนเรียก tool + ส่งเมลต้องทวนยืนยันก่อน

## `read_url` + `analyze_image` (Phase 1 · Tier 1 · plan `plans/01-read-url-analyze-image.md`)

สอง tool แรกของแผน "จัสมิน ระดับ Jarvis" (ดู `../ROADMAP.md`). chat session = **26 tools** หลังเพิ่ม 2 ตัวนี้

**`read_url(url)` — `tools/web.py`** (ข้าง `search_web`) · dep ใหม่: `trafilatura` (ฟรี ไม่ต้อง key)
- ใช้เมื่อผู้ใช้ให้ลิงก์แล้วขอ อ่าน/สรุป/ตอบจากหน้านั้น — SYSTEM_PROMPT สั่งว่า "อย่าเดาจากตัว URL"
- **`_normalize_url()`** — percent-encode path/query ที่มีอักขระ non-ASCII (URL ไทยที่ paste มาดิบ) + IDNA hostname + ตัด fragment · `%` อยู่ใน `safe` เลยไม่ double-encode ลิงก์ที่ encode มาแล้ว
- **`_url_is_safe()` = SSRF guard** — ต้อง http/https + `socket.getaddrinfo(host)` แล้วเช็คทุก IP ที่ resolve ได้ ปฏิเสธถ้าเป็น `is_private / is_loopback / is_link_local / is_reserved / is_multicast / is_unspecified` — กัน LLM ชี้ url ไป `127.0.0.1:8000` (server ตัวเอง), `169.254.169.254` (cloud metadata), IP ในวง LAN · **ข้อจำกัดที่ยอมรับ:** ยังมีช่อง TOCTOU + redirect ตาม (trafilatura ไม่เปิดให้ปิด redirect) — พอสำหรับใช้ส่วนตัวในบ้าน
- `trafilatura.fetch_url(url, config=_tf_cfg)` (timeout 10 วิ แทน default 30) → `trafilatura.extract(html, include_comments=False, include_tables=True, favor_precision=True)` · หัวข้อจาก `extract_metadata().title` · ตัดที่ `_MAX_URL_CHARS = 8000`
- error ทุกแบบ (SSRF / โหลดไม่ได้ / ไม่มีบทความ / ต้องรัน JS) → คืน string graceful · **ไม่มี `pending_action`** — Gemini สรุปเอง

**`analyze_image(path, question="")` — `tools/vision.py` (ไฟล์ใหม่)** · ดูรูปด้วย Gemini multimodal
- **security = ตัวเดียวกับ file tools** — `files.get_allowed_folder()` + `files._resolve_safe_path(path)` (containment ด้วย `commonpath()`) + `files._log_activity("analyze_image", ...)` ลง audit log เดียวกัน · จำกัด ext `.png/.jpg/.jpeg/.webp` (+`.gif/.bmp/.tiff` ถ้ามี Pillow)
- **nested Gemini call** — tool function รันซ้อนอยู่ใน automatic function calling ของ `chat` อยู่แล้ว จะแทรกรูปเข้า `chat` โดยตรงไม่ได้ เลยยิง `client.models.generate_content()` ของตัวเอง · **`_get_client()` = client แยกแบบ lazy** (อ่าน `GEMINI_API_KEY` ตอนเรียก เหมือน `mail.py`) — กัน circular import (server.py import tools)
- call config: `system_instruction` "ตอบไทยสั้น ไม่มี markdown" (ผลลัพธ์ป้อนกลับเข้า chat ให้ จัสมิน เรียบเรียง) + `automatic_function_calling(disable=True)` (ไม่มี tool + กัน warning รก log)
- รุ่น: `os.environ.get("VISION_MODEL", "gemini-3.5-flash-lite")` — **`-flash-lite` รับรูปได้อยู่แล้ว** (ทดสอบจริง) · env var ไว้เผื่อบัญชีไหนรุ่น default ไม่รับ ให้ตั้ง `gemini-3.5-flash`
- Pillow (optional, อยู่ใน `requirements.txt`): มี → `_prep_bytes()` ย่อด้านยาว > 1024px + แปลง mode/format ก่อนส่ง (ประหยัด token/quota) · ไม่มี → ส่งดิบ + reject ext ที่ต้องแปลง + reject > 12MB
- **quota drift ที่ยอมรับ**: call ตัวนี้ไม่ถูกนับใน `quota_state["used_today"]` ของ `server.py` (นับแค่ `chat.send_message`)

**`.env`**: `VISION_MODEL=` (ไม่บังคับ) · **`requirements.txt`**: +`trafilatura` +`Pillow` (Pillow มีคอมเมนต์ว่าไม่บังคับ)

## ค้น / ดาวน์โหลด / เปิดดู รูป+วิดีโอ (Phase 1 · plan `plans/02-media.md`)

3 tool ใน **`tools/media.py`** (ใหม่) · chat = **29 tools** · dep ใหม่: `imageio-ffmpeg` (bundled ffmpeg binary — yt-dlp ต่อ video+audio ของ YouTube ยุคใหม่ที่ progressive ถูกถอดแล้ว)

**`search_media(query, kind="image")`**
- `image` → `ddgs.images(max_results=12)` (retry 1 ครั้ง) · `video` → **`yt-dlp ytsearch{8}`** (`_yt_search_videos` — `ddgs.videos` เทสแล้วคืน `No results` ตลอด, yt-dlp เชื่อถือได้กว่า + โหลดได้จริง)
- normalize → `{n, kind, title, thumb, url, page, source, duration?}` · เก็บ `_last_results`/`_last_kind` (module global) ให้ `#N` อ้าง
- `_state.pending_action = {"type":"show_media_results", "kind", "query", "items":[...]}` → HUD grid · `_norm_kind` map คำไทย ("รูป"/"คลิป"/"วิดีโอ")

**`download_media(ref, dest="")`**
- `ref` = `"#3"` / `"1,3,5"` / `"all"` / `"current"` (อันที่เปิดใน viewer) / URL เต็ม (`_resolve_refs` + `_sniff_kind` เดา image/video จาก host+ext)
- `dest` = โฟลเดอร์ย่อยที่ **จัสมิน เลือกเอง** (ผู้ใช้สั่ง) · `files._resolve_safe_path(dest)` บังคับ containment + `os.makedirs`
- **รูป (sync)**: `web._url_is_safe` (SSRF, reuse) → `requests.get(stream)` → เช็ค `Content-Type: image/*` → ext จาก content-type → `files._safe_name`+`files._uniq` → soft-ceiling 60MB (abort+ลบ) → `files._log_activity`. โหลดเสร็จ **auto-open viewer** (`_show_viewer`)
- **วิดีโอ (async)**: `threading.Thread(daemon)` → `yt_dlp.YoutubeDL` (`_FFMPEG` = system ffmpeg หรือ `imageio_ffmpeg.get_ffmpeg_exe()`; มี ffmpeg → `bestvideo*+bestaudio` merge mp4, ไม่มี → `best[acodec!=none][vcodec!=none]`) → เสร็จ `notify.push(...,"media")` → `notify.js` พูด. `_video_jobs` set จำกัด 2 อันพร้อมกัน
- คืน string สรุปทันที (วิดีโอไม่รอ)

**`view_media(target="", action="open", seconds=0)`**
- `action`: open / close (ปิด viewer + grid) / next / prev / **slideshow** (เล่นวนอัตโนมัติ) / **stop** (หยุดสไลด์ ยังดูค้าง) · `seconds` = ช่วงสไลด์ (default 6)
- `target`: `"#N"` (เปิด**จากเว็บตรงๆ** ไม่โหลด, gallery = ผลค้นทั้งชุด) · path ไฟล์ที่โหลดมา · **ชื่อโฟลเดอร์** (`_local_gallery` → รูป/วิดีโอทุกไฟล์ในนั้น เรียงชื่อ) · `""`/`"current"` (viewer ที่ค้างอยู่ ไม่งั้นผลค้นล่าสุด)
- `search_media` `_viewer_list.clear()` ทุกครั้ง → "เล่นสไลด์"/"เปิด" แบบไม่ระบุ target หลังค้น = อิงผลค้นชุดใหม่
- `_show_viewer(items, index, slideshow=0)` ส่ง **`{"type":"show_media", "index", "list":[...], "slideshow": N}`** — gallery ทั้งชุดทีเดียว → HUD เลื่อน prev/next + เล่นสไลด์ (`setInterval`, วนด้วย modulo) ในเครื่องเอง ไม่ต้อง round-trip (voice "ถัดไป"/"หยุด" ยังผ่าน server ได้) · เลื่อนเองระหว่างสไลด์ = รีเซ็ตนาฬิกา เล่นต่อ
- `_local_item`/`_remote_item` → `{src, kind, name, source, page, ref?}` · `ref` (ลำดับใน `_last_results`) มีเฉพาะผลค้น → ปุ่ม "⬇ ดาวน์โหลด" ใน viewer โผล่เฉพาะกรณีนั้น (กดแล้ว client สั่ง "โหลดอันที่ N")

**Endpoint `GET /api/media?path=`** (`server.py`) — `tools.files._resolve_safe_path(path)` เช็ค containment ฝั่ง server เอง (ห้ามเชื่อ query param) + ext ∈ `_MEDIA_EXTS` (รูป+วิดีโอ) → `FileResponse` (รองรับ `Range` เอง → `<video>` seek ได้) · ไม่มี auth (personal-use/localhost)

**HUD** — `static/js/media.js` + `static/css/media.css` (`@import` ใน style.css ก่อน core.css) + markup `#mediaGridPanel`/`#mediaViewer` ใน `index.html` + dispatch `show_media_results`/`show_media`/`hide_media` ใน `main.js` + refs ใน `dom.js`
- grid: tile responsive, เลข badge, ▶+duration ถ้าวิดีโอ, skeleton/`onerror`, คลิก → สั่ง "เปิดอันที่ N"
- viewer: overlay เต็มจอ (`z-index:600`), `<img>`/`<video controls autoplay>`, ‹ › + `←/→` เลื่อน (client-side จาก `list`), คลิกรูป = zoom 1x/2x, ✕/Esc/คลิก backdrop ปิด, `<video>` → `pause()`+`removeAttribute('src')`+`load()` ตอนปิด

**shared helpers ย้ายที่**: `_safe_name` / `_uniq` ย้ายจาก `tools/mail.py` → `tools/files.py` (mail.py import `files._safe_name`/`files._uniq` แทน) — ใช้ร่วมกับ media.py

## ตำแหน่งที่ตั้ง (geolocation) — `get_weather()` ใช้พิกัดจริงของเบราว์เซอร์

ผู้ใช้ถามอากาศ "ที่นี่"/ไม่ระบุเมือง แล้วต้องไม่ต้องพิมพ์ชื่อเมืองเอง — โครงเดียวกับ folder picker / `_pending_action` เป๊ะ: **ข้อมูล (พิกัด) อยู่ฝั่ง browser แต่ tool รันฝั่ง server** เลยต้องให้ client แนบพิกัดมากับ request

- **`app.js`**: `refreshClientGeo()` เรียก `navigator.geolocation.getCurrentPosition()` (หน่วง 1.2 วิหลังโหลดหน้า กันชน prompt ขอสิทธิ์ไมค์) ปัดพิกัดเหลือ 4 ตำแหน่งทศนิยม (~11 ม. + หยาบลงนิดเรื่อง privacy) เก็บใน `clientGeo = {lat, lon, label}` — `label` ได้จาก **BigDataCloud `reverse-geocode-client`** (ฟรี ไม่ต้อง key ออกแบบมาให้เรียกจาก browser) เรียกไม่สำเร็จ/ผู้ใช้ไม่อนุญาต ก็ปล่อย `null` ได้ ไม่พังอะไร (เซ็ต `lat/lon` ก่อนแล้วค่อยเติม `label` ทีหลัง เผื่อ reverse geocode ค้าง) ทุก `POST /api/chat` แนบ `geo` ไปถ้ามี
- **บั๊กจริงที่เจอ + วิธีกัน**: เดิม `refreshClientGeo()` รันครั้งเดียวตอนโหลดหน้า ถ้าตอนนั้นสิทธิ์ยังเป็น "prompt" หรือผู้ใช้กดอนุญาตทีหลัง → `clientGeo` ค้างเป็น `null` ตลอด (submit handler เดิม re-fetch เฉพาะตอน `clientGeo` มีค่าแล้ว) ผู้ใช้เจอว่า "อนุญาตในเบราว์เซอร์แล้วแต่ระบบยังบอกเข้าถึงไม่ได้" ต้องรีเฟรชหน้าถึงจะติด — แก้ 4 ทาง: (1) submit handler ขอพิกัดใหม่เมื่อ `!clientGeo` ด้วย (ไม่ใช่แค่ตอนเก่าเกิน 10 นาที) มี rate-limit `GEO_RETRY_MS = 20s` กันยิงทุก submit ตอนโดนปฏิเสธ (2) `navigator.permissions.query({name:'geolocation'})` + ฟัง event `change` → พอสิทธิ์เปลี่ยนเป็น `granted` ดึงพิกัดทันทีไม่ต้องรีเฟรช (3) `visibilitychange` → กลับมาที่แท็บแล้วยังไม่มีพิกัด ลองใหม่ (4) `geoInFlight` guard กัน `getCurrentPosition` ซ้อนกันจากหลายเส้นทาง — ทั้งหมด log เหตุผลที่ล้มเหลว (`err.code`) ลง console (F12) ได้ + เตือนถ้า `!window.isSecureContext` (เปิดผ่าน IP เครื่องในวง LAN แทน `127.0.0.1` → เบราว์เซอร์บล็อก geolocation เงียบๆ)
- **`server.py`**: `ChatRequest.geo: Optional[dict]` — `chat_endpoint` เรียก `tools.set_client_location(req.geo)` ก่อน `chat.send_message()` แล้วล้างด้วย `None` ใน `finally` **ทุกทางออก** (เหมือน `pop_pending_action`) กันพิกัดเก่าค้างไปโผล่ request ถัดไปที่ไม่ได้ส่ง `geo` มา
- **`tools.py`**: `set_client_location()` รับเฉพาะ dict ที่ `lat`/`lon` cast เป็น `float` ได้จริง นอกนั้นเป็น `None`. `get_weather(location="")` (เปลี่ยน `location` เป็น optional แล้ว) — ถ้า `location` อยู่ใน `_HERE_ALIASES` (ว่าง/"ที่นี่"/"ปัจจุบัน"/"my location" ฯลฯ): มีพิกัด → ยิง forecast ตรงด้วย lat/lon เลย ข้าม geocoding, `display_name` = `label` ที่ client ส่งมา หรือ `"ตำแหน่งปัจจุบัน"` ถ้าไม่มี; ไม่มีพิกัด → ตอบข้อความบอกให้บอกชื่อเมือง (LLM เอาไปถามผู้ใช้ต่อ) ส่วน path ปกติ (ระบุชื่อเมือง) ยัง geocode เหมือนเดิม
- refactor: แยกส่วนยิง forecast + ประกอบ `_pending_action` ออกมาเป็น `_build_weather_reply(lat, lon, display_name)` ใช้ร่วมกันทั้ง 2 ทางที่ได้พิกัดมา (จากชื่อเมือง / จาก geolocation)
- **หลักการ "ห้ามโชว์ข้อมูลปลอม"**: `label` มาจาก reverse geocode พิกัดจริง ถ้าไม่ได้ก็โชว์ `"ตำแหน่งปัจจุบัน"` ตรงๆ (ไม่เดาชื่อเมือง) การ์ดอากาศยังโผล่เฉพาะตอนมีข้อมูล Open-Meteo จริงเหมือนเดิม
- ยังเป็น global ตัวเดียว (`_client_location`) ไม่ใช่ per-request — ยอมรับได้เพราะ personal use คนเดียว เหมือน `_pending_action`

**Bluetooth**: ผู้ใช้บอกว่ายังไม่ต้องรีบทำตอนนี้ — บันทึกไว้เผื่ออนาคต: เบราว์เซอร์ทำไม่ได้ (Web Bluetooth API จับคู่ทีละเครื่องผ่าน device picker เท่านั้น นับจำนวนอุปกรณ์ที่เชื่อมต่ออยู่ไม่ได้) ถ้าจะทำต้องให้ server (Python) คุย Windows Bluetooth stack ตรงๆ (เช่นผ่าน `bleak` หรือ WMI) ซึ่งจะใช้ได้เฉพาะตอน server รันบนเครื่อง Windows นี้เท่านั้นเหมือนกับปัญหาของ folder picker

## บุคลิกของ จัสมิน

- **เพศหญิง** — ระบุไว้ชัดใน system prompt ทั้ง `jusmin.py`/`server.py` ให้ใช้คำลงท้าย/สรรพนามผู้หญิงเสมอ (ค่ะ, ดิฉัน/หนู) และ default เสียง TTS เป็น `th_f_1` (ผู้หญิง)
- ฉลาด กระชับ เป็นกันเอง มีอารมณ์ขันนิด ๆ (สไตล์ AI ใน Iron Man)
- พูดภาษาไทยเป็นหลัก เว้นแต่ถูกถามเป็นภาษาอื่น
- ตอบสั้นได้ใจความ ไม่เยิ่นเย้อ

## เรื่องต้องคิดต่อ (อย่าลืม)

- **Safety layer** — ก่อนรัน `control_home` ต้องเช็ค whitelist อุปกรณ์/action ก่อน ไม่เชื่อ LLM สั่งมั่ว
- **Memory** — เก็บประวัติลง SQLite ให้ agent จำเรื่องต่อได้
- **Timeout / fallback** — ถ้า LLM ล่ม ต้องมีทางสั่งงานตรงกับ HA อยู่
- **Secret** — `.env` ห้าม commit ขึ้น Git เด็ดขาด

## หลักการออกแบบ UI

**ห้ามใส่ panel/กราฟ/gauge ที่โชว์ข้อมูลปลอม** — ทุกอย่างที่ดูเหมือนแสดงข้อมูลต้องผูกกับข้อมูลจริงหรือ state จริงเสมอ (เช่น panel มุมจอ 4 มุมใน `static/` ตอนนี้ผูกกับ: เวลาตอบสนองจริงที่วัดได้, โควตาจริงจาก `/api/quota`, สถานะการเชื่อมต่อ server จริง, เวลาปัจจุบันจริง) ถ้าไม่มีข้อมูลจริงมาผูก ให้ข้ามไปเลยดีกว่าใส่ของปลอม ส่วนของตกแต่งบรรยากาศล้วน ๆ (particles, scanline, vignette, กรอบมุมจอ) ใส่ได้เพราะไม่ได้แอบอ้างว่าเป็นข้อมูล

## โครงสร้างโปรเจกต์ปัจจุบัน

> **หมายเหตุ (refactor "แยกไฟล์"):** ตอนนี้แยกเป็นโมดูลย่อยแล้ว 3 จุด — `tools.py` → package `tools/`, `static/style.css` → `@import` ไฟล์ใน `static/css/`, `static/app.js` → **ES modules** ใน `static/js/` (entry = `js/main.js`, `<script type="module">`). พฤติกรรมเหมือนเดิมทุกอย่าง เป็น pure refactor

```
jusmin-ai/
├── jusmin.py         # agent loop แบบ CLI (Step 0)
├── server.py         # FastAPI backend — เสิร์ฟหน้าเว็บ + /api/chat + /api/quota + /api/tts
├── personality.py    # SYSTEM_PROMPT ที่ jusmin.py กับ server.py ใช้ร่วมกัน
├── tools/            # tool registry (package) — server.py ยัง `from tools import ...` / `import tools` ได้เหมือนเดิม
│   ├── __init__.py   #   re-export ทุกชื่อ public + `from . import notify, reminders`
│   ├── _state.py     #   pending_action (คำสั่งที่ส่งให้ app.js ทำจริงในเบราว์เซอร์) — weather+youtube share กัน
│   ├── db.py         #   SQLite layer (jusmin.db) — connect/query/execute + schema memory/tasks/reminders
│   ├── web.py        #   search_web (ddgs) + read_url (trafilatura + SSRF guard + URL normalize)
│   ├── vision.py     #   analyze_image — ดูรูปในโฟลเดอร์ที่อนุญาต ผ่าน Gemini (nested call, client แยก lazy)
│   ├── media.py      #   search_media / download_media (รูป sync, วิดีโอ async+yt-dlp+ffmpeg) / view_media (overlay)
│   ├── weather.py    #   get_weather + set_client_location + view โฟกัส (now/rain/temp/wind/uv/sun/forecast)
│   ├── youtube.py    #   open_youtube / control_youtube (yt-dlp)
│   ├── files.py      #   list_files/read_file/create_folder/write_file/delete_path + audit log + persist folder
│   ├── memory.py     #   remember/recall/forget + memory_preamble() (server.py prepend ทุกเทิร์น)
│   ├── tasks.py      #   add_task/list_tasks/complete_task
│   ├── reminders.py  #   add_reminder/list_reminders/cancel_reminder + check_due() (scheduler เรียก)
│   ├── notify.py     #   queue+lock — check_due() push, /api/notifications drain, js/notify.js poll
│   ├── mail.py       #   check/read/search/save_attachment/send_email (imaplib+smtplib, .env, ทุกกล่อง+ไฟล์แนบ) + unread_count()
│   └── briefing.py   #   daily_briefing() — วันที่ไทย+งาน+เตือน+เมลค้าง (LLM เรียก get_weather() ต่อเอง)
├── tts.py            # เสียงพูดไทยฝั่ง server (vachanatts engine vachana / gTTS)
├── static/
│   ├── index.html    # โครง HUD — <link style.css> + <script type="module" src="js/main.js">
│   ├── style.css      # แค่ list ของ @import css/*.css (ลำดับ = cascade)
│   ├── css/          # base / boot-fx / controls / sidebar / core / panels / youtube / weather / media / chat
│   └── js/           # ES modules:
│       ├── main.js       #   entry — import ทุกโมดูล + form submit handler + bootstrap ที่ท้าย
│       ├── state.js      #   `S` = object เดียวสำหรับ flag ที่ใช้ข้ามโมดูล (S.engagedActive, S.ttsSpeaking, S.ytPlayer, ...)
│       ├── dom.js        #   element refs ทั้งหมด (export const ... = document.getElementById(...))
│       ├── sound.js      #   beep + TTS (speak, engine/voice select, analyser); export ttsAnalyser/ttsDataArray (live binding)
│       ├── voice.js      #   STT push-to-talk + wake mode + ช่วงคุยต่อเนื่อง/debounce
│       ├── wave.js       #   wave-ring rendering + mic analyser (+ prevEngagedActive local, ย่อจอ YT ตอนถูกเรียก)
│       ├── youtube.js    #   YT.Player + controls + fullscreen/maximize + audio ducking
│       ├── weather.js    #   การ์ดอากาศทุก view + renderSeriesChart (SVG)
│       ├── chatui.js     #   addLine/typeText/announceSystemNotice/setThinking/openUrlWithFallback
│       ├── hud.js        #   boot + particles + idle-tilt + clock + latency graph + quota gauge + link health
│       ├── settings.js   #   sidebar ⚙ + ปุ่มเลือกโฟลเดอร์
│       ├── geo.js        #   navigator.geolocation -> S.clientGeo (แนบไป /api/chat)
│       ├── notify.js     #   poll /api/notifications ทุก 10 วิ -> announceSystemNotice + speak (reminder เด้ง)
│       └── media.js      #   grid ผลค้นรูป/วิดีโอ + viewer overlay เต็มจอ (prev/next/zoom/keyboard)
├── voices/  logs/  venv/  .env  file_access_config.json  jusmin.db   # ไม่ commit
├── .gitignore
└── requirements.txt
```

**หลักการของ ES module split (สำคัญตอนแก้ต่อ):**
- flag ที่ **หลายโมดูลอ่าน+เขียน** อยู่ใน `state.js` `S` (import เป็น read-only binding เขียนตรงๆ ไม่ได้ แต่ mutate property ได้) — flag ที่ใช้ในไฟล์เดียว (`selectedEngine`, `recognition`, `followUpActive`, `ytVolume`, `ytPlayerReady`, `geoInFlight`, `prevEngagedActive`, ...) ยังเป็น `let` ในไฟล์นั้น
- `main.js` เป็นตัวเดียวที่ import กว้าง + ไม่มีใคร import มัน → ตัด circular dependency ส่วนใหญ่ ที่เหลือ (sound↔voice, chatui↔voice) ปลอดภัยเพราะ binding ถูกเรียกใน callback เท่านั้น ไม่เรียกตอน module top-level
- `dom.js` เพิ่ม `wakeBtn` เป็น explicit ref (เดิม app.js พึ่ง named-element global `window.wakeBtn` โดยบังเอิญ)

## วิธีรัน

**แบบ CLI (Step 0):**
```bash
cd jusmin-ai
venv\Scripts\activate            # Windows
pip install -r requirements.txt  # ครั้งแรกครั้งเดียว
python jusmin.py
```

**แบบเว็บ (Jarvis HUD):**
```bash
cd jusmin-ai
venv\Scripts\activate
python server.py
```
แล้วเปิดเบราว์เซอร์ไปที่ `http://127.0.0.1:8000/` — ตอนนี้ chat session เป็นแบบ session เดียวเก็บใน memory ของ server (เหมาะกับ personal use คนเดียว ยังไม่รองรับหลาย user/หลายแท็บพร้อมกันแบบแยกบทสนทนา)

**หมายเหตุ:** ทุกครั้งที่แก้ `server.py`/`tools.py`/`tts.py` ต้อง restart server เอง (กด Ctrl+C แล้วรัน `python server.py` ใหม่) ไม่มี auto-reload — server เริ่มช้าลงกว่าเดิมเล็กน้อย (~3-5 วิ) เพราะต้องโหลดโมเดลเสียง TTS ตอน start

## Quota tracking

`server.py` เก็บ state เอง (`quota_state`) นับจำนวนครั้งที่เรียก Gemini สำเร็จวันนี้ (`used_today`, รีเซ็ตทุกเที่ยงคืนตามเวลาเครื่อง — เป็นค่าประมาณ เพราะ Google ไม่เปิดเผยเวลารีเซ็ตจริงของ free tier) ส่วน `limit` จะรู้ค่าจริงก็ต่อเมื่อโดน HTTP 429 ครั้งแรกเท่านั้น (parse จาก `QuotaFailure.violations[0].quotaValue` ในตัว error) และ `cooldown_until` มาจาก `RetryInfo.retryDelay` ของ error เดียวกัน

**Optimize แล้ว:** เดิมหน้าเว็บ poll `GET /api/quota` ทุก 1 วินาที (86,400 request/วันแม้ไม่ได้ใช้เลย) ตอนนี้ sync กับ server ทุก `QUOTA_SYNC_MS` (5 วิ) เท่านั้น ส่วนตัวนับถอยหลัง cooldown ที่ต้องขยับทุกวินาทีให้ลื่น คำนวณเอาเองฝั่ง client จากค่า `cooldown_seconds` ล่าสุด + เวลาที่ผ่านไปจริง (`renderQuotaDisplay()`) ไม่ต้องยิง request ทุกครั้ง — ทดสอบแล้วว่า request ลดจาก ~12 ครั้ง/12วิ เหลือ ~2-3 ครั้ง/12วิ และเลขนับถอยหลังยังแม่นยำ (ทดสอบ edge case ค่าติดลบด้วย ผลลัพธ์ clamp เป็น 0 ถูกต้อง)

## งานถัดไปสำหรับ Claude Code

Step 0-2 + เว็บ UI + กลุ่ม tool เลขา (กลุ่ม A: memory/tasks/reminders/email/briefing) เสร็จแล้ว

**ยังเหลือจาก roadmap "จัสมิน เลขาสมบูรณ์" (ทำเมื่อผู้ใช้สั่ง):**
- กลุ่ม B — ปฏิทิน (Google Calendar) + สภาพจราจร/เส้นทาง + ค่าเงิน/หุ้น
- กลุ่ม C — สรุปข่าว + จดโน้ตยาว/สรุปเอกสาร + timer/นาฬิกาปลุก + คุมสมาร์ตโฮม (Step 3-5 เดิม)

**หนี้ทางเทคนิคของกลุ่ม A ที่ควรรู้:**
- `send_email` มี confirmation flow จริงในโค้ดแล้ว (2 ขั้น `_pending_send` + `confirm=True`) — แต่ `delete_path` / `control_youtube` ยังคุมด้วย docstring อย่างเดียว ถ้าเจอเคส LLM ลบเองโดยไม่ถาม ควรทำ flow แบบเดียวกับ `send_email`
- reminder เด้งเฉพาะตอนเปิดแท็บ (ผู้ใช้เลือกเอง) — ถ้าอยากได้ Windows notification ต้องทำ layer แยกฝั่ง server
- `memory_preamble()` prepend ทุกเทิร์น = fact ซ้ำใน history เรื่อยๆ ถ้า fact เยอะขึ้นมากอาจเปลือง token ควรเปลี่ยนไป inject ผ่าน `system_instruction` + rebuild chat session แทน
