"""ความจำถาวรของ จัสมิน — ข้อเท็จจริงเกี่ยวกับผู้ใช้ (ชื่อคน, วันเกิด, ความชอบ, เป้าหมาย, กิจวัตร ฯลฯ)
เก็บลง SQLite (db.py) ข้ามเซสชัน/ข้าม restart. server.py แปะ memory_preamble() ไว้หน้าข้อความผู้ใช้ทุก
เทิร์นให้ Gemini เห็น fact เสมอ; recall()/forget() เป็น tool ให้ LLM เรียกเองเวลาต้องค้น/ลบเจาะจง
"""
from datetime import datetime

from . import db

_MAX_RECALL = 40


def remember(fact: str, tag: str = "") -> str:
    """จำข้อมูล/ข้อเท็จจริงเกี่ยวกับผู้ใช้ไว้ถาวร (ข้ามเซสชัน ข้าม restart) ใช้เมื่อผู้ใช้บอกว่า "จำไว้ว่า..."
    หรือเผยข้อมูลส่วนตัวที่ควรจำระยะยาว (ชื่อคนรอบตัว/วันเกิด/ความชอบ/ที่อยู่/เป้าหมาย/กิจวัตร ฯลฯ) —
    อย่าจำเรื่องชั่วคราวหรือบริบทของบทสนทนาเฉยๆ

    Args:
        fact: สิ่งที่จะจำ เขียนเป็นประโยคสั้นสมบูรณ์ในตัว (เช่น "แม่ชื่อสมศรี วันเกิด 3 มีนาคม")
        tag: หมวดสั้นๆ ไม่บังคับ (เช่น "คน" "ความชอบ" "งาน") ช่วยจัดกลุ่ม

    Returns:
        ข้อความยืนยันสั้นๆ
    """
    fact = (fact or "").strip()
    if not fact:
        return "ยังไม่มีอะไรให้จำเลยค่ะ บอกมาได้เลย"
    db.execute(
        "INSERT INTO memory (text, tag, created_at) VALUES (?, ?, ?)",
        (fact, (tag or "").strip(), datetime.now().isoformat(timespec="seconds")),
    )
    return f"จำไว้แล้วค่ะ: {fact}"


def recall(query: str = "") -> str:
    """ค้นสิ่งที่จัสมินจำไว้เกี่ยวกับผู้ใช้ ใช้เมื่อผู้ใช้ถาม "เคยบอกอะไรไว้เรื่อง..." / "จำได้ไหมว่า..." หรือ
    ต้องใช้ข้อมูลส่วนตัวมาตอบแต่ไม่มีในบทสนทนา (ถ้ามีอยู่ในบริบทแล้วไม่ต้องเรียก)

    Args:
        query: คำค้น (ปล่อยว่างเพื่อดูทั้งหมด)

    Returns:
        รายการสิ่งที่จำไว้ที่ตรง
    """
    query = (query or "").strip()
    if query:
        like = f"%{query}%"
        rows = db.query(
            "SELECT text, tag FROM memory WHERE text LIKE ? OR tag LIKE ? ORDER BY id DESC LIMIT ?",
            (like, like, _MAX_RECALL),
        )
    else:
        rows = db.query("SELECT text, tag FROM memory ORDER BY id DESC LIMIT ?", (_MAX_RECALL,))
    if not rows:
        return "ยังไม่ได้จำอะไรไว้เลยค่ะ" if not query else f'ไม่มีบันทึกที่เกี่ยวกับ "{query}" ค่ะ'
    return "\n".join(f"- {r['text']}" + (f" [{r['tag']}]" if r["tag"] else "") for r in rows)


def forget(query: str) -> str:
    """ลบสิ่งที่จำไว้ที่ตรงกับคำค้น ใช้เมื่อผู้ใช้บอกให้ "ลืม..." / "ลบที่จำเรื่อง..." — ถ้าคำค้นกว้างจน
    อาจลบเกินที่ตั้งใจ ให้ recall() มาโชว์ก่อนแล้วถามยืนยัน

    Args:
        query: คำค้นของบันทึกที่จะลบ

    Returns:
        ผลการลบ
    """
    query = (query or "").strip()
    if not query:
        return "บอกด้วยว่าจะให้ลืมเรื่องอะไรค่ะ"
    like = f"%{query}%"
    _id, n = db.execute("DELETE FROM memory WHERE text LIKE ? OR tag LIKE ?", (like, like))
    return f"ลบไป {n} รายการค่ะ" if n else f'ไม่เจอบันทึกที่ตรงกับ "{query}" ค่ะ'


def memory_preamble() -> str:
    """server.py แปะไว้หน้าข้อความผู้ใช้ทุกเทิร์น เพื่อให้ Gemini เห็น fact เสมอ (+ fact ใหม่มีผลทันที
    ในเซสชันเดียวกัน) — คืน "" ถ้ายังไม่มี fact"""
    rows = db.query("SELECT text FROM memory ORDER BY id")
    if not rows:
        return ""
    facts = "\n".join(f"- {r['text']}" for r in rows)
    return (
        "(ข้อมูลพื้นหลังที่จัสมินจำไว้เกี่ยวกับผู้ใช้ — ใช้ประกอบการตอบตามเหมาะสม "
        "ไม่ต้องพูดถึงตรงๆ เว้นแต่ผู้ใช้ถาม):\n" + facts + "\n\n"
    )
