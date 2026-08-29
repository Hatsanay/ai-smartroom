# จัสมิน — แผนพัฒนา (Roadmap)

> **ชื่อผู้ช่วยคือ "จัสมิน" เสมอ — ไม่เปลี่ยน** "Jarvis" ในเอกสารนี้เป็นแค่ **เกณฑ์เทียบความสามารถ**
> (AI สไตล์ Iron Man ที่บุคลิก จัสมิน อ้างอิงอยู่แล้ว) ไม่ใช่ชื่อใหม่ ห้าม rename
> **เป้าหมาย:** ยกความสามารถของ จัสมิน ให้ใกล้เคียงระดับ Jarvis มากที่สุด
> **ข้อกำหนด:** อยู่บน **สถาปัตยกรรมเดิม** — FastAPI + HUD (vanilla JS ES modules) + Gemini function calling + `tools/` package
> ไม่ย้ายไป agent framework สำเร็จรูป (เหตุผลท้ายเอกสาร)
> **รูปแบบสุดท้าย: ไม่ใช่แค่เว็บ** — ต้องมี **โปรแกรม desktop รันได้ทั้ง Windows และ Linux** (+ headless บน Pi, + Telegram) — ดูหัวข้อ "รูปแบบที่ส่งมอบ"

อัปเดตล่าสุด: 2026-08-29

**ตัดสินใจ 2026-08-29:**
- **Phase 1 = ทำ Tier 1 + Tier 2 + Tier 3 (ฟีเจอร์ทั้งหมด) บนเว็บให้ครบ** — ยกเว้น STT-server-side + packaging ที่เป็น Phase 2 · *(เดิมเคยจำกัดแค่ Tier 1 แล้วประเมินใหม่ — ผู้ใช้เปลี่ยนใจ เอา Tier 2/3 กลับมา)*
- **`control_home` เลื่อนออกไปก่อน** — ยังไม่มี Home Assistant + ฮาร์ดแวร์ (ESP32/รีเลย์/อุปกรณ์จริง) ใดๆ เลย · เริ่มได้เมื่อฮาร์ดแวร์พร้อม
- **ตัด LiteLLM ออกจากแผน** — ใช้ Gemini อย่างเดียว (เก็บ automatic function calling ของ `google-genai` ไว้ ไม่ต้องเขียน tool loop เอง) · ยอมผูกกับ Gemini + โควตา free tier
- งานค้าง session ก่อนหน้า **commit แล้ว** (commit `6971792`, working tree สะอาด, branch `main`)

---

## เฟสการทำงาน (ลำดับใหญ่)

**Phase 1 — ทำฟีเจอร์ทั้งหมดบนเว็บให้ครบ** ← ทำอยู่ตอนนี้
เว็บ HUD รันได้ทุก OS อยู่แล้ว (ผ่านเบราว์เซอร์ Chrome/Edge) — ใช้ Web Speech API สำหรับ wake word ต่อไป
ทำ **Tier 1 → Tier 2 → Tier 3** (ยกเว้น STT-server-side ที่อยู่ Phase 2) · `control_home` พักไว้จนกว่าฮาร์ดแวร์พร้อม
**ไม่ต้องแตะ STT / packaging**

**Phase 2 — โปรแกรม desktop (Windows + Linux)** ← หลัง Phase 1 เสร็จ
ย้าย STT มา server-side (openWakeWord + faster-whisper) → แพ็กเกจ pywebview + PyInstaller → `.exe` / AppImage (Capstone)
Phase นี้เท่านั้นที่ต้องทำเรื่อง STT/webview/packaging — Phase 1 ไม่ต้องรอ

> STT-server-side, barge-in, headless-Pi, desktop packaging = **Phase 2 ทั้งหมด** ไม่ใช่ blocker ของงานฟีเจอร์ใน Phase 1

---

## สถานะปัจจุบัน (ทำแล้ว)

