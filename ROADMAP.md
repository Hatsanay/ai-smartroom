# จัสมิน — แผนพัฒนา (Roadmap)

> **ชื่อผู้ช่วยคือ "จัสมิน" เสมอ — ไม่เปลี่ยน** "Jarvis" ในเอกสารนี้เป็นแค่ **เกณฑ์เทียบความสามารถ**
> (AI สไตล์ Iron Man ที่บุคลิก จัสมิน อ้างอิงอยู่แล้ว) ไม่ใช่ชื่อใหม่ ห้าม rename
> **เป้าหมาย:** ยกความสามารถของ จัสมิน ให้ใกล้เคียงระดับ Jarvis มากที่สุด
> **ข้อกำหนด:** อยู่บน **สถาปัตยกรรมเดิม** — FastAPI + HUD (vanilla JS ES modules) + Gemini function calling + `tools/` package
> ไม่ย้ายไป agent framework สำเร็จรูป (เหตุผลท้ายเอกสาร)
> **รูปแบบสุดท้าย: ไม่ใช่แค่เว็บ** — ต้องมี **โปรแกรม desktop รันได้ทั้ง Windows และ Linux** (+ headless บน Pi, + Telegram) — ดูหัวข้อ "รูปแบบที่ส่งมอบ"

อัปเดตล่าสุด: 2026-08-28

---

## เฟสการทำงาน (ลำดับใหญ่)

