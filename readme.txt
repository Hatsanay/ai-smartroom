FRIDAY — AI Assistant Project
==============================

โปรเจกต์ AI ผู้ช่วยส่วนตัวสไตล์ Jarvis ชื่อ FRIDAY คุยตอบคำถามได้ ค้นเว็บได้ เปิด/คุมเพลง YouTube
ได้ เช็คสภาพอากาศได้ พร้อมหน้าเว็บ HUD ที่ฟัง/พูดเป็นภาษาไทยได้จริง (wake word "Friday")

โปรเจกต์หลักอยู่ในโฟลเดอร์ friday-ai/ ทุกคำสั่งด้านล่างให้รันจากในโฟลเดอร์นั้น


ต้องมีก่อนเริ่ม
----------------
- Python 3.10 ขึ้นไป
- Gemini API key (ฟรี) — ขอได้ที่ Google AI Studio (ai.dev หรือ aistudio.google.com)


วิธีติดตั้งหลังโคลนโปรเจกต์
-----------------------------
1. เข้าไปที่โฟลเดอร์โปรเจกต์
     cd friday-ai

2. สร้าง virtual environment
     python -m venv venv

3. เปิดใช้งาน venv
     Windows (cmd/PowerShell) :  venv\Scripts\activate
     macOS / Linux             :  source venv/bin/activate

4. ติดตั้ง dependency ทั้งหมด
     pip install -r requirements.txt

5. สร้างไฟล์ .env ในโฟลเดอร์ friday-ai/ (โฟลเดอร์เดียวกับ server.py) ใส่ Gemini API key ของตัวเอง
     GEMINI_API_KEY=ใส่คีย์ของคุณตรงนี้

   ไฟล์นี้ต้องสร้างเองเสมอ — ไม่ได้อยู่ใน repo (อยู่ใน .gitignore ไว้เพราะมี key จริง) ถ้าไม่สร้าง
   โปรแกรมจะ error ทันทีตอนเริ่มรัน


วิธีรัน
--------
แบบเว็บ (แนะนำ — มีหน้าจอ HUD, พิมพ์หรือพูดคุยได้ พูดตอบเป็นเสียงจริง):
     python server.py
   แล้วเปิดเบราว์เซอร์ (แนะนำ Chrome หรือ Edge เพราะต้องใช้ Web Speech API) ไปที่
     http://127.0.0.1:8000/

แบบ CLI (คุยผ่าน terminal เฉยๆ พิมพ์อย่างเดียว ไม่มีเสียง เหมาะเทสเร็วๆ):
     python friday.py
   พิมพ์ 'exit' หรือ 'quit' เพื่อออก


หมายเหตุ
---------
- รันครั้งแรกจะช้ากว่าปกตินิดหน่อย เพราะต้องดาวน์โหลดโมเดลเสียง TTS มาแคชไว้ที่โฟลเดอร์ voices/
  (ดาวน์โหลดแค่ครั้งแรกครั้งเดียว รอบต่อไปเร็วปกติ)
- แก้โค้ด (server.py, tools.py, tts.py ฯลฯ) แล้วต้อง restart server เอง (กด Ctrl+C แล้วรัน
  python server.py ใหม่) ไม่มี auto-reload
- หน้าเว็บจะเปิดโหมด "ฟังตลอด" (wake word พูดคำว่า "Friday") เป็นค่าเริ่มต้นทันที เบราว์เซอร์จะขอ
  สิทธิ์ไมโครโฟนเอง
- รายละเอียดสถาปัตยกรรม เหตุผลการออกแบบ และ decision ต่างๆ ทั้งหมดอยู่ใน friday-ai/CLAUDE.md
