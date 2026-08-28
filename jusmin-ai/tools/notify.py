"""notification queue — เรื่องที่ถึงเวลาเด้ง (ตอนนี้มีแค่ reminder). scheduler thread ใน server.py
เรียก reminders.check_due() แล้ว push() เข้าคิว; GET /api/notifications drain(); static/js/notify.js
poll ทุก 10 วิ เอาไปแจ้ง + ให้ จัสมิน พูด — เด้งเฉพาะตอนเปิดหน้าเว็บค้างไว้ (ผู้ใช้เลือกเอง ไม่ทำ OS toast)

thread-safe: scheduler thread เขียน, FastAPI threadpool อ่าน -> ล็อกไว้
"""
import threading
from datetime import datetime

_lock = threading.Lock()
_queue: list[dict] = []


def push(text: str, kind: str = "reminder") -> None:
    with _lock:
        _queue.append({"text": text, "kind": kind, "at": datetime.now().isoformat(timespec="seconds")})


def drain() -> list[dict]:
    with _lock:
        items = _queue[:]
        _queue.clear()
        return items