**Phase 1 — ทำเว็บให้ครบทุกอย่างก่อน** ← ทำอยู่ตอนนี้
เว็บ HUD รันได้ทุก OS อยู่แล้ว (ผ่านเบราว์เซอร์ Chrome/Edge) — ยังใช้ Web Speech API สำหรับ wake word ต่อไปได้
สร้างฟีเจอร์ Jarvis ทั้งหมด (Tier 1 + Tier 2 ยกเว้น #6 + Tier 3) บนเว็บให้เสร็จ **ไม่ต้องแตะ STT / packaging**

**Phase 2 — โปรแกรม desktop (Windows + Linux)** ← หลัง Phase 1 เสร็จ
ย้าย STT มา server-side (Tier 2 #6: openWakeWord + faster-whisper) → แพ็กเกจ pywebview + PyInstaller → `.exe` / AppImage (Capstone)
Phase นี้เท่านั้นที่ต้องทำเรื่อง STT/webview/packaging — Phase 1 ไม่ต้องรอ

> STT-server-side, barge-in, headless-Pi, desktop packaging = **Phase 2 ทั้งหมด** ไม่ใช่ blocker ของงานฟีเจอร์ใน Phase 1

---

## สถานะปัจจุบัน (ทำแล้ว)

- ✅ **Group A (เลขา)** — `memory` / `tasks` / `reminders` / `email` / `daily_briefing` (ยังไม่ commit รอเทสเบราว์เซอร์)
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
| ความจำถาวรข้ามเซสชัน | ✅ | Group A |
| รู้เวลาปัจจุบัน / ตำแหน่ง | ✅ | `_now_preamble` / geolocation |
| จำเอง (สกัด fact จากบทสนทนาโดยไม่ต้องสั่ง) | ❌ | pass เบื้องหลังเรียก `remember()` |
| รู้ว่าในบ้านมีอุปกรณ์อะไร เปิด/ปิดอยู่ ใครอยู่บ้าน | ❌ | ผูกกับหมวด 6 |
| ปฏิทิน / ตารางนัด | ❌ | Google Calendar (กลุ่ม B เดิม) |
| ค้นความจำแบบ semantic | 🟡 | ตอนนี้ LIKE — พอ fact เยอะค่อยทำ FTS5/embedding |

### 4. ข้อมูล & การค้นคว้า
| ต้องมี | สถานะ |
|---|---|
| ค้นเว็บ / อากาศ / อีเมล | ✅ |
| อ่านบทความจาก URL (`read_url`) | ❌ (trafilatura ฟรี) |
| สรุปข่าว (RSS) | ❌ (กลุ่ม C เดิม) |
| คำนวณ / แปลงหน่วย / ค่าเงิน / หุ้น | ❌ |
| ข้อมูลเรียลไทม์: จราจร / รถเมล์ / BTS | ❌ (กลุ่ม B เดิม) |

### 5. งาน & การมอบหมาย
| ต้องมี | สถานะ |
|---|---|
| จดงาน + กำหนดส่ง + ความด่วน | ✅ |
| ตั้งเตือนตามเวลา (เด้ง + พูดเอง) | ✅ |
| บรีฟสรุปวัน | ✅ |
| นาฬิกาปลุก / จับเวลา / pomodoro | ❌ |
| subagent ทำงานเบื้องหลัง (ไม่กิน context หลัก) | ❌ |

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

### 8. การมองเห็น (perception)
| ต้องมี | สถานะ | หมายเหตุ |
|---|---|---|
| วิเคราะห์รูป / อ่านภาพหน้าจอ (`analyze_image`) | ❌ | Gemini เป็น multimodal อยู่แล้ว แค่ต่อ tool |
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
| สลับโมเดลได้ (ไม่ผูก Gemini) — LiteLLM | ❌ | กันโควตาหมดแล้วใช้ไม่ได้เลย |
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

### Tier 1 — แกน Jarvis · เข้ากับโครงเดิม · ทำก่อน
1. **`control_home()` + Home Assistant + safety whitelist** — คุมไฟ/แอร์/ทีวีจริง (หัวใจ Jarvis + ชื่อโปรเจกต์)
2. **รัน 24/7 บน Pi เป็น service** — auto-start ตอนบูต ไม่ต้องเปิดแท็บ
3. **Telegram bot** — สั่ง จัสมิน จากมือถือทุกที่ (แยก logic "รับข้อความ → ตอบ + action" ออกจาก `chat_endpoint` เป็นฟังก์ชันกลางก่อน)
4. **บรีฟ + แจ้งเตือนเชิงรุกอัตโนมัติ** — 7 โมงทักเอง, "ฝนจะตกแล้ว เก็บผ้าไหม" (ต่อยอด `notify` + scheduler ที่มี)
5. **`read_url` + `analyze_image`** — อ่านลิงก์, ดูรูป (เร็ว คุ้ม)

### Tier 2 — เพิ่มความลื่น/ฉลาด
6. **[Phase 2 เท่านั้น] ย้าย STT มา server-side: openWakeWord (wake) + faster-whisper `small` (command) + WebSocket `/ws/audio`** → ปลดล็อก barge-in + streaming + เป็น prerequisite ของ desktop app + headless Pi + Telegram voice · **Phase 1 ข้ามข้อนี้ ใช้ Web Speech API ต่อไป** (รายละเอียดในหัวข้อ "รูปแบบที่ส่งมอบ")
7. Auto-memory (จำเองไม่ต้องสั่ง "จำไว้ว่า")
8. subagent เบื้องหลัง + นาฬิกาปลุก/จับเวลา/pomodoro
9. ปฏิทิน (Google Calendar) + ข่าว (RSS) + คำนวณ/แปลงหน่วย/ค่าเงิน
10. **LiteLLM** — สลับโมเดล Gemini ↔ OpenRouter ↔ Nous Portal ↔ Ollama ผ่าน `.env` (ต้องเขียน tool loop เอง เพราะจะเสีย automatic function calling ของ `google-genai`)

### Tier 3 — ล้ำ แต่หนัก/เสี่ยง
11. กล้องดูห้อง / อ่านหน้าจอ / จำเสียงคนพูด (speaker ID)
12. ฉาก-รูทีนบ้าน, data-analysis sandbox (รัน Python คำนวณ)

### ไม่แนะนำ
- ให้ LLM เขียนโค้ดแล้วรันเอง (arbitrary code execution บนเครื่องผู้ใช้)
- browser automation เต็มรูปแบบ (Playwright — หนักเกินคุ้ม)
- subagent มี shell/terminal จริง (เสี่ยง)
- Electron เป็น shell หลัก (ใหญ่ 150MB) — ใช้ pywebview/Tauri หลังย้าย STT แล้วแทน

### Capstone — โปรแกรม desktop (Windows + Linux)
ทำ**หลัง Tier 2 #6** (STT server-side) แล้ว — แพ็กเกจ pywebview + PyInstaller → `.exe` / AppImage + system tray + auto-start · รายละเอียดในหัวข้อ "รูปแบบที่ส่งมอบ"

---

## หมายเหตุ

- **browser-side action** เดิม (เครื่องเล่น YouTube, การ์ดอากาศ, เต็มจอ) ใช้ได้เฉพาะบนหน้าเว็บ HUD — บน Telegram/Discord ใช้ได้แค่ tool ที่เป็นข้อความ (memory, tasks, reminders, email, ค้นเว็บ, control_home)
- **`_pending_action` เป็น slot เดียว** — ทำ 2 browser action ในเทิร์นเดียวไม่ได้ ถ้า Tier 2+ ต้องการ (เช่น timer ที่มี countdown บนจอ) อาจต้องเปลี่ยนเป็น list หรือใช้ channel `notify`

---

## ทำไมอยู่บนโครงเดิม (ไม่ย้าย framework)

พิจารณาแล้ว: **LiteLLM** (lib model-agnostic), **Letta/MemGPT** (memory engine), **Agno**, **Pydantic AI**, **CrewAI**, **Claude Agent SDK**, **Hermes Agent by Nous Research**

- "เปลือก จัสมิน" ที่สร้างเอง = HUD Jarvis + wake word ไทย + TTS ไทย + audio choreography + บุคลิก + bridge `pending_action → app.js` — **ไม่มี framework ไหนให้** ต้องสร้างใหม่บน runtime เขาอยู่ดี
- ของ generic ที่ยังขาด (memory ขั้นสูง / skills / subagent / model-agnostic) อย่างละ ~ครึ่งวันบนฐาน SQLite + tool-loop เดิม — ย้ายไป framework ใช้เวลามากกว่า
- จัสมิน เป็น personal use คนเดียว ยังไม่โตถึงจุดที่ท่อ generic (multi-user, 20 แพลตฟอร์ม, pipeline หลาย agent) ครอบงำ

**ทบทวนใหม่เมื่อ:** ใช้เวลาส่วนใหญ่ re-implement ท่อ agent generic · หรือ roadmap โตพ้น "เลขาส่วนตัว" → multi-user / หลายสิบแพลตฟอร์ม / multi-agent pipeline หนัก

**ทางสายกลาง (ถ้าอยากได้ memory engine เขาจริงๆ):** เก็บ จัสมิน เป็น frontend (HUD + เสียง + บุคลิก + gateway) แล้วให้ Letta/Hermes Agent เป็น "สมอง" backend — `/api/chat` ยิงไป Letta server แทนรัน loop เอง · แลกกับมี service ต้องรันตลอด
