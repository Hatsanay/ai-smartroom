# FRIDAY — AI Assistant Project

> Context file สำหรับ Claude Code เอาไว้ปรับตัวให้เข้าใจเป้าหมายและขอบเขตของโปรเจกต์นี้

## เป้าหมาย

สร้าง AI agent สไตล์ Jarvis ชื่อ **FRIDAY** ที่:

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
- [x] **เว็บ UI (Jarvis HUD)** — `server.py` (FastAPI) + `static/` หน้าเว็บ animation แบบ HUD วงกลม คุยกับ FRIDAY ผ่านเบราว์เซอร์ได้ พร้อม panel แสดงโควตา Gemini + คูลดาวน์แบบสด
- [x] **Step 1** — เพิ่ม tool แรก `search_web()` ผ่าน `ddgs` (DuckDuckGo, ฟรี ไม่ต้องขอ key)
  - **บั๊กจริงที่เจอตอนทดสอบครบทุกฟังก์ชัน**: `_ddgs.text()` (รุ่นที่ใช้อยู่) ยิง `DDGSException` ตอนไม่เจอผลลัพธ์/โดน rate-limit/timeout แทนที่จะคืน list ว่างตามที่โค้ดเดิมคาดไว้ (`if not results:` เลยเป็น dead code ที่ไม่เคยถูกเรียกถึง) — Gemini function calling เจอ exception ดิบแล้วรอดมาได้ (SDK จับเองแล้วบอกโมเดลว่า tool fail) แต่คำตอบจะกำกวมไม่ตรงประเด็น ("ระบบค้นหาขัดข้องชั่วคราว") ทั้งที่ query ไม่ได้ผิดอะไร — แก้โดยครอบ `try/except DDGSException` ใน `search_web()` คืนข้อความ graceful แทน
