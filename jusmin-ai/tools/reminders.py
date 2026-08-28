"""เตือนตามเวลา — เก็บใน SQLite (db.py). ตอนสร้างแค่คืน string; ตอน "เด้ง" scheduler thread ใน
server.py เรียก check_due() ทุก ~20 วิ -> push เข้า notify queue -> client poll เอาไปแจ้ง + ให้ จัสมิน พูด
(ทำงานเฉพาะตอนเปิดหน้าเว็บค้างไว้)
"""
from datetime import datetime

from . import db, notify


def _parse(when_iso: str):
    """คืน datetime หรือ None ถ้า parse ไม่ได้ — Python 3.11+ fromisoformat lenient อยู่แล้ว
    (รับทั้ง 'T'/ช่องว่าง, มี/ไม่มีวินาที) แต่กัน format แปลกๆ ไว้อีกชั้น"""
    s = (when_iso or "").strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        try:
            return datetime.fromisoformat(s.replace(" ", "T"))
        except ValueError:
            return None


def add_reminder(text: str, when_iso: str) -> str:
    """ตั้งเตือนให้ผู้ใช้ตามเวลา ใช้เมื่อผู้ใช้บอก "เตือนฉัน... ตอน..." / "อีก X นาทีเตือนด้วย" — พอถึงเวลา
    จัสมิน จะแจ้งเตือนในแชท + พูดออกมา (ทำงานเฉพาะตอนเปิดหน้าเว็บค้างไว้)

    Args:
        text: ข้อความที่จะเตือน สั้นๆ (เช่น "โทรหาหมอ", "ประชุมทีม")
        when_iso: เวลาที่จะเตือน เป็น ISO 8601 ตามเวลาท้องถิ่น (เช่น "2026-08-29T09:00:00") —
            **แปลงจากคำพูดของผู้ใช้เป็นเวลาจริงเอง โดยคิดจากเวลาปัจจุบัน** เช่น "อีก 10 นาที" /
            "พรุ่งนี้ 9 โมงเช้า" / "บ่าย 3 วันศุกร์". ถ้าเวลาไม่ชัดเจนให้ถามผู้ใช้ก่อน

    Returns:
        ข้อความยืนยัน (พร้อมเวลาที่จะเตือน)
    """
    text = (text or "").strip()
    if not text:
        return "จะให้เตือนเรื่องอะไรคะ"
    dt = _parse(when_iso)
    if dt is None:
        return f'ระบุเวลาไม่ถูกต้องค่ะ ("{when_iso}") บอกเวลาที่ชัดเจนอีกทีได้ไหมคะ'
    if dt <= datetime.now():
        return "เวลานั้นผ่านไปแล้วค่ะ บอกเวลาในอนาคตนะคะ"
    rid, _n = db.execute(
        "INSERT INTO reminders (text, remind_at, created_at) VALUES (?, ?, ?)",
        (text, dt.isoformat(timespec="seconds"), datetime.now().isoformat(timespec="seconds")),
    )
    return f'ตั้งเตือน "#{rid} {text}" ไว้ {dt.strftime("%d/%m %H:%M")} น. แล้วค่ะ'


def list_reminders() -> str:
    """ดูรายการเตือนที่ตั้งไว้และยังไม่ถึงเวลา ใช้เมื่อผู้ใช้ถาม "มีเตือนอะไรไว้บ้าง" """
    rows = db.query("SELECT * FROM reminders WHERE fired=0 ORDER BY remind_at")
    if not rows:
        return "ไม่มีการเตือนที่ตั้งค้างไว้ค่ะ"
    return "\n".join(
        f"#{r['id']} {r['text']} — {datetime.fromisoformat(r['remind_at']).strftime('%d/%m %H:%M')} น."
        for r in rows
    )


def cancel_reminder(query: str) -> str:
    """ยกเลิกการเตือนที่ตั้งไว้ ใช้เมื่อผู้ใช้บอก "ยกเลิกเตือน..." / "ไม่ต้องเตือนเรื่อง..."

    Args:
        query: เลข id (เช่น "3") หรือคำในข้อความเตือน

    Returns:
        ผลลัพธ์
    """
    query = (query or "").strip()
    if not query:
        return "จะยกเลิกการเตือนอันไหนคะ"
    key = query.lstrip("#")
    if key.isdigit():
        _i, n = db.execute("DELETE FROM reminders WHERE id=? AND fired=0", (int(key),))
        return "ยกเลิกแล้วค่ะ" if n else "ไม่พบการเตือนนั้นค่ะ"
    rows = db.query("SELECT id, text FROM reminders WHERE fired=0 AND text LIKE ?", (f"%{query}%",))
    if not rows:
        return f'ไม่เจอการเตือนที่ตรงกับ "{query}" ค่ะ'
    if len(rows) > 1:
        return "เจอหลายอัน บอก id มาได้ไหมคะ:\n" + "\n".join(f"#{r['id']} {r['text']}" for r in rows)
    db.execute("DELETE FROM reminders WHERE id=?", (rows[0]["id"],))
    return f'ยกเลิกการเตือน "{rows[0]["text"]}" แล้วค่ะ'


def check_due() -> None:
    """scheduler thread เรียกทุก ~20 วิ — หา reminder ที่ถึงเวลาแล้วยังไม่เด้ง mark fired + push เข้า notify queue"""
    now = datetime.now().isoformat(timespec="seconds")
    rows = db.query("SELECT id, text FROM reminders WHERE fired=0 AND remind_at<=?", (now,))
    for r in rows:
        db.execute("UPDATE reminders SET fired=1 WHERE id=?", (r["id"],))
        notify.push(r["text"], "reminder")