- ✅ **Group A (เลขา)** — `memory` / `tasks` / `reminders` / `email` / `daily_briefing` (commit แล้ว)
- ✅ **เสียง** — wake word "จัสมิน" (regex กว้าง) + คุยต่อเนื่อง 15 วิ + TTS ไทย server-side (vachana/gTTS) + audio ducking + wave-ring จาก amplitude จริง
- ✅ **ข้อมูล** — `search_web` (ddgs) / `get_weather` (Open-Meteo, ปรับตามคำถาม) / อีเมล Gmail เต็ม (อ่าน/ค้น/ส่ง/ไฟล์แนบ/ลายเซ็นอัตโนมัติ/ยืนยัน 2 ขั้น)
- ✅ **ไฟล์ในคอม** — `list_files`/`read_file`/`create_folder`/`write_file`/`delete_path` จำกัดโฟลเดอร์ + audit log
- ✅ **YouTube** — เปิด/คุม/เต็มจอ ผ่าน HUD (เสียงเริ่ม 25% ตอนเปิดใหม่, เปลี่ยนเพลงคงเสียงเดิม)
- ✅ **บริบท** — รู้เวลาปัจจุบัน (`_now_preamble`) + ตำแหน่ง (browser geolocation)

รวม tool ที่ Gemini เรียกได้ตอนนี้: 24 ตัว

---

## เช็คลิสต์ความเป็น Jarvis

สถานะ: ✅ มีแล้ว · 🟡 มีบางส่วน · ❌ ยังไม่มี

### 1. เสียง & บทสนทนา
| ต้องมี | สถานะ | หมายเหตุ |
|---|---|---|
| Wake word + ฟังตลอด | ✅ | "จัสมิน" + regex กว้าง |
| คุยต่อเนื่องไม่ต้องเรียกชื่อซ้ำ | ✅ | 15 วิ |
| เสียงพูดไทยธรรมชาติ + ลดเสียงเพลงตอนพูด | ✅ | vachana/gTTS + ducking |
| แทรก/ขัดกลางประโยคได้ | ❌ | ต้องทำ AEC (`getUserMedia echoCancellation`) + STT ที่ฟังระหว่างพูด |
| Streaming TTS (พูดทีละประโยคไม่รอ synth จบ) | ❌ | ลด perceived latency |
| โหมดไม่มีจอ (กล่องเสียงอย่างเดียว) | ❌ | ตอนนี้ต้องเปิดแท็บเบราว์เซอร์ค้าง |

### 2. บุคลิก & ความเป็นเชิงรุก
| ต้องมี | สถานะ | หมายเหตุ |
|---|---|---|
| บุคลิกฉลาด กระชับ มีอารมณ์ขัน (สไตล์ Iron Man) | ✅ | |
| พูดขึ้นเองโดยไม่ต้องถาม ("มีสายเข้า", "ฝนกำลังจะตก") | ❌ | event → push → speak (มี channel `notify` อยู่แล้ว) |
| ทักตอนเช้า / บรีฟอัตโนมัติ | ❌ | `daily_briefing` มีแล้ว แค่ให้ scheduler ยิงเอง |

### 3. ความจำ & การรับรู้บริบท
| ต้องมี | สถานะ | หมายเหตุ |
|---|---|---|
| ความจำ (fact) ถาวรข้ามเซสชัน | ✅ | Group A (`remember`/`recall`) |
| **จำบทสนทนาข้ามการ restart server** | ❌ | ตอนนี้ `chat` เป็น object ใน RAM — restart แล้วลืมทั้งบทสนทนา เหลือแค่ fact · เก็บ turn ลง `jusmin.db` + rehydrate ตอน start |
| รู้เวลาปัจจุบัน / ตำแหน่ง | ✅ | `_now_preamble` / geolocation |
| จำเอง (สกัด fact จากบทสนทนาโดยไม่ต้องสั่ง) | ❌ | pass เบื้องหลังเรียก `remember()` |
| **รู้สถานะเครื่อง** (แบต / เน็ต / CPU / หน้าต่างที่โฟกัสอยู่) | ❌ | `psutil` + platform-specific — ให้ จัสมิน มี ambient awareness |
| รู้ว่าในบ้านมีอุปกรณ์อะไร เปิด/ปิดอยู่ ใครอยู่บ้าน | ❌ | ผูกกับหมวด 6 (`control_home`) |
| ปฏิทิน / ตารางนัด | ❌ | Google Calendar |
| ค้นความจำแบบ semantic | 🟡 | ตอนนี้ LIKE — พอ fact เยอะค่อยทำ FTS5/embedding |