- [ ] **Step 2** — เพิ่ม memory ถาวร (SQLite) ให้จำเรื่องเก่า-ใหม่ได้ข้ามเซสชัน
- [ ] **Step 3** — ตั้ง Home Assistant + ESP32/รีเลย์ ให้คุมอุปกรณ์จริง
- [ ] **Step 4** — เพิ่ม `control_home()` เพื่อให้ agent เรียก HA สั่งอุปกรณ์ได้
- [ ] **Step 5** — ขยาย tool (คุม TV, เครื่องเล่น) ทีละอัน
- [x] **Step 6** — เสียงบนเว็บ: กดไมค์พูด (STT) + FRIDAY พูดตอบ (TTS) + **โหมดฟังตลอดพร้อม wake word "Friday"** ทั้งหมดผ่าน Web Speech API ของเบราว์เซอร์ (ของเดิมที่วางแผนจะใช้ Whisper ยังไม่ได้ทำ เพราะย้ายมาทำเวอร์ชันเว็บก่อน)
- [x] **Tool: `open_youtube()` + `control_youtube()`** — ให้ FRIDAY ค้นหาแล้ว**เล่นเพลง/วิดีโอ YouTube อัตโนมัติจริง** (ไม่ใช่แค่เปิดหน้าค้นหา) พร้อมสั่งหยุด/เล่นต่อ/ปิด/เปลี่ยนเพลงด้วยเสียงได้
- [x] **Tool: `get_weather()`** — เช็คสภาพอากาศจริงผ่าน [Open-Meteo](https://open-meteo.com/) (ฟรี ไม่ต้องขอ API key เหมือน ddgs/yt-dlp) พร้อม UI การ์ดแสดงผลสวยๆ มุมขวากลางจอ (ล้อกับ `.yt-panel` ฝั่งซ้าย)
  - `_search_youtube`-style pattern เดิม: geocoding API (`geocoding-api.open-meteo.com/v1/search`) แปลงชื่อสถานที่เป็นพิกัดก่อน แล้วยิง forecast API (`api.open-meteo.com/v1/forecast`) ด้วยพิกัดนั้นอีกที ขอทั้ง current weather + พยากรณ์ 4 วันข้างหน้า (`forecast_days=4`)
  - แปลรหัสสภาพอากาศ WMO (มาตรฐานที่ Open-Meteo ใช้) เป็นคำอธิบายไทย + emoji + หมวด `fx` (สำหรับเลือก animation พื้นหลัง ดูด้านล่าง) ไว้ที่ `_WMO_WEATHER` dict ใน `tools.py` **คำนวณครั้งเดียวฝั่ง server** แล้วส่งค่าที่พร้อมแสดงผลไปให้ทั้งข้อความตอบ (พูด/แชท) และ `action.data` (สำหรับ UI) เลย — ตั้งใจไม่ทำ mapping ชุดเดียวกันซ้ำสองที่ (Python + JS) กัน mapping หลุดไม่ตรงกันในระยะยาว (ต่างจาก `_YT_VOLUME_STEP`/`YT_VOLUME_STEP` ที่จำเป็นต้อง sync มือเพราะเป็นค่าที่ทั้งสองฝั่งต้องใช้แยกกันจริงๆ)
  - `action.type = "show_weather"`, `action.data` มี `location`/`temperature`/`feels_like`/`humidity`/`wind_speed`/`condition`/`emoji`/`fx`/`is_day`/`forecast` (array 4 รายการ) — `app.js`'s `showWeather(data)` แค่เอาไปแปะแสดงผลตรงๆ ไม่มีเดา/เติมค่าเองเลย ตรงตามหลักการ "ห้ามใส่ panel ที่โชว์ข้อมูลปลอม"
  - **animation พื้นหลังตามสภาพอากาศจริง** (ผู้ใช้ขอให้ "สวยกว่านี้ ใหญ่ขึ้น มี animation") — `renderWeatherFx(data.fx)` ใน `app.js` สร้าง DOM element ใน `#weatherFx` (layer ซ้อนอยู่หลังเนื้อหา, `overflow:hidden` ตัดขอบ) ตาม `fx` 6 หมวด: `sunny` (แสงเปล่งพัลส์ผ่าน CSS `::before` ล้วนๆ ไม่ต้องสร้าง element), `cloudy` (ก้อนเมฆเบลอ 3 ก้อนลอยผ่าน), `fog` (แถบหมอกไหลซ้ายขวา 3 แถบ), `rain` (เม็ดฝนตกจริง 16 เม็ด), `storm` (เหมือน rain + แสงฟ้าแลบเป็นจังหวะ), `snow` (เกล็ดหิมะโปรย 14 เกล็ด แกว่งซ้ายขวาผ่าน CSS var `--fx-drift`) — สุ่มแค่ `top`/`left`/`animation-duration`/`animation-delay` ต่อ element ให้ดูเป็นธรรมชาติ (ไม่ทับกันแข็งๆ) ตัว**หมวด**ยังคงมาจากข้อมูลจริงเสมอ ไม่ใช่สุ่มว่าจะโชว์ฝนหรือหิมะ
  - panel เข้าด้วย spring easing (`cubic-bezier(0.34, 1.56, 0.64, 1)`, ค่า overshoot เกิน 1 แล้วเด้งกลับ) แทน fade ธรรมดา ขยายขนาดจาก 220px เป็น 320px ตัวเลขอุณหภูมิ/ไอคอนใหญ่ขึ้นชัดเจน (52px/64px) ไอคอนมี animation ลอยขึ้นลงเบาๆ ตลอดเวลา (`weather-emoji-float`)
  - panel (`#weatherPanel`) ซ่อนไว้เป็นค่าเริ่มต้น โผล่มาเฉพาะตอนมีข้อมูลจริงจาก Open-Meteo แล้วเท่านั้น (เหมือน `.yt-panel`)
  - **ปิดตัวเองอัตโนมัติหลัง 30 วิ** (`WEATHER_AUTO_HIDE_MS`, ผู้ใช้ขอ) — นับเวลาจาก**เสียงพูดหยุดจริง** (ผ่าน `speak()`'s `onDone` callback) ไม่ใช่จากตอนได้ข้อมูลมา ใช้ pattern เดียวกับช่วงคุยต่อเนื่อง 15 วิเป๊ะ (`scheduleWeatherHide()` เรียกคู่กับ `startFollowUpWindow()` ใน `onDone`) — ถ้าถามอากาศที่ใหม่ระหว่างนับถอยหลังเดิมอยู่ `showWeather()` จะเคลียร์ตัวจับเวลาเก่าทิ้งแล้วเริ่มนับใหม่ ไม่ปิดกลางคันขณะกำลังโชว์ข้อมูลใหม่
  - เพิ่ม `requests` เป็น dependency ตรงๆ ใน `requirements.txt` (แม้จะมีอยู่แล้วแบบ transitive ผ่าน `gTTS` ก็ตาม) เพราะตอนนี้ `tools.py` เรียกใช้ตรงๆ เอง ไม่ควรพึ่ง transitive dependency ที่อาจหายไปได้ถ้า `gTTS` เปลี่ยนไปในอนาคต

**สถาปัตยกรรม tool ที่ต้อง "ทำอะไรบางอย่างในเบราว์เซอร์" (ไม่ใช่แค่คืนข้อความให้ LLM อ่าน):**
- ปัญหา: `google-genai`'s automatic function calling รัน Python function (`tools.py`) ฝั่ง **server** แต่ผู้ใช้ดู/คุมเบราว์เซอร์อยู่ฝั่ง **client** — ยิ่งมีแผนย้ายไป Pi ในอนาคต (`server` อาจรันคนละเครื่องกับเบราว์เซอร์ผู้ใช้เลย) เรียก `webbrowser.open()` ฝั่ง server ตรงๆ ไม่ได้
- แก้โดยให้ tool เก็บ "คำสั่งที่ต้องทำจริง" ไว้ในตัวแปร module-level `_pending_action` (dict) แทนที่จะลงมือเองฝั่ง server แล้ว `server.py`'s `chat_endpoint` เรียก `pop_pending_action()` หลัง `chat.send_message()` เสร็จ แนบมากับ `ChatResponse.action` — ฝั่ง `app.js` เช็ค `data.action.type` แล้วลงมือจริง (เป็นคนทำจริงตามหลัก "LLM เลือก tool, โค้ดเราลงมือจริง" เดียวกับที่ตั้งใจไว้ตอนแรกสำหรับ `control_home`)
- **`_pending_action` เป็น global ตัวเดียว ไม่ใช่ per-request** — ยอมรับได้เพราะโปรเจกต์นี้ตั้งใจไว้แต่แรกว่าเป็น personal use คนเดียว ไม่รองรับหลาย session พร้อมกันอยู่แล้ว — pop แล้วเคลียร์ทิ้งทุก path ที่ออกจาก `chat_endpoint` (ทั้งสำเร็จและ error) กัน action หลงเหลือไปโผล่ผิด request
- ตั้งใจไม่เพิ่ม tool พวกนี้ใน `friday.py` (CLI) เพราะ CLI ไม่มีกลไกไปทำอะไรจริงๆ ได้ (ไม่มี `pop_pending_action()` มาเรียกใช้) จะทำให้ FRIDAY โกหกว่าทำให้แล้วทั้งที่ไม่ได้ทำจริง

**`action.type` ที่มีตอนนี้ 3 แบบ (`server.py` ส่ง, `app.js` เป็นคนลงมือจริง):**
1. `open_url` — เปิดแท็บใหม่ด้วย `url` ที่กำหนด (ใช้ตอน `open_youtube()` ไม่มี query เลย แค่เปิดหน้าแรก youtube.com เฉยๆ)
2. `play_youtube` — โหลด+เล่นวิดีโอ `video_id`/`title` ที่กำหนดในเครื่องเล่นที่ฝังอยู่ในหน้าเว็บเอง (ไม่ใช่เปิดแท็บแยก)
3. `youtube_control` — สั่ง `action` ("pause"/"resume"/"stop"/"volume_up"/"volume_down") กับเครื่องเล่นที่กำลังเล่นอยู่

**ทำไมต้อง "ฝัง player ในหน้าเว็บ" (`YT.Player`) แทนเปิดแท็บแยกด้วย `window.open()` เหมือนตอนแรก:**
- แท็บที่เปิดแยกเป็นคนละ browsing context กันเลย โค้ดเราคุม play/pause/stop จากภายนอกไม่ได้จริงๆ (ไม่มี API ให้เข้าถึง iframe ข้าม origin) — ต้องฝัง [YouTube IFrame Player API](https://developers.google.com/youtube/iframe_api_reference) (`https://www.youtube.com/iframe_api`, ฟรี ไม่ต้องขอ key) ไว้ในหน้าเว็บเราเองถึงจะเรียก `player.pauseVideo()`/`playVideo()`/`stopVideo()`/`loadVideoById()` ได้จริง
- โหลด script แบบ dynamic ผ่าน `loadYtApiScript()` ใน `app.js` (ไม่ใช่ `<script>` ตายตัวใน `index.html`) เพราะไม่จำเป็นต้องโหลดถ้าไม่เคยสั่งเปิดเพลงเลย
- **บั๊กจริงที่เจอตอนไล่หาความเสถียร (`ytPlayerReady`)**: เมธอดของ `YT.Player` (`setVolume`/`pauseVideo`/`playVideo`/`stopVideo`) **ใช้งานจริงไม่ได้ก่อน event `onReady`** แม้ `new YT.Player(...)` จะคืน object กลับมาแบบ synchronous ทันทีก็ตาม (iframe ข้างในยังไม่เชื่อมต่อ postMessage เสร็จ เป็นพฤติกรรมที่เอกสารทางการของ YouTube ระบุไว้) — เดิมโค้ดเช็คแค่ `ytPlayer !== null` ไม่ได้เช็ค ready จริง ถ้าผู้ใช้สั่ง "หยุดเพลง"/"เพิ่มเสียง" ไวมากทันทีหลัง "เปิดเพลง X" (ภายในเสี้ยววินาทีที่ iframe ยังโหลดไม่เสร็จ) คำสั่งนั้นจะเงียบหายไปเฉยๆ ไม่มีผลอะไรเลย
  - แก้โดยเพิ่ม `ytPlayerReady` (true เฉพาะหลัง `onReady` จริง ค้างจนกว่าจะโหลดหน้าใหม่ — ไม่รีเซ็ตตอนเปลี่ยนเพลงเพราะ `loadVideoById()` ไม่ยิง `onReady` ซ้ำ) `controlYoutube()` เช็ค flag นี้ก่อนเสมอ ถ้ายังไม่ ready จะเก็บ action ล่าสุดไว้ใน `ytPendingCommand` (คำสั่งล่าสุดชนะ ไม่สะสมเป็นคิว) แล้วให้ `onYtPlayerReady()` ทำให้ทันทีที่ ready จริง — `duckYoutubeVolume()`/`restoreYoutubeVolume()` เช็ค flag เดียวกันแต่ไม่คิว (ปล่อยผ่านเฉยๆ เพราะรอบพูดถัดไปจะ duck/restore ใหม่ให้เองอยู่แล้ว ไม่คุ้มจะเพิ่ม complexity)
- `#ytPlayerMount` ถูก YT API แทนที่ด้วย `<iframe>` จริงตอนสร้าง `new YT.Player(...)` — panel `#ytPanel` (มุมซ้ายกลางของจอ) ซ่อนไว้เป็นค่าเริ่มต้น (`opacity:0`) โผล่มาเฉพาะตอนกำลังเล่นเพลงจริงเท่านั้น ตรงกับหลักการ "ห้ามใส่ panel ที่โชว์ข้อมูลปลอม"
- **Audio ducking**: ตอน FRIDAY พูด (TTS) จะลดเสียงเพลง YouTube ลงชั่วคราวเหลือ `YT_DUCK_VOLUME = 15` (จาก `ytVolume` ปัจจุบัน) ผ่าน `ytPlayer.setVolume()` แล้วคืนกลับตอนพูดจบ (`ttsAudio`'s `play`/`ended`/`error` event — `duckYoutubeVolume()`/`restoreYoutubeVolume()` ใน `app.js`) กันเสียงพูดทับเพลงจนฟังไม่รู้เรื่อง ยังไม่ได้ทำ AEC จริงจัง (echo cancellation ระดับสัญญาณเสียง) แค่ลด volume ธรรมดา เพียงพอสำหรับ use case นี้แล้ว
- **สั่งเพิ่ม/ลดเสียงเพลงด้วยเสียงได้** (`control_youtube('volume_up'/'volume_down')`) — `ytVolume` (ตัวแปรใน `app.js`) เป็น "baseline" ที่ผู้ใช้ตั้งไว้ล่าสุด **แยกต่างหากจากค่าตอน duck ชั่วคราว** (`YT_DUCK_VOLUME`) เพิ่ม/ลดทีละ `YT_VOLUME_STEP = 25` (เดิม 20) clamp ไว้ที่ 0-100 เสมอ
  - **feedback จริงจากผู้ใช้**: สั่ง "ลดเสียง" แล้ว "รู้สึกว่าไม่ลดเลย" — ไล่ตรวจสอบด้วย `player.getVolume()` ของ real YT.Player (ไม่ใช่ mock) ยืนยันว่า**กลไกทำงานถูกต้อง 100%** (ค่าเปลี่ยนจาก 100 เป็น 80 จริงตามที่สั่ง 1 ครั้งที่ step เดิม 20) แต่หูมนุษย์รับรู้ความดังแบบ logarithmic ไม่ใช่ linear ทำให้ step 20 หน่วยจาก 100 รู้สึกถึงความต่างน้อยเกินไปจนเหมือนไม่ได้เปลี่ยน — เพิ่ม step เป็น 25 ให้รู้สึกถึงการเปลี่ยนแปลงชัดเจนขึ้นต่อ 1 คำสั่ง (ถ้ายังรู้สึกน้อยไปอีกปรับเพิ่มได้ตามใจ)
  - **feedback รอบ 2**: ผู้ใช้รายงานว่า "หลังถาม FRIDAY มันเพิ่มเสียงให้เอง" — ทดสอบจำลองสถานการณ์ (เปิดเพลง → ลดเสียง → ถามคำถามทั่วไปที่ไม่เกี่ยวกับเพลงเลย → เช็ค `player.getVolume()` จริงหลัง TTS duck/restore cycle) **ไม่พบว่า Gemini เรียก `volume_up` เองเลย** (`action: null` ตามคาด, volume คงที่ถูกต้อง) เป็นไปได้ว่าเป็นเคสเฉพาะ (STT ฟังผิดเป็นคำสั่งเพิ่มเสียง, หรือบทสนทนารูปแบบอื่นที่ไม่ได้ลองจำลอง) — แก้เชิงป้องกันไว้ก่อนตามที่ผู้ใช้ขอ: เพิ่ม `_youtube_volume` ให้ server (`tools.py`) ติดตามระดับเสียงปัจจุบันขนานไปกับฝั่ง client (`ytVolume` ใน `app.js`คนละตัวแปร คนละภาษา ต้อง sync `_YT_VOLUME_STEP`/`YT_VOLUME_STEP` มือเอง) ให้ข้อความตอบของ `volume_up`/`volume_down` บอกเปอร์เซ็นต์ปัจจุบันเสมอ (เช่น "ลดเสียงเพลงให้แล้วค่ะ ตอนนี้อยู่ที่ 75%") จะได้ปรากฏในประวัติบทสนทนาที่ Gemini เห็น มี context จริงอ้างอิงแทนเดามั่วๆ พร้อมเสริม docstring ของ `control_youtube()` ให้ชัดว่า**ห้ามเรียกเองเดาเอาว่าผู้ใช้อาจต้องการ** ต้องเป็นคำขอที่ชัดเจนจริงๆ เท่านั้น
  - **จุดที่ต้องระวัง**: `restoreYoutubeVolume()` ต้องคืนกลับไปที่ `ytVolume` ไม่ใช่ค่าคงที่ 100 เสมอ ไม่งั้นถ้าผู้ใช้เคยหรี่เสียงไว้ พอ FRIDAY พูดจบเสียงเพลงจะดังกลับไป 100% เองทุกครั้งที่พูด ผิดจากที่ผู้ใช้ตั้งไว้
  - **ถ้าสั่งปรับเสียงระหว่างที่ FRIDAY กำลังพูดอยู่พอดี** (`ttsSpeaking === true`, กำลัง duck ค้างอยู่) จะไม่เรียก `setVolume()` ทันที แค่จำค่า `ytVolume` ใหม่ไว้ก่อน กันเสียงเพลงดังแทรกขึ้นมากลางประโยคที่ FRIDAY กำลังพูด — พอ TTS จบจริง `restoreYoutubeVolume()` จะหยิบค่าล่าสุดไปใช้เอง
  - `control_youtube('stop')` รีเซ็ต `ytVolume` กลับ 100 ด้วย (เริ่มเซสชันฟังเพลงครั้งถัดไปที่ปกติเสมอ ไม่ค้างค่าที่เคยปรับไว้ข้ามเซสชันเก่า)
- **ระหว่างเพลงเล่นอยู่จริง ต้องพูด "Friday" นำทุกครั้ง ห้ามข้ามช่วงคุยต่อเนื่อง 15 วิ** — ผู้ใช้ขอเพราะกลัวเนื้อเพลง/เสียงร้องถูก STT จับแล้วตีความเป็นคำสั่งมั่วๆ ระหว่างเพลงเล่น (ความเสี่ยงสูงกว่าเวลาปกติเพราะมีเสียงคนพูด/ร้องเพลงในห้องต่อเนื่องยาวกว่าประโยคสนทนาทั่วไป) — คุมด้วยตัวแปร `ytIsPlaying` ใน `app.js` ที่อัปเดตจาก **state จริงของ `YT.Player`** ผ่าน `onStateChange` event (ไม่ใช่เดาจากว่าเพิ่งสั่ง `playVideo()` ไปหรือยัง) แล้วเช็คเงื่อนไข `if (followUpActive && !ytIsPlaying)` ใน `wakeRecognition.onresult` — เพลงเล่นอยู่จริงจะบังคับให้ตกไปเช็ค `extractWakeCommand()` เสมอ ซึ่งต้องมีคำว่า "Friday" อยู่จริงในประโยคถึงจะทำงาน
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
  - `window.open()` คืนค่า `null` เงียบๆ ตอนโดนบล็อก (ไม่ throw) — `openUrlWithFallback()` ใน `app.js` เช็คค่านี้ ถ้า blocked จะเพิ่มลิงก์ให้กดเองใน chat log (`addLinkLine()`, คลาส CSS `.friday-link`) แทนที่จะปล่อยให้ดูเหมือน "ใช้ไม่ได้" เฉยๆ
  - **สำคัญ**: ต้องเรียก `window.open(url, '_blank')` แบบ**ไม่ใส่** `'noopener'`/`'noreferrer'` ถึงจะเช็คผลลัพธ์ได้ — ทดสอบยืนยันแล้วว่าถ้าใส่ 2 อันนี้ (ปกติควรใส่เพื่อความปลอดภัย กัน tabnabbing) `window.open()` จะคืนค่า `null` เสมอไม่ว่าจะเปิดสำเร็จหรือไม่ก็ตาม เลยแยกแยะไม่ได้เลย — ยอมข้ามไปเพราะ url ตายตัวที่ youtube.com ไม่ใช่ url จากภายนอกที่ควบคุมไม่ได้
  - `play_youtube`/`youtube_control` ไม่เจอปัญหานี้เลยเพราะไม่ได้เปิดแท็บ/popup ใหม่ แค่โหลด/สั่ง player ที่ฝังอยู่ในหน้าเดิม

**เรื่องต้องรู้เกี่ยวกับ wake word:**
- **โหมดฟังตลอดเปิดเป็นค่าเริ่มต้น** (auto-start ทันทีที่โหลดหน้าเว็บ, ปุ่ม 👂 จะติดไฟทันที) — เบราว์เซอร์จะขอสิทธิ์ไมค์เองถ้ายังไม่เคยอนุญาต
- เปิดแล้ว browser จะส่งเสียงไมค์ไปประมวลผลที่ cloud ของ Google (Web Speech API) **ตลอดเวลา** ไม่ใช่แค่ตอนกดพูด มีผลเรื่อง privacy/แบตเตอรี่/data ที่ควรรู้ไว้
- "Friday" เป็นคำภาษาอังกฤษทั่วไป (ชื่อวัน) เสี่ยง false trigger ได้ถ้ามีคนพูดถึงวันศุกร์ หรือทีวี/พอดแคสต์พูดคำนี้ผ่าน ๆ ในห้อง
- **กัน feedback loop โดยปิดไมค์จริงตอน FRIDAY พูด** — `pauseWakeListening()` เรียก `recognition.stop()` จริง ๆ ตอน audio element ยิง event `play` (ไม่ใช่แค่เช็ค flag) แล้ว `resumeWakeListeningAfterDelay()` เปิดกลับมาหลัง event `ended`/`error` + หน่วง 500ms กันหางเสียง/เสียงสะท้อนในห้อง ข้อแลกเปลี่ยนที่ยอมรับ: **แทรกกลางประโยคไม่ได้** ต้องรอ FRIDAY พูดจบก่อน (ชดเชยด้วยช่วงคุยต่อเนื่อง 15 วิด้านล่าง)
  - เคยลองอีกวิธี (ไม่ปิดไมค์ เทียบข้อความที่ได้ยินกับสิ่งที่ FRIDAY กำลังพูดอยู่แทน เพื่อให้แทรกได้ทันที) แต่ไม่น่าเชื่อถือพอในการใช้งานจริง เพราะเสียงสะท้อนที่ผ่าน STT กลับมามักเพี้ยนจากต้นฉบับเยอะ เทียบไม่ติด — **แผนอนาคต**: ทำ Acoustic Echo Cancellation จริงผ่าน `getUserMedia({echoCancellation:true})` + STT backend เอง (เช่น Whisper ตามแผนเดิม) ถึงจะแทรกกลางประโยคได้แบบเชื่อถือได้จริง
- ใช้ปุ่มไมค์กดพูดปกติไม่ได้พร้อมกับโหมดนี้ (ปิดปุ่มไมค์ไว้อัตโนมัติตอนเปิดโหมดฟังตลอด)
- **คุยต่อเนื่องได้ 15 วิ** — หลัง FRIDAY ตอบเสร็จ (ไมค์เปิดกลับมาแล้ว) พูดคำถามต่อได้เลยโดยไม่ต้องพูด "Friday" ซ้ำ (สถานะใต้ core จะขึ้น "STANDBY · ฟังต่อเนื่อง") ถ้าเงียบเกิน 15 วิ ต้องพูด "Friday" นำใหม่ กันไม่ให้จับเสียงอื่นในห้องมั่ว ๆ — **นับ 15 วิเริ่มตั้งแต่เสียงพูดหยุดจริง** (ผ่าน `speak(text, onDone)` callback ตอน TTS `onend`) ไม่ใช่นับตั้งแต่ได้คำตอบมา เพื่อไม่ให้คำตอบยาวๆ ที่พูดนานโดนกินเวลาช่วงคุยต่อเนื่องไปตั้งแต่ยังพูดไม่จบ
- **เรียกชื่อเฉยๆ ไม่มีคำสั่งตาม** (พูดแค่ "Friday" คำเดียว) — FRIDAY จะ**ตอบรับด้วยเสียงจริง** (สุ่มจาก `WAKE_ACK_PHRASES` กันซ้ำจำเจ) ไม่ใช่แค่เสียง beep เหมือนก่อนหน้านี้ พอตอบรับเสร็จ (ไมค์เปิดกลับมาเอง) จะเข้าสู่ช่วงคุยต่อเนื่อง 15 วิทันที (`startFollowUpWindow()`) ให้พูดคำถามจริงต่อได้เลยโดยไม่ต้องพูด "Friday" ซ้ำอีกรอบ
- **บั๊กจริงที่เจอ: พูด "Friday" คำเดียวแล้วติดบ้างไม่ติดบ้าง** — สาเหตุคือ `wakeRecognition.onend` restart session ใหม่ทุกครั้งที่ session เดิมจบ (Chrome ตัด `continuous:true` session เองเป็นระยะ**แม้ไม่มี error เลย** ไม่ใช่แค่ตอน error เท่านั้น) โค้ดเดิมหน่วง 250ms ก่อน restart ทุกรอบ — ระหว่าง 250ms นั้นไมค์ "หูหนวก" สนิท ถ้าจังหวะพูดคำสั้นๆ อย่าง "Friday" (~300-500ms) ดันตรงกับช่วงรีสตาร์ทพอดี คำนั้นจะหายไปเงียบๆ โดยไม่มี error ให้เห็นเลย — ยิ่งพูดคำเดียวสั้นๆ ยิ่งเสี่ยงกว่าประโยคยาว (มีโอกาสถูก "ตัด" มากกว่า) ตรงกับ pattern ที่ผู้ใช้เจอ แก้โดยลดหน่วงเหลือ `WAKE_RESTART_DELAY_MS = 30` (จาก 250) ลดหน้าต่างที่พลาดได้ลงไปมาก (ทดสอบวัดจริง gap ลดจาก 250ms เหลือ ~31ms) ยังเหลือกันชนเล็กน้อยกัน Chrome โยน "recognition already started" ถ้า restart เร็วเกินไป
  - เพิ่ม retry ใน `catch` ของ `wakeRecognition.start()` ด้วย (เดิมถ้า `start()` throw จะไม่มีอะไรมา restart ให้เลยเพราะ session นั้นไม่เคย start จริง `onend` เลยไม่มีทางยิง) — ป้องกันโหมดฟังตลอดค้างเงียบไปเฉยๆ แบบไม่มี error ให้เห็น
  - เพิ่ม `console.debug('[wake] missed:', transcript)` ตอน STT ได้ยินอะไรมาแต่ไม่ตรงกับ `WAKE_WORD_PATTERNS` เลย — เผื่อสาเหตุอีกทางที่เป็นไปได้คือ Google STT ถอดเสียง "Friday" เป็นคำไทยสะกดแบบอื่นที่ไม่อยู่ใน pattern list (ไม่ใช่ปัญหาจังหวะ) เปิด DevTools console (F12) เทียบดูได้ว่า STT ได้ยินเป็นคำว่าอะไรจริงๆ ตอนพูดแล้วไม่ติด
- **Debounce 5 วิก่อนส่งคำสั่งจริง (`COMMAND_DEBOUNCE_MS`)** — ผู้ใช้ขอเพราะเดิม `wakeRecognition.onresult` ส่งคำสั่งทันทีที่ recognition ตัดจบประโยค (isFinal) ซึ่งเกิดขึ้นเร็วกว่าที่คิด ถ้าหยุดพูดแป๊บนึงเพื่อคิดคำต่อ ท่อนแรกจะถูกตัดส่งไปเป็นคำสั่งที่ยังพูดไม่จบเลย — แก้ด้วย `queueWakeCommand(text)`/`flushWakeCommand()`: แทนที่จะ `form.requestSubmit()` ทันที จะต่อท้อความเข้ากับ `pendingCommandText` แล้วรีเซ็ตนาฬิกา 5 วิใหม่ทุกครั้งที่ได้ยินเสียงเพิ่ม จนกว่าจะเงียบจริงๆ ครบ 5 วิถึงส่งเป็นข้อความเดียว
  - ระหว่างรอ debounce (`isAccumulatingCommand = true`) พูดต่อได้โดย**ไม่ต้องพูด "Friday" ซ้ำ** — เงื่อนไขใน `onresult` เปลี่ยนจาก `if (followUpActive && !ytIsPlaying)` เป็น `if ((followUpActive || isAccumulatingCommand) && !ytIsPlaying)` ไม่งั้นท่อนพูดต่อ (ที่ไม่มีคำว่า Friday แน่นอนเพราะเป็นประโยคเดียวกัน) จะหลุดไปเช็ค `extractWakeCommand()` แล้วโดนทิ้งเป็น "missed" ไปเฉยๆ
  - **ผลข้างเคียงที่ตั้งใจยอมรับ**: ทุกคำสั่งเสียง (ไม่ว่าจะหยุดคิดหรือพูดรวดเดียวจบ) จะช้าลง 5 วิเทียบกับก่อนหน้านี้เสมอ เพราะระบบรอดูก่อนว่าจะพูดต่อไหมทุกครั้ง ไม่ใช่แค่ตอนตรวจจับว่าหยุดกลางคัน — เป็น trade-off ที่ผู้ใช้ยอมรับเพื่อแลกกับไม่ให้ประโยคถูกตัดกลางคัน
  - `queueWakeCommand()` เคลียร์ `followUpTimer` เดิมทุกครั้งด้วย (เหมือน `consumeFollowUpWindow()`) กันช่วงคุยต่อเนื่อง 15 วิเดิมหมดอายุกลางคันระหว่างรอ debounce แล้วค่อยเรียก `consumeFollowUpWindow()` จริงตอน `flushWakeCommand()` ก่อนส่ง
  - `stopWakeMode()` เคลียร์ `pendingCommandText`/`commandDebounceTimer`/`isAccumulatingCommand` ด้วย กันคำสั่งที่กำลังรอ debounce อยู่หลุดไปส่งทีหลังทั้งที่ปิดโหมดฟังตลอดไปแล้ว

## เสียงพูด TTS: เปลี่ยนจาก browser มาเป็น server-side (vachanatts)

เดิมใช้ `speechSynthesis` ของเบราว์เซอร์ (ฟรี ไม่ต้องตั้งอะไร) แต่เสียง Windows SAPI ที่มีในเครื่องฟังดูหุ่นยนต์เกินไป ไล่หาทางเลือกแล้วสรุปได้ดังนี้:
- **Piper TTS** — เช็คตรงจากซอร์สทางการ (GitHub `VOICES.md`, Hugging Face repo) ยืนยันแล้วว่า**ไม่มีเสียงภาษาไทยเลย** ทั้ง catalog ทางการและโมเดลชุมชน ตัดออก
- **ThonburianTTS / F5-TTS-THAI** — คุณภาพน่าจะดีสุด แต่เป็น diffusion model ไม่มี GPU จะช้ามาก (หลายวิ/ประโยค) ไม่เหมาะกับ voice assistant ที่ต้องตอบไว
- **`facebook/mms-tts-tha`** — VITS เบา (36M params) แต่เป็นโมเดลรวม 1000+ ภาษา ไม่ได้เน้นภาษาไทยโดยเฉพาะ
- **เลือกใช้ `vachanatts` (engine `vachana` ของ PyThaiNLP/`pythaitts`) เรียก `Voice`/`SpeechConfig` ระดับล่างตรงๆ** — Thai-specific, ONNX/VITS, เบา, รองรับข้อความปนอังกฤษ/ตัวเลขได้ (ทดสอบคำว่า "FRIDAY", "Gemini API", "27" แล้วผ่าน) — engine เริ่มต้นของ pythaitts (`lunarlist_onnx`) ใช้ไม่ได้เพราะช้ากว่ามากและ error ทันทีถ้ามีตัวอักษรอังกฤษปน
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
- UI: dropdown `#engineSelect` มุมขวาบน (เหนือ `#voiceSelect`) จำค่าไว้ใน `localStorage` key `friday_tts_engine` — ตอนเลือก `google` จะซ่อน `#voiceSelect` อัตโนมัติ (คลาส `.hidden`) เพราะรายชื่อเสียง `th_f_1` ฯลฯ มีความหมายเฉพาะ `vachana` เท่านั้น
- ข้อเสียของ Google engine (บอกผู้ใช้ไปแล้ว): endpoint ไม่เป็นทางการ ต้องมีเน็ต ปรับ noise/speed ผ่าน API ไม่ได้เหมือน vachana (Google TTS API มีแค่ normal/slow ไม่มี "เร็วขึ้น") และเสี่ยงโดน rate-limit ถ้าเรียกถี่ — เหมาะเป็น fallback/ของเล่นเปรียบเทียบมากกว่าใช้หลัก
- **ความเร็วพูดของ Google engine ช้ากว่า vachana มาก** — วัดจริงประโยคเดียวกัน: vachana ~3.66 วิ vs google ~6.79 วิ (ช้ากว่าเกือบ 2 เท่า) เพราะ Google TTS API ไม่มีพารามิเตอร์ปรับความเร็วแบบ vachana's `length_scale` แก้โดยเร่ง `ttsAudio.playbackRate = 1.4` ใน `app.js` เฉพาะตอน `selectedEngine === 'google'` เท่านั้น (vachana ยังคง 1.0 เหมือนเดิมเพราะปรับ SPEED ที่ต้นทางอยู่แล้ว) เบราว์เซอร์คง pitch อัตโนมัติเลยไม่ใช่เสียงเร่งเทปแบบตลก ไม่ต้องประมวลผลเสียงเพิ่มฝั่ง server เลย
- ติดตั้ง `gTTS` ดันให้ `click` conflict กับ `huggingface-hub` (ที่ `vachanatts` ใช้โหลดโมเดล) เล็กน้อยตาม pip resolver warning แต่ทดสอบจริงแล้วทั้งคู่ import/ทำงานได้ปกติไม่มีปัญหา (อัปเกรด `click` เป็น `>=8.4.2` ให้ `huggingface-hub` พอใจ แล้ว `gTTS` ก็ยังใช้ได้)

**บทเรียนตอน debug feature นี้ — อย่าเชื่อ error ที่มาจาก curl -d ข้อความไทยตรงๆ ใน Bash tool บน Windows:**
ตอนทดสอบเจอ `/api/tts` ตอบ 500 ทุกครั้งที่ส่งข้อความไทยสั้นๆ (เช่น "สวัสดี") ผ่าน `curl -d '{"text":"...ภาษาไทย..."}'` พร้อม traceback ลึกไปถึง `vachanatts/TH_G2P.py` (`IndexError: list index out of range` เพราะ `word_tokenize()` คืนลิสต์ว่าง) — ไล่หาสาเหตุอยู่นานมาก (ลอง thread lock ป้องกัน race ก็ยังไม่หาย) สุดท้ายพิสูจน์ได้ว่า **ต้นเหตุคือ Git Bash/Windows เข้ารหัสอาร์กิวเมนต์ `-d` ที่มีอักษรไทยผิดเพี้ยนเป็น `?` ล้วนๆ ก่อนถึง curl.exe เลย** (เหมือนปัญหา mojibake ที่เจอตอนต้น session แต่รอบนี้ไปทำ **request body ที่ส่งจริงพัง** ไม่ใช่แค่ปัญหาแสดงผลที่ console) ยืนยันได้ชัดโดยเขียน JSON body ลงไฟล์ UTF-8 ด้วย Write tool ก่อน แล้วยิงด้วย `curl --data-binary @file.json` แทน — หายขาดทันที เบราว์เซอร์จริง (`fetch()` + `JSON.stringify()`) เข้ารหัส UTF-8 ถูกต้องอยู่แล้ว ไม่เจอปัญหานี้เลย
**บทเรียน**: ทดสอบ API ที่รับข้อความไทยผ่าน `curl` บน Windows/Git Bash เสมอต้องส่งผ่าน `--data-binary @ไฟล์.json` (เขียนไฟล์ผ่าน Write tool ที่เป็น UTF-8 แท้) ห้ามใส่ข้อความไทยเป็น inline `-d '...'` ตรงๆ เด็ดขาด ไม่งั้นจะเจอ error ปลอมที่ดูเหมือนบั๊กจริงจังของ backend/library ทั้งที่จริงๆ แค่ shell เข้ารหัสอาร์กิวเมนต์พัง

## คลื่นเสียงรอบวง (wave-ring)

Bar 40 อันรอบ core ขยับตามข้อมูลจริง 2 แหล่งต่างกันตามสถานะ (ไม่ใช่ animation สุ่มเล่นๆ):
- **ตอนไมค์เปิดฟัง** (`isMicOpen()` true) — amplitude จริงจากไมค์ผ่าน `getUserMedia` + Web Audio `AnalyserNode` (`ensureMicAnalyser()`) แม่นยำเต็มที่
- **ตอน FRIDAY กำลังพูด** (`ttsSpeaking` true) — ตั้งแต่เปลี่ยนมาเล่นเสียงผ่าน `<audio>` element จริง (จาก `/api/tts`) เลยต่อ Web Audio `AnalyserNode` เข้ากับ `createMediaElementSource(ttsAudio)` ได้ตรงๆ (`ensureTtsAnalyser()`) — เป็น **amplitude จริงเหมือนฝั่งไมค์เป๊ะ** ไม่ใช่ของประมาณแบบตอนใช้ `speechSynthesis` (ที่ต้องอาศัย `onboundary` event มาขับคลื่นแทนเพราะดึง waveform จริงไม่ได้)

**สีของ core/wave/glow** — ผูกกับ `engagedActive` (ไม่ใช่แค่ไมค์เปิดหรือเปล่า และกว้างกว่า `followUpActive`):
- ตอนแค่เปิดไมค์รอฟังคำว่า "Friday" เฉยๆ (ยังไม่ได้เรียก) → สีฟ้า (cyan) เดิม
- **พอได้ยินคำว่า "Friday" ปุ๊บ** → เปลี่ยนเป็น**สีเขียว** (`--active-color`) ทันที ไม่ต้องรอคำตอบมาก่อน — ครอบคลุมช่วงกำลังประมวลผลและกำลังตอบด้วย
- ค้างเขียวต่อเนื่องได้ข้ามหลายรอบคุยต่อ (follow-up) โดยไม่กระพริบกลับ ตราบใดที่ยังคุยกันต่อภายใน 15 วิ
- ต่อเมื่อ**เงียบครบ 15 วิจริงๆ**หลัง FRIDAY ตอบครั้งล่าสุด (ไม่มีการคุยต่อ) ถึงจะกลับเป็นฟ้า ต้องพูด "Friday" นำใหม่

`followUpActive` (ตัวเดิม) ยังใช้แยกต่างหากสำหรับคุมว่า "ไม่ต้องพูด Friday ซ้ำไหม" ส่วน `engagedActive` คุมสีอย่างเดียว เริ่มไวกว่าและครอบคลุมกว้างกว่า

**แชท (`.log`) ก็ผูกกับ `engagedActive` ตัวเดียวกัน** — ซ่อนไว้เป็นค่าเริ่มต้น (`opacity:0` ใน `style.css`) โชว์เฉพาะตอนกำลังเรียก/คุยกับ FRIDAY จริง (`.chat-active` ถูก toggle ทุกเฟรมใน `renderWaveRing()`) หรือตอนเอาเมาส์ไปชี้ (`:hover` ล้วนๆ ฝั่ง CSS ไม่พึ่ง JS) เพื่อให้ hover ใช้ได้แม้ตอนซ่อนอยู่เลยไม่ใช้ `pointer-events:none`
- `engagedActive` ไม่ได้จำกัดแค่ voice/wake mode แล้ว — `form.addEventListener('submit', ...)` ตั้งเป็น `true` ทันทีตอนส่งข้อความ ไม่ว่าจะพิมพ์, กดพูด (push-to-talk), หรือสั่งผ่าน wake mode ก็ตาม แชทเลยโผล่มาให้เห็นทันทีที่เริ่มคุย ไม่ใช่แค่ตอนพูดคำว่า "Friday" เท่านั้น
- `startFollowUpWindow()` ถูกเรียกไม่มีเงื่อนไข (`if (wakeMode)` เดิม) หลัง `speak()` จบทุกเส้นทาง รวมถึง error path (`catch` ใน submit handler) ด้วย — กันแชท/สีเขียวค้างตลอดไปถ้า request ล้มเหลว แต่ `followUpActive` (ข้อความ "ฟังต่อเนื่อง" + ไม่ต้องพูด "Friday" ซ้ำ) ยังคงมีความหมายเฉพาะตอน `wakeMode` เปิดจริงเท่านั้น (`followUpActive = wakeMode` ใน `startFollowUpWindow()`) เพราะ text นั้นสื่อว่า STT กำลังฟังต่อเนื่องอยู่จริง ซึ่งเป็นจริงเฉพาะตอน wake mode เปิด
- **บั๊กจริงที่เจอ**: error handler ของ `recognition.onerror`/`wakeRecognition.onerror` (เช่น ไม่ได้สิทธิ์ไมค์ `not-allowed`) เรียก `addLine('friday', ...)` ตรงๆ โดยไม่ได้ตั้ง `engagedActive = true` ก่อน — ข้อความเลยถูกเพิ่มเข้า DOM จริงแต่ **มองไม่เห็น** (แชทซ่อนอยู่) ผู้ใช้เจอว่า "เรียก Friday แล้วไม่มีอะไรเกิดขึ้นเลย" ทั้งที่จริงๆ FRIDAY พยายามแจ้ง error (เช่นสิทธิ์ไมค์หลุด) อยู่ แค่มองไม่เห็น — แก้โดยเพิ่มฟังก์ชัน `announceSystemNotice(text)` (`engagedActive = true` + `addLine()` + `startFollowUpWindow()`) แล้วเปลี่ยน error handler ทั้งหมดให้เรียกผ่านนี้แทน `addLine()` ตรงๆ — **บทเรียน**: ทุกจุดที่เพิ่มข้อความลง `.log` ต้องเช็คว่าตั้ง `engagedActive` ไว้ก่อนเสมอ ไม่งั้นข้อความจะถูกซ่อนแบบเงียบๆ โดยไม่มี error ให้เห็นเลย

## บุคลิกของ FRIDAY

- **เพศหญิง** — ระบุไว้ชัดใน system prompt ทั้ง `friday.py`/`server.py` ให้ใช้คำลงท้าย/สรรพนามผู้หญิงเสมอ (ค่ะ, ดิฉัน/หนู) และ default เสียง TTS เป็น `th_f_1` (ผู้หญิง)
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

```
friday-ai/
├── friday.py         # agent loop แบบ CLI (Step 0, ยังใช้ speechSynthesis ของเบราว์เซอร์ไม่ได้เพราะเป็น CLI)
├── server.py         # FastAPI backend — เสิร์ฟหน้าเว็บ + /api/chat + /api/quota + /api/tts
├── personality.py    # SYSTEM_PROMPT ที่ friday.py กับ server.py ใช้ร่วมกัน (กันสองไฟล์เพี้ยนไปคนละทาง)
├── tools.py          # tool ที่ agent เรียกใช้ได้ (search_web ผ่าน ddgs, open_youtube/control_youtube ผ่าน yt-dlp)
├── tts.py            # เสียงพูดไทยฝั่ง server (pythaitts engine vachana, ปรับ noise param แล้ว)
├── static/
│   ├── index.html    # โครง HUD (core, panel มุม 4 มุม, log, input bar, quota readout)
│   ├── style.css      # ธีม dark cyan + animation, boot sequence, particles, scanline/vignette
│   └── app.js         # แชท + boot + particles + core เอียงลอยเอง + panel มุม 4 มุมที่ผูกกับข้อมูลจริง + TTS/STT
├── voices/            # แคชโมเดลเสียง ONNX ที่ pythaitts โหลดมา (ไม่ commit)
├── venv/              # virtualenv (ไม่ commit)
├── .env               # GEMINI_API_KEY (ไม่ commit)
├── .gitignore
└── requirements.txt
```

## วิธีรัน

**แบบ CLI (Step 0):**
```bash
cd friday-ai
venv\Scripts\activate            # Windows
pip install -r requirements.txt  # ครั้งแรกครั้งเดียว
python friday.py
```

**แบบเว็บ (Jarvis HUD):**
```bash
cd friday-ai
venv\Scripts\activate
python server.py
```
แล้วเปิดเบราว์เซอร์ไปที่ `http://127.0.0.1:8000/` — ตอนนี้ chat session เป็นแบบ session เดียวเก็บใน memory ของ server (เหมาะกับ personal use คนเดียว ยังไม่รองรับหลาย user/หลายแท็บพร้อมกันแบบแยกบทสนทนา)

**หมายเหตุ:** ทุกครั้งที่แก้ `server.py`/`tools.py`/`tts.py` ต้อง restart server เอง (กด Ctrl+C แล้วรัน `python server.py` ใหม่) ไม่มี auto-reload — server เริ่มช้าลงกว่าเดิมเล็กน้อย (~3-5 วิ) เพราะต้องโหลดโมเดลเสียง TTS ตอน start

## Quota tracking

`server.py` เก็บ state เอง (`quota_state`) นับจำนวนครั้งที่เรียก Gemini สำเร็จวันนี้ (`used_today`, รีเซ็ตทุกเที่ยงคืนตามเวลาเครื่อง — เป็นค่าประมาณ เพราะ Google ไม่เปิดเผยเวลารีเซ็ตจริงของ free tier) ส่วน `limit` จะรู้ค่าจริงก็ต่อเมื่อโดน HTTP 429 ครั้งแรกเท่านั้น (parse จาก `QuotaFailure.violations[0].quotaValue` ในตัว error) และ `cooldown_until` มาจาก `RetryInfo.retryDelay` ของ error เดียวกัน

**Optimize แล้ว:** เดิมหน้าเว็บ poll `GET /api/quota` ทุก 1 วินาที (86,400 request/วันแม้ไม่ได้ใช้เลย) ตอนนี้ sync กับ server ทุก `QUOTA_SYNC_MS` (5 วิ) เท่านั้น ส่วนตัวนับถอยหลัง cooldown ที่ต้องขยับทุกวินาทีให้ลื่น คำนวณเอาเองฝั่ง client จากค่า `cooldown_seconds` ล่าสุด + เวลาที่ผ่านไปจริง (`renderQuotaDisplay()`) ไม่ต้องยิง request ทุกครั้ง — ทดสอบแล้วว่า request ลดจาก ~12 ครั้ง/12วิ เหลือ ~2-3 ครั้ง/12วิ และเลขนับถอยหลังยังแม่นยำ (ทดสอบ edge case ค่าติดลบด้วย ผลลัพธ์ clamp เป็น 0 ถูกต้อง)

## งานถัดไปสำหรับ Claude Code

Step 0-1 กับเว็บ UI เสร็จแล้ว งานถัดไปคือ **Step 2: เพิ่ม memory ถาวร (SQLite)** ให้ FRIDAY จำเรื่องเก่า-ใหม่ได้ข้ามเซสชัน (ตอนนี้ restart server ทีก็ลืมบทสนทนาหมด)
