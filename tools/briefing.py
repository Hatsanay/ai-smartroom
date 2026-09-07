"""สรุปภาพรวมของวัน — รวมข้อมูลจาก tasks + reminders + mail (unread count) เป็นก้อนเดียว
ให้ LLM เอาไปเรียบเรียง + เรียก get_weather() เพิ่มแล้วพูดสรุปสั้นๆ
"""
from datetime import datetime

from . import db, mail

_THAI_WD = ("จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์")
_THAI_MONTH = (
    "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
)


def daily_briefing() -> str:
    """สรุปภาพรวมของวันให้ผู้ใช้ ใช้เมื่อผู้ใช้ถาม "วันนี้มีอะไรบ้าง" / "สรุปวันนี้ให้หน่อย" / ทักตอนเช้า
    รวม วันที่ + งานที่ต้องทำวันนี้-เลยกำหนด + งานด่วนที่ค้าง + การเตือนที่เหลือวันนี้ + จำนวนเมลใหม่

    **หลังได้ผลจาก tool นี้ ให้เรียก get_weather() เพิ่มด้วย แล้วเรียบเรียงทุกอย่างรวมกันเป็นบทสรุป
    พูดสั้นๆ เป็นกันเอง** (อย่าอ่านเป็นลิสต์แข็งๆ)

    Returns:
        ข้อมูลดิบของวันนี้ เอาไปเรียบเรียงต่อ
    """
    now = datetime.now()
    today = now.date().isoformat()
    date_str = f"วัน{_THAI_WD[now.weekday()]}ที่ {now.day} {_THAI_MONTH[now.month - 1]} {now.year}"
    parts = [f"วันนี้: {date_str} เวลา {now.strftime('%H:%M')} น."]

    due = db.query(
        "SELECT text, due_at FROM tasks WHERE done=0 AND due_at!='' AND substr(due_at,1,10)<=? ORDER BY due_at",
        (today,),
    )
    hi = db.query(
        "SELECT text FROM tasks WHERE done=0 AND priority='high' AND (due_at='' OR substr(due_at,1,10)>?)",
        (today,),
    )
    if due:
        lines = []
        for r in due:
            when = ""
            if r["due_at"][:10] < today:
                when = " (เลยกำหนดแล้ว)"
            elif len(r["due_at"]) > 10:
                when = f" ({r['due_at'][11:16]} น.)"
            lines.append(f"- {r['text']}{when}")
        parts.append("งานที่ต้องทำวันนี้/เลยกำหนด:\n" + "\n".join(lines))
    if hi:
        parts.append("งานด่วนที่ค้างอยู่:\n" + "\n".join(f"- {r['text']}" for r in hi))
    if not due and not hi:
        parts.append("ไม่มีงานเร่งด่วนวันนี้")

    rem = db.query(
        "SELECT text, remind_at FROM reminders WHERE fired=0 AND substr(remind_at,1,10)=? ORDER BY remind_at",
        (today,),
    )
    if rem:
        parts.append(
            "การเตือนวันนี้:\n" + "\n".join(f"- {r['remind_at'][11:16]} น. {r['text']}" for r in rem)
        )

    uc = mail.unread_count()
    if uc is not None:
        parts.append(f"เมลใหม่: {uc} ฉบับ" if uc else "เมลใหม่: ไม่มี")

    return "\n\n".join(parts)