### 4. ข้อมูล & การค้นคว้า
| ต้องมี | สถานะ |
|---|---|
| ค้นเว็บ / อากาศ / อีเมล | ✅ |
| อ่านบทความจาก URL (`read_url`) | ❌ (trafilatura ฟรี) |
| สรุปข่าว (RSS) | ❌ (`feedparser`) |
| คำนวณ / แปลงหน่วย / ค่าเงิน / หุ้น | ❌ (Frankfurter API ฟรี + calc) |
| **ร่างเอกสาร/จดหมาย/สรุปยาว** (`draft_document` → `write_file` เป็น .md) | ❌ |
| ข้อมูลเรียลไทม์: จราจร / รถเมล์ / BTS | ❌ |

### 5. งาน & การมอบหมาย
| ต้องมี | สถานะ |
|---|---|
| จดงาน + กำหนดส่ง + ความด่วน | ✅ |
| ตั้งเตือนตามเวลา (เด้ง + พูดเอง) | ✅ |
| บรีฟสรุปวัน | ✅ |
| นาฬิกาปลุก / จับเวลา / pomodoro | ❌ |
| subagent ทำงานเบื้องหลัง (ไม่กิน context หลัก) | ❌ |
| **skills ที่ปรับปรุงตัวเองได้** (จำวิธีทำงานซับซ้อนเป็นไฟล์ instruction แล้วเรียกใช้ทีหลัง) | ❌ |

### 6. คุมบ้าน & โลกจริง  ← ช่องว่างใหญ่สุด (อยู่ในชื่อโปรเจกต์ "ai-smartroom")
| ต้องมี | สถานะ | หมายเหตุ |
|---|---|---|
| `control_home()` — ไฟ / แอร์ / ทีวี / มอเตอร์ ผ่าน Home Assistant | ❌ | roadmap Step 3-4 · **หัวใจของ Jarvis** |
| คุมเพลง YouTube | ✅ | (เฉพาะบนหน้าเว็บ) |
| ลำโพงทั้งบ้าน | ❌ | |
| ประตู / ล็อก / กล้องวงจรปิด | ❌ | |
| ฉาก/รูทีน ("โหมดดูหนัง" = หรี่ไฟ + เปิดทีวี + ปิดม่าน) | ❌ | ต้องมี `control_home` ก่อน |
| safety layer — whitelist อุปกรณ์/action ก่อนสั่ง | ❌ | จำเป็นคู่กับ `control_home` |

### 7. อยู่ทุกที่ (presence)
| ต้องมี | สถานะ | หมายเหตุ |
|---|---|---|
| รัน 24/7 บน Pi เป็น service (auto-start ตอนบูต) | ❌ | ตอนนี้รันบนเครื่อง dev + เปิดแท็บเอง |
| คุมผ่านมือถือ (Telegram/LINE bot) | ❌ | Telegram ง่ายสุด ไม่ต้องมี public URL |
| แจ้งเตือนนอกแท็บเบราว์เซอร์ | 🟡 | ตอนนี้ browser-poll เท่านั้น |

### 8. การมองเห็น & เดสก์ท็อป (perception)
| ต้องมี | สถานะ | หมายเหตุ |
|---|---|---|
| วิเคราะห์รูป / อ่านภาพหน้าจอ (`analyze_image`) | ❌ | Gemini เป็น multimodal อยู่แล้ว แค่ต่อ tool |
| **ถ่าย screenshot + อ่าน/เขียน clipboard** | ❌ | `mss`/`ImageGrab` + `pyperclip` — "จัสมิน อันนี้บนจอฉันคืออะไร" / "ก๊อปข้อความนี้ให้หน่อย" |
| อ่าน/สรุป PDF, เอกสาร | 🟡 | ไฟล์แนบดาวน์โหลดได้แล้ว แต่ยังไม่ auto-อ่าน |
| กล้องดูห้อง / รู้ว่าใครเข้ามา | ❌ | ต้องมีกล้อง + vision loop |

