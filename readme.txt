Jusmin — AI Assistant Project
==============================

โปรเจกต์ AI ผู้ช่วยส่วนตัวสไตล์ Jarvis ชื่อ Jusmin คุยตอบคำถามได้ ค้นเว็บได้ เปิด/คุมเพลง YouTube
ได้ เช็คสภาพอากาศได้ พร้อมหน้าเว็บ HUD ที่ฟัง/พูดเป็นภาษาไทยได้จริง (wake word "จัสมิน")

โปรเจกต์หลักอยู่ในโฟลเดอร์ jusmin-ai/ ทุกคำสั่งด้านล่างให้รันจากในโฟลเดอร์นั้น


เริ่มเร็ว (Windows) — แค่ 2 ไฟล์ .bat ที่ repo root
--------------------------------------------------
1. ดับเบิลคลิก  setup.bat   (รันครั้งเดียวหลังโคลน — ติดตั้ง Python ถ้ายังไม่มี + สร้าง venv +
   ลง dependency + ทำไฟล์ .env ให้ใส่ Gemini API key)
2. ดับเบิลคลิก  dev.bat     (รันเว็บ — ปิด server เดิม, เปิด venv, รัน server.py, เปิดเบราว์เซอร์ให้เอง)

ถ้าอยากทำเองทีละขั้น (หรือใช้ macOS/Linux) ดูวิธีด้านล่าง


ต้องมีก่อนเริ่ม
----------------
- Python 3.10 ขึ้นไป
- Gemini API key (ฟรี) — ขอได้ที่ Google AI Studio (ai.dev หรือ aistudio.google.com)


วิธีติดตั้งหลังโคลนโปรเจกต์
-----------------------------
1. เข้าไปที่โฟลเดอร์โปรเจกต์
     cd jusmin-ai

2. สร้าง virtual environment
     python -m venv venv

3. เปิดใช้งาน venv
     Windows (cmd/PowerShell) :  venv\Scripts\activate
     macOS / Linux             :  source venv/bin/activate

4. ติดตั้ง dependency ทั้งหมด
     pip install -r requirements.txt

5. ทำไฟล์ .env จากไฟล์ตัวอย่าง (อยู่ในโฟลเดอร์ jusmin-ai/ โฟลเดอร์เดียวกับ server.py)
     Windows      :  copy .env.example .env
     macOS/Linux  :  cp .env.example .env

   แล้วเปิด .env ใส่ Gemini API key ของตัวเองในบรรทัด GEMINI_API_KEY=
   (ไฟล์ .env จริงไม่ได้อยู่ใน repo — อยู่ใน .gitignore เพราะมี key จริง ส่วน .env.example อยู่ใน repo
    เป็นแค่แม่แบบ ไม่มีค่า secret) ถ้าไม่ทำ .env โปรแกรมจะ error ทันทีตอนเริ่มรัน

   อีเมล (ไม่บังคับ) — ถ้าอยากให้ Jusmin เช็ค/อ่าน/ส่งเมล Gmail ได้ ใส่ค่าในบรรทัด EMAIL_ADDRESS=
   กับ EMAIL_APP_PASSWORD= ที่มีอยู่แล้วใน .env (คำอธิบายแต่ละ key อยู่ในคอมเมนต์ของ .env.example)
   EMAIL_APP_PASSWORD คือ App Password 16 หลักจาก myaccount.google.com/apppasswords (ต้องเปิด
   2-Step Verification ก่อน — ไม่ใช่รหัสผ่าน Gmail ปกติ) ไม่ใส่ก็ได้ ฟีเจอร์อื่นทำงานปกติ
   ตั้ง EMAIL_SENDER_NAME= เป็นชื่อคุณได้ด้วย จะไปโผล่ในลายเซ็นท้ายเมลทุกฉบับที่ Jusmin ส่ง


วิธีรัน
--------
แบบเว็บ (แนะนำ — มีหน้าจอ HUD, พิมพ์หรือพูดคุยได้ พูดตอบเป็นเสียงจริง):
     python server.py
   แล้วเปิดเบราว์เซอร์ (แนะนำ Chrome หรือ Edge เพราะต้องใช้ Web Speech API) ไปที่
     http://127.0.0.1:8000/

แบบ CLI (คุยผ่าน terminal เฉยๆ พิมพ์อย่างเดียว ไม่มีเสียง เหมาะเทสเร็วๆ):
     python jusmin.py
   พิมพ์ 'exit' หรือ 'quit' เพื่อออก


หมายเหตุ
---------
- รันครั้งแรกจะช้ากว่าปกตินิดหน่อย เพราะต้องดาวน์โหลดโมเดลเสียง TTS มาแคชไว้ที่โฟลเดอร์ voices/
  (ดาวน์โหลดแค่ครั้งแรกครั้งเดียว รอบต่อไปเร็วปกติ)
- แก้โค้ด (server.py, tools.py, tts.py ฯลฯ) แล้วต้อง restart server เอง (กด Ctrl+C แล้วรัน
  python server.py ใหม่) ไม่มี auto-reload
- หน้าเว็บจะเปิดโหมด "ฟังตลอด" (wake word พูดคำว่า "จัสมิน") เป็นค่าเริ่มต้นทันที เบราว์เซอร์จะขอ
  สิทธิ์ไมโครโฟนเอง
- Jusmin จำเรื่องผู้ใช้ / งาน / การเตือน ไว้ในไฟล์ jusmin-ai/jusmin.db (SQLite, สร้างเองอัตโนมัติ,
  อยู่ใน .gitignore) จำได้ข้าม restart — ลบไฟล์นี้ทิ้งคือล้างความจำทั้งหมด
- การเตือน (reminder) จะเด้ง + พูดเฉพาะตอนเปิดหน้าเว็บค้างไว้เท่านั้น (ไม่มี Windows notification)
  ปิดแท็บแล้วพอเปิดใหม่ การเตือนที่เลยเวลาไปแล้วจะเด้งย้อนให้ทันที
- รายละเอียดสถาปัตยกรรม เหตุผลการออกแบบ และ decision ต่างๆ ทั้งหมดอยู่ใน jusmin-ai/CLAUDE.md
