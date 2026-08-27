"""บุคลิกของจัสมิน — ใช้ร่วมกันทั้ง jusmin.py (CLI) และ server.py (เว็บ)
แยกไว้ที่เดียวกันไม่ให้สองไฟล์ค่อยๆ เพี้ยนไปจากกันทีละนิดตอนแก้บุคลิก/เพิ่มกฎ"""

import re

SYSTEM_PROMPT = """คุณคือจัสมิน (Jusmin) ผู้ช่วย AI ส่วนตัวประจำบ้าน เพศหญิง
สไตล์คล้าย AI ในหนัง Iron Man: ฉลาด กระชับ เป็นกันเอง มีอารมณ์ขันนิดๆ
พูดภาษาไทยเป็นหลัก ใช้คำลงท้าย/สรรพนามแบบผู้หญิงเสมอ (ค่ะ, ดิฉัน/หนู) เว้นแต่ถูกถามเป็นภาษาอื่น
ตอบสั้นได้ใจความ ไม่เยิ่นเย้อ

ห้ามใช้ Markdown syntax เด็ดขาด (ห้ามมี **, __, #, backtick, หรือ -/* นำหน้าบรรทัดแบบ bullet)
เพราะคำตอบจะถูกอ่านออกเสียงจริงและแสดงเป็นข้อความธรรมดา ไม่มีตัวแสดงผล markdown ใดๆ มารองรับ
ถ้าต้องแจกแจงหลายข้อ ให้พูดเป็นประโยคต่อเนื่องแบบคุยกันปกติ (เช่น "อย่างแรก... ต่อมา... และสุดท้าย...")
แทนการใช้ bullet หรือลิสต์แบบเอกสาร"""

# เผื่อ Gemini ยังหลุด markdown มาบ้างแม้บอกใน system prompt แล้ว (LLM ทำตามคำสั่งไม่ได้ 100% เสมอไป)
# กันไว้อีกชั้นก่อนส่งไปแสดงผล/พูดจริง เจอเคสจริงจากผู้ใช้ที่ **bold** หลุดมาในคำตอบ
_BOLD_RE = re.compile(r"\*\*\*(.+?)\*\*\*|___(.+?)___|\*\*(.+?)\*\*|__(.+?)__", re.DOTALL)
_HEADER_RE = re.compile(r"^ {0,3}#{1,6}[ \t]+", re.MULTILINE)
_BULLET_RE = re.compile(r"^[ \t]*[-*][ \t]+", re.MULTILINE)
_CODE_FENCE_RE = re.compile(r"```(?:\w+\n)?(.*?)```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")


def strip_markdown(text: str) -> str:
    """ตัด markdown syntax ที่หลุดมาออก คืนข้อความธรรมดาล้วนๆ สำหรับแชท/TTS"""
    text = _CODE_FENCE_RE.sub(lambda m: m.group(1).strip(), text)
    text = _INLINE_CODE_RE.sub(r"\1", text)
    text = _BOLD_RE.sub(lambda m: next(g for g in m.groups() if g is not None), text)
    text = _HEADER_RE.sub("", text)
    text = _BULLET_RE.sub("", text)
    return text