### 9. ความปลอดภัย & การเข้าถึง
| ต้องมี | สถานะ | หมายเหตุ |
|---|---|---|
| เข้าถึงไฟล์จำกัดโฟลเดอร์ + audit log | ✅ | |
| ยืนยันก่อนส่งเมล (2 ขั้นบังคับในโค้ด) | ✅ | |
| รู้ว่ากำลังคุยกับใคร (จำเสียง / กันคนแปลกหน้าสั่ง) | ❌ | speaker recognition |
| confirm-gate มาตรฐาน | 🟡 | ตอนนี้มีจริงแค่ `send_email` — `delete_path`/`control_home` ควรมีแบบเดียวกัน |

### 10. โครงสร้างพื้นฐาน
| ต้องมี | สถานะ | หมายเหตุ |
|---|---|---|
| ติดตามโควตา + cooldown | ✅ | |
| `setup.bat` / `dev.bat` | ✅ | |
| สลับโมเดลได้ (ไม่ผูก Gemini) — LiteLLM | ⛔ ไม่ทำ | ตัดออก 2026-08-29 — ใช้ Gemini อย่างเดียว ยอมผูกกับโควตา free tier (แลกกับเก็บ automatic function calling ไว้) |
| log ว่า จัสมิน ทำอะไรไปบ้าง (นอกจาก file audit) | ❌ | |

---

## รูปแบบที่ส่งมอบ (จะไม่ใช่แค่เว็บ) — **Phase 2**

> ทั้งหัวข้อนี้ = Phase 2 ทำหลังเว็บ (Phase 1) ครบแล้ว

core = FastAPI server + `tools/` เดิม · frontend เปลี่ยนได้หลายแบบ **พร้อมกัน** โดยไม่รื้อ core:

| รูปแบบ | สถานะ | หมายเหตุ |
|---|---|---|
| เว็บ HUD (เบราว์เซอร์) | ✅ | ที่มีอยู่ตอนนี้ |
| **โปรแกรม desktop (Windows + Linux)** | ❌ | เป้าหมายสุดท้าย |
| headless บน Raspberry Pi 24/7 | ❌ | Tier 1 #2 |
| Telegram / มือถือ | ❌ | Tier 1 #3 |

### เงื่อนไขสำคัญของ desktop app: ต้องย้าย STT มาฝั่ง server ก่อน

**ปัญหา:** wake word ตอนนี้ = Web Speech API (`SpeechRecognition`) — ของ Chrome/Edge เท่านั้น + ส่งเสียงไป Google · desktop shell ที่ใช้ OS webview (Tauri/pywebview) บน Linux (WebKitGTK) **ไม่มี** `SpeechRecognition` · ทางเดียวที่ Web Speech ครบ Win+Linux = บันเดิล Chromium (Electron ~150MB, ไม่คุ้ม)

**แนวทางที่เลือก — แยกเป็น 2 งาน:**

| งาน | เครื่องมือ | เหตุผล |
|---|---|---|
| **1. ตรวจจับ wake word "จัสมิน"** (รันตลอด) | **openWakeWord** — โมเดล "จัสมิน" custom (train ใน Colab, gen ตัวอย่างด้วย TTS) | ฟรี Apache-2.0 · ~1-2MB · offline · กิน CPU น้อยมาก · รัน 24/7 ได้ทั้ง desktop และ Pi |
| **2. ถอดเสียงประโยคคำสั่ง** (เป็นช่วงๆ หลัง wake) | **faster-whisper `small`** (local, default) · `medium`/GPU บนเครื่องแรง · เครื่องอ่อน/Pi → `whisper.cpp base` หรือ Vosk | ไทยดี · offline · โมเดล ~500MB โหลดครั้งแรก (เหมือน `voices/`) |
| 2. (ทางเลือกออนไลน์) | **Whisper API / `gpt-4o-transcribe` / Deepgram** | แม่นสุด ไม่กินเครื่อง — สำหรับคนไม่ซีเรียส privacy |

`.env`: `WAKE_ENGINE=openwakeword` · `STT_ENGINE=whisper-local` (`whisper-api` / `vosk` ได้)

