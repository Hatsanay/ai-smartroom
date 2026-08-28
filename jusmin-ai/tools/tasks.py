"""to-do list ของ จัสมิน — งานที่ต้องทำ เก็บถาวรใน SQLite (db.py)
ต่างจาก reminders: task ไม่เด้งเตือนตามเวลา แค่อยู่ในลิสต์ให้ทบทวน (daily_briefing เอาไปสรุปด้วย)
"""
from datetime import date, datetime

from . import db

_PRIORITIES = {"low", "normal", "high"}


def _fmt(r) -> str:
    mark = "[เสร็จ]" if r["done"] else "[ ]"
    pri = "(ด่วน) " if r["priority"] == "high" else ""
    due = f" — ครบกำหนด {r['due_at'][:16].replace('T', ' ')}" if r["due_at"] else ""
    return f"{mark} #{r['id']} {pri}{r['text']}{due}"


def add_task(text: str, due: str = "", priority: str = "normal") -> str:
    """เพิ่มงานเข้า to-do list ของผู้ใช้ (เก็บถาวร ข้ามเซสชัน) ใช้เมื่อผู้ใช้บอกว่ามีงานต้องทำ/ต้องไม่ลืมทำ
    ถ้าผู้ใช้อยากให้เตือนตามเวลาจริงๆ ให้ใช้ add_reminder แทน

    Args:
        text: งานที่ต้องทำ
        due: กำหนดส่ง/วันครบกำหนด เป็น ISO 8601 (เช่น "2026-08-30" หรือ "2026-08-30T17:00") แปลงจาก
            คำพูดของผู้ใช้เอง — ปล่อยว่างถ้าไม่มีกำหนด
        priority: "low" / "normal" / "high" (ผู้ใช้บอกว่าด่วน/สำคัญ = high)

    Returns:
        ข้อความยืนยัน
    """
    text = (text or "").strip()
    if not text:
        return "ยังไม่มีงานให้เพิ่มค่ะ"
    priority = priority if priority in _PRIORITIES else "normal"
    tid, _n = db.execute(
        "INSERT INTO tasks (text, due_at, priority, created_at) VALUES (?, ?, ?, ?)",
        (text, (due or "").strip(), priority, datetime.now().isoformat(timespec="seconds")),
    )
    return f'เพิ่มงาน "#{tid} {text}" แล้วค่ะ'


def list_tasks(which: str = "open") -> str:
    """ดูรายการงาน ใช้เมื่อผู้ใช้ถาม "มีงานอะไรบ้าง" / "งานที่ยังไม่เสร็จ" / "งานวันนี้"

    Args:
        which: "open" (ยังไม่เสร็จ, ค่าเริ่มต้น) / "today" (ครบกำหนดวันนี้หรือเลยกำหนด) /
            "done" (เสร็จแล้ว) / "all" (ทั้งหมด)

    Returns:
        รายการงาน
    """
    which = (which or "open").strip().lower()
    if which == "done":
        rows = db.query("SELECT * FROM tasks WHERE done=1 ORDER BY done_at DESC LIMIT 30")
    elif which == "all":
        rows = db.query("SELECT * FROM tasks ORDER BY done, id")
    elif which == "today":
        rows = db.query(
            "SELECT * FROM tasks WHERE done=0 AND due_at!='' AND substr(due_at,1,10)<=? ORDER BY due_at",
            (date.today().isoformat(),),
        )
    else:
        rows = db.query("SELECT * FROM tasks WHERE done=0 ORDER BY (priority='high') DESC, id")
    if not rows:
        return "ไม่มีงานในรายการค่ะ"
    return "\n".join(_fmt(r) for r in rows)


def complete_task(query: str) -> str:
    """ทำเครื่องหมายว่างานเสร็จแล้ว ใช้เมื่อผู้ใช้บอกว่าทำงานเสร็จ

    Args:
        query: เลข id ของงาน (เช่น "3") หรือคำในชื่องาน

    Returns:
        ผลลัพธ์
    """
    query = (query or "").strip()
    if not query:
        return "บอกด้วยว่างานไหนเสร็จค่ะ"
    now = datetime.now().isoformat(timespec="seconds")
    key = query.lstrip("#")
    if key.isdigit():
        _i, n = db.execute("UPDATE tasks SET done=1, done_at=? WHERE id=? AND done=0", (now, int(key)))
        return "ทำเครื่องหมายว่าเสร็จแล้วค่ะ" if n else "ไม่พบงานนั้น หรือทำเสร็จไปแล้วค่ะ"
    rows = db.query("SELECT id, text FROM tasks WHERE done=0 AND text LIKE ?", (f"%{query}%",))
    if not rows:
        return f'ไม่เจองานที่ค้างอยู่ตรงกับ "{query}" ค่ะ'
    if len(rows) > 1:
        return "เจอหลายงานที่ตรงกัน บอก id มาได้ไหมคะ:\n" + "\n".join(f"#{r['id']} {r['text']}" for r in rows)
    db.execute("UPDATE tasks SET done=1, done_at=? WHERE id=?", (now, rows[0]["id"]))
    return f'ทำเครื่องหมายว่า "#{rows[0]["id"]} {rows[0]["text"]}" เสร็จแล้วค่ะ'