**Audio pipeline (ทำให้ใช้ได้ทุก webview):** frontend ไม่แตะ `SpeechRecognition` เลย — `getUserMedia()` → ดาวน์แซมเปิล 16kHz mono → สตรีม PCM ผ่าน **WebSocket `/ws/audio`** (เสียงดิบล้วน ทำงานใน Tauri/pywebview/Electron/เบราว์เซอร์เหมือนกันหมด) · server รัน openWakeWord ตลอด → fire → บัฟเฟอร์ ~5 วิ → faster-whisper → เข้า `chat_endpoint` เดิม · ส่ง event `{wake}` / `{transcript}` กลับ

**ผลพลอยได้:**
- **barge-in** — server มีสตรีมเสียงตลอด รู้ว่าผู้ใช้พูดแทรกตอน จัสมิน พูดอยู่
- **headless บน Pi** — entrypoint เล็กๆ อ่านไมค์ผ่าน `sounddevice` ตรงๆ ไม่ต้องมีเบราว์เซอร์เลย
- `voice.js` **ง่ายลงมาก** — ตัด hack restart-loop / debounce กัน STT ตัดคำทิ้งได้ เหลือแค่สตรีมเสียง + รับ event
- offline · ไม่พึ่ง Google · ใช้ได้กับ Telegram (ส่ง voice message → server ถอดเสียงตัวเดียวกัน)

deps ใหม่: `openwakeword`, `faster-whisper`, `sounddevice` (`websockets` มากับ FastAPI แล้ว)

### แพ็กเกจ desktop
- **pywebview + PyInstaller** (แนะนำ) — ทั้ง app = process Python เดียว เปิดหน้าต่าง native ชี้ไป FastAPI local · HUD เดิม (HTML/CSS/JS) ไม่ต้องแก้ · ไม่ต้องมี JS build toolchain
  - Windows: ต้องมี WebView2 runtime (มากับ Win11 / auto-install บน Win10) → `.exe` เดียว
  - Linux: ต้องมี `PyGObject` + `WebKit2` (system package) → distribute เป็น **AppImage** (รันได้ทุก distro) หรือ `.deb`/Flatpak
- ทางเลือก: **Tauri** (ไฟล์เล็กสุด, Rust shell + Python sidecar — moving parts เยอะกว่า) · **Electron** (ง่ายสุด, ใหญ่สุด, Speech API ทำงานทุกที่ถ้ายังไม่ย้าย STT)
- **system tray** (ย่อลง tray, ฟังอยู่เบื้องหลัง — Jarvis มาก) + ตัวเลือก auto-start ตอน login
- **user-data dir**: `jusmin.db`, `.env`, โมเดล TTS/STT, `voices/`, `logs/` → `%APPDATA%\Jusmin` (Windows) / `~/.local/share/jusmin` (Linux) — ไม่ใช่ข้างๆ binary
- first-run: บันเดิลหรือดาวน์โหลดโมเดล TTS/STT ครั้งแรก (เหมือน `voices/` ตอนนี้)

---

## ลำดับพัฒนา (เรียงตามคุ้มค่า/แรง)

> **implementation plan ละเอียดต่อฟีเจอร์** อยู่ใน `jusmin-ai/plans/NN-<ชื่อ>.md` — เขียนตอนเริ่มแต่ละอัน
> - [`plans/01-read-url-analyze-image.md`](jusmin-ai/plans/01-read-url-analyze-image.md) — code-complete (branch `phase1-tier1`), รอ user เทสเบราว์เซอร์ + commit
> - [`plans/02-media.md`](jusmin-ai/plans/02-media.md) — ค้น/โหลด/เปิดดู รูป+วิดีโอ — code-complete (branch `phase1-tier1`), รอ user เทส + commit

### Tier 1 — แกน Jarvis · เข้ากับโครงเดิม · **= งาน Phase 1**

**ทำใน Phase 1 (software-only ไม่ต้องรอฮาร์ดแวร์) — ลำดับที่แนะนำ:**

1. **`read_url` + `analyze_image`** ✅ code-complete (branch `phase1-tier1`, รอ user เทส + commit) — `plans/01`
   - `tools/web.py` +`read_url(url)` (trafilatura + SSRF guard) · `tools/vision.py` *(ใหม่)* +`analyze_image(path, question)` (Gemini vision, client แยก lazy)
1.5. **ค้น/โหลด/เปิดดู รูป+วิดีโอ** — `plans/02-media.md` (ผู้ใช้ขอแทรก) — `search_media` / `download_media` (รูป sync, วิดีโอ async+notify) / `view_media` (overlay เต็มจอ) + endpoint `/api/media` (containment + Range) + HUD `media.js`/`media.css` · จัสมิน เลือกโฟลเดอร์ย่อยเอง · วิดีโอไม่ cap
2. **Telegram bot**
   - refactor `server.py`: ดึงแกนของ `chat_endpoint` เป็น `handle_message(text, geo=None, source="web") -> (reply, actions)` ที่ web + telegram เรียกร่วมกัน
   - `channels/telegram.py` — `python-telegram-bot` (long-polling ไม่ต้องมี public URL) · `.env`: `TELEGRAM_BOT_TOKEN` + `TELEGRAM_ALLOWED_USER_ID` (กันคนอื่นสั่ง)
   - action ที่เป็น browser (`play_youtube`, `show_weather`) → บน Telegram ส่งเป็นข้อความ/รูปแทน
3. **Event-watchers + proactive** (ความเป็นเชิงรุก)
   - `tools/watchers.py` — poller เบื้องหลังใน scheduler thread เดิม: เมลใหม่จากคนสำคัญ / reminder / อากาศเปลี่ยน (จะตก/ร้อนจัด) / ปฏิทินใกล้ถึง → `notify.push()` → `notify.js` พูด
   - scheduler ยิง `daily_briefing` เอง (เวลา + สวิตช์เปิด/ปิด เก็บผ่าน `remember()` หรือ config)
4. **รัน 24/7 บน Pi เป็น service**
   - `deploy/jusmin.service` (systemd, `Restart=always`, `WantedBy=multi-user.target`) + คู่มือ
   - HUD เปิดบนแท็บเล็ต/มือถือในบ้าน ชี้มาที่ IP ของ Pi · **headless แท้ (ไม่มีเบราว์เซอร์) รอ STT ของ Phase 2**

**เลื่อนไว้ (ยังไม่มีฮาร์ดแวร์ ณ 2026-08-29):**
- ⏸️ **`control_home()` + Home Assistant + safety whitelist** — `tools/home.py` เรียก HA REST API (`/api/services/...`) · whitelist entity+action ก่อนสั่ง (ไม่เชื่อ LLM) · confirm-gate ใช้ pattern เดียวกับ `send_email` (`_pending_send`) · เริ่มเมื่อมี HA + ESP32/รีเลย์/อุปกรณ์

> **หลัง Tier 1 เสร็จ → ทำ Tier 2 → Tier 3 ต่อ** (ยังอยู่ Phase 1 / บนเว็บ) แล้วค่อยขึ้น Phase 2

### Tier 2 — เพิ่มความลื่น/ฉลาด (Phase 1, หลัง Tier 1)
- **Conversation persistence** — เก็บทุก turn ลงตาราง `conversation` ใน `jusmin.db` · ตอน start rehydrate N turn ล่าสุดเข้า `chat` history → restart แล้วคุยต่อได้ (ตอนนี้ลืมหมด)
- **Auto-memory** — ใน `handle_message` หลังจบ turn: ถ้าผู้ใช้เผยข้อมูลส่วนตัว → Gemini call เบาๆ 1 ครั้งสกัดเป็น fact → `remember(tag="auto")` · หรือ system prompt สั่ง จัสมิน เรียก `remember()` เองเชิงรุก
- **Skills ปรับปรุงตัวเองได้** — `skills/*.md` (name + "ใช้เมื่อไหร่" + instruction) · `tools/skills.py`: list เข้า preamble (1 บรรทัด/skill), `use_skill(name)` คืน instruction เต็ม, `create_skill()`/`update_skill()` เขียนไฟล์ · **instruction ล้วน — ไม่ให้เขียนโค้ดรันเอง** (ประกอบ tool ที่ปลอดภัยอยู่แล้วเท่านั้น)
- **subagent** — `tools/subagent.py` `run_subagent(task, allowed_tools=[])`: `client.chats.create()` ใหม่ system prompt โฟกัส + tool ชุดย่อย + cap 8 รอบ → คืนแค่สรุป (ไม่กิน context หลัก)
- **timers / นาฬิกาปลุก / pomodoro** — `tools/timers.py` + scheduler + `notify` · HUD countdown panel (**ต้องมี `pending_action` queue ก่อน** — ดูหลักสถาปัตยกรรม)
- **ปฏิทิน** — `tools/gcal.py` Google Calendar API (OAuth ครั้งเดียว, token ใน user-data dir) — **หนักสุดในกลุ่มนี้** เพราะต้องมี OAuth flow
- **ข่าว** — `tools/news.py` `feedparser` + รายการ RSS ใน config
- **calc / currency / แปลงหน่วย** — `tools/calc.py`: `pint` (หน่วย) + Frankfurter API (ค่าเงิน, ฟรี) + เลขคณิตแบบปลอดภัย (ไม่ `eval`)
- **draft_document** — `tools/draft.py` `draft_document(kind, brief) -> เนื้อหา` (LLM ร่างจดหมาย/สรุป/บันทึก) → ผู้ใช้สั่ง `write_file` / `send_email` ต่อ
- **system status** — `tools/system.py` `psutil` (แบต/CPU/RAM/disk/เน็ต) + หน้าต่างโฟกัส (win: `pygetwindow` / linux: `wmctrl`) — **read-only** · HUD gauge panel
- **clipboard** — `tools/desktop.py` `read_clipboard()` / `write_clipboard(text)` (`pyperclip`)

### Tier 3 — ล้ำ แต่หนัก/เสี่ยง (Phase 1, หลัง Tier 2)
- **screenshot + อ่านหน้าจอ** — `tools/desktop.py` `screenshot()` (`mss`) → ป้อนเข้า `analyze_image` · "อันนี้บนจอฉันคืออะไร"
- **กล้องดูห้อง** — frontend `getUserMedia(video)` จับเฟรมเป็นระยะ → `/api/vision` → Gemini · "มีใครอยู่ในห้องไหม"
- **speaker ID** — embedding เสียง (`resemblyzer`) เทียบตัวอย่างเสียงเจ้าของ → กันคนแปลกหน้าสั่งงานสำคัญ (คู่กับ confirm-gate)
- **ฉาก/รูทีนบ้าน** — ต้องมี `control_home` ก่อน · เก็บ scene เป็น skill หรือตารางใน db
- **data-analysis sandbox** — รัน Python คำนวณใน subprocess จำกัดสิทธิ์ · **เสี่ยง — ทำอันท้ายสุด หรือข้าม**

### ไม่แนะนำ
- ให้ LLM เขียนโค้ดแล้วรันเอง (arbitrary code execution บนเครื่องผู้ใช้)
- browser automation เต็มรูปแบบ (Playwright — หนักเกินคุ้ม)
- subagent มี shell/terminal จริง (เสี่ยง)
- Electron เป็น shell หลัก (ใหญ่ 150MB) — ใช้ pywebview/Tauri หลังย้าย STT แล้วแทน

### Capstone (Phase 2) — โปรแกรม desktop (Windows + Linux)
ทำ**หลังย้าย STT มา server-side** แล้ว — แพ็กเกจ pywebview + PyInstaller → `.exe` / AppImage + system tray + auto-start · รายละเอียดในหัวข้อ "รูปแบบที่ส่งมอบ"

---

## หลักสถาปัตยกรรมของ Phase 1 (ทำตามนี้ทุกฟีเจอร์)

1. **`_pending_action` → queue** *(ทำก่อน timer / HUD panel หลายอันต่อเทิร์น)* — เปลี่ยน `_state.pending_action` จาก slot เดียวเป็น **list** · `chat_endpoint`/`handle_message` คืน `actions: []` · `main.js` วน dispatch ทีละอัน · แก้ข้อจำกัด "เปิดเพลง X แบบเต็มจอในประโยคเดียวไม่ได้" ไปด้วย
2. **shared `handle_message()`** — web / Telegram / (อนาคต) เรียกแกนเดียวกัน (`text, geo, source` → `reply, actions`) · action ที่เป็น browser (YouTube, การ์ดอากาศ, เต็มจอ, timer panel) เดกราดเป็นข้อความ/รูปบน channel ที่ไม่มี HUD
3. **event-watcher pattern** — ความเป็นเชิงรุก **ทั้งหมด** ไปทางเดียว: poller เบื้องหลัง (`tools/watchers.py`) → `notify.push()` → `notify.js` พูด · อย่ากระจายไปเขียน logic แจ้งเตือนซ้ำในหลาย tool
4. **HUD-panel principle** — ต่อจาก "ห้ามใส่ UI ข้อมูลปลอม": ทุก tool ที่ผลิตข้อมูล (`analyze_image`, ปฏิทิน, ข่าว, system status, timer) **ต้องมีพาเนล HUD ของตัวเอง** ที่ผูกข้อมูลจริง — ไม่งั้นตอบเป็นข้อความในแชทอย่างเดียว
5. **`JUSMIN_DATA_DIR` ตั้งแต่ตอนนี้** — path ของ `jusmin.db` / `.env` / โมเดล / `voices/` / `logs/` / `skills/` อ่านจาก env var เดียว (default = repo dir) เพื่อให้ Phase 2 packaging (user-data dir) ไม่ต้องรื้อทีหลัง
6. **quota Gemini free tier** — ทุก tool call + reasoning กิน quota · tool list ยาวขึ้นเรื่อยๆ → เลือก tool ช้าลง · เฝ้าดู ถ้าชนบ่อยพิจารณา (ก) จัดกลุ่ม tool ให้ Gemini เห็นน้อยลงต่อเทิร์น (ข) ย้ายไปรุ่น quota สูงกว่า — **ไม่ใช่ LiteLLM (ตัดแล้ว)**
7. **ทุก tool ที่ทำ action ออกนอก** (ส่งเมล, ลบไฟล์, คุมบ้าน) — confirm-gate แบบ `send_email` (`_pending_send` 2 ขั้น) ไม่ใช่ docstring อย่างเดียว

---

## ทำไมอยู่บนโครงเดิม (ไม่ย้าย framework)

พิจารณาแล้ว: **LiteLLM** (lib model-agnostic), **Letta/MemGPT** (memory engine), **Agno**, **Pydantic AI**, **CrewAI**, **Claude Agent SDK**, **Hermes Agent by Nous Research** — **ทั้งหมดไม่เอา** (LiteLLM ก็ตัดออก 2026-08-29, ใช้ Gemini อย่างเดียว)

- "เปลือก จัสมิน" ที่สร้างเอง = HUD Jarvis + wake word ไทย + TTS ไทย + audio choreography + บุคลิก + bridge `pending_action → app.js` — **ไม่มี framework ไหนให้** ต้องสร้างใหม่บน runtime เขาอยู่ดี
- ของ generic ที่ยังขาด (memory ขั้นสูง / skills / subagent) อย่างละ ~ครึ่งวันบนฐาน SQLite + tool-loop เดิม — ย้ายไป framework ใช้เวลามากกว่า
- ผูกกับ Gemini + `google-genai` automatic function calling (รันฟังก์ชัน tool ให้เอง วนจนจบ) — ไม่ต้องเขียน agent loop เอง
- จัสมิน เป็น personal use คนเดียว ยังไม่โตถึงจุดที่ท่อ generic (multi-user, 20 แพลตฟอร์ม, pipeline หลาย agent) ครอบงำ

**ทบทวนใหม่เมื่อ:** ใช้เวลาส่วนใหญ่ re-implement ท่อ agent generic · หรือ roadmap โตพ้น "เลขาส่วนตัว" → multi-user / หลายสิบแพลตฟอร์ม / multi-agent pipeline หนัก

**ทางสายกลาง (ถ้าอยากได้ memory engine เขาจริงๆ):** เก็บ จัสมิน เป็น frontend (HUD + เสียง + บุคลิก + gateway) แล้วให้ Letta/Hermes Agent เป็น "สมอง" backend — `/api/chat` ยิงไป Letta server แทนรัน loop เอง · แลกกับมี service ต้องรันตลอด
