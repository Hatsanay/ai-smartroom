"""ดู/วิเคราะห์รูปภาพด้วย Gemini (multimodal) — จำกัดไฟล์ในโฟลเดอร์ที่ผู้ใช้อนุญาตเท่านั้น (ใช้ security
ตัวเดียวกับ tools/files.py คือ _resolve_safe_path + audit log)

analyze_image ยิง Gemini call ของตัวเอง (แยกจาก chat session หลัก) เพราะ tool function รันซ้อนอยู่ใน
automatic function calling ของ chat อยู่แล้ว จะแทรกรูปเข้าไปใน chat โดยตรงไม่ได้ — ตั้ง client ของ
ตัวเองแบบ lazy (อ่าน key ตอนเรียก เหมือน mail.py) กัน circular import (server.py import tools)

หมายเหตุ: Gemini call ตัวนี้ไม่ถูกนับใน quota_state ของ server.py (นับแค่ chat.send_message) — ยอมรับ drift
"""
import mimetypes
import os

from google import genai
from google.genai import types

from . import files

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
_CONVERTIBLE_EXTS = {".gif", ".bmp", ".tiff", ".tif"}  # แปลงเป็น PNG ก่อนถ้ามี Pillow
_MAX_IMAGE_BYTES = 12 * 1024 * 1024  # เผื่อ margin จาก limit inline ~20MB ของ Gemini
_MAX_EDGE_PX = 1024  # ย่อด้านยาวสุดลงเหลือเท่านี้ก่อนส่ง (ถ้ามี Pillow) — ประหยัด token/quota

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


def _prep_bytes(target: str, ext: str) -> tuple[bytes | None, str, str]:
    """คืน (bytes, mime_type, error) — พยายามย่อ/แปลงด้วย Pillow ถ้ามี ไม่มีก็ส่งดิบ"""
    try:
        raw = open(target, "rb").read()
    except OSError:
        return None, "", "อ่านไฟล์รูปไม่สำเร็จค่ะ"

    try:
        from PIL import Image  # optional
    except ImportError:
        if ext in _CONVERTIBLE_EXTS:
            return None, "", f"ไฟล์ {ext} นี้ต้องมี Pillow ถึงจะอ่านได้ค่ะ (ลองแปลงเป็น .png ก่อน)"
        if len(raw) > _MAX_IMAGE_BYTES:
            return None, "", "ไฟล์รูปใหญ่เกินไปค่ะ (เกิน 12MB) ลองย่อขนาดก่อนนะคะ"
        return raw, mimetypes.guess_type(target)[0] or "image/jpeg", ""

    import io

    try:
        im = Image.open(io.BytesIO(raw))
        im.load()
    except Exception:
        return None, "", "เปิดไฟล์รูปนี้ไม่ได้ค่ะ (ไฟล์อาจเสียหรือไม่ใช่รูปจริง)"

    if max(im.size) > _MAX_EDGE_PX:
        im.thumbnail((_MAX_EDGE_PX, _MAX_EDGE_PX))
    if im.mode not in ("RGB", "RGBA", "L"):
        im = im.convert("RGB")
    out = io.BytesIO()
    fmt = "PNG" if (ext in _CONVERTIBLE_EXTS or im.mode == "RGBA" or ext == ".png") else "JPEG"
    if fmt == "JPEG" and im.mode == "RGBA":
        im = im.convert("RGB")
    im.save(out, format=fmt, quality=88)
    data = out.getvalue()
    if len(data) > _MAX_IMAGE_BYTES:
        return None, "", "ไฟล์รูปใหญ่เกินไปค่ะ แม้ย่อแล้ว"
    return data, ("image/png" if fmt == "PNG" else "image/jpeg"), ""


def analyze_image(path: str, question: str = "") -> str:
    """ดู/วิเคราะห์ไฟล์รูปภาพในโฟลเดอร์ที่ผู้ใช้อนุญาต ใช้เมื่อผู้ใช้ขอให้ดูรูป บอกว่าในรูปมีอะไร
    อ่านข้อความในรูป (OCR) เทียบรูป อธิบายภาพหน้าจอ ฯลฯ

    Args:
        path: path ของไฟล์รูป นับจากโฟลเดอร์ที่อนุญาต (เช่น "screenshot.png", "รูป/ใบเสร็จ.jpg")
        question: สิ่งที่อยากรู้จากรูป (เว้นว่าง = ให้บรรยายภาพทั่วไป)

    Returns:
        คำอธิบาย/คำตอบจากการดูรูป หรือข้อความบอกว่าดูไม่ได้
    """
    if not files.get_allowed_folder():
        return "ยังไม่ได้ตั้งค่าโฟลเดอร์ที่อนุญาตให้เข้าถึงเลยค่ะ กดปุ่ม 📁 เลือกโฟลเดอร์ มุมขวาบนของหน้าเว็บก่อนนะคะ"

    path = (path or "").strip()
    ok, target = files._resolve_safe_path(path)
    if not ok:
        files._log_activity("analyze_image", path, False, "outside allowed scope")
        return "ไม่สามารถเข้าถึงไฟล์นี้ได้ค่ะ อยู่นอกขอบเขตที่อนุญาตไว้"
    if not os.path.isfile(target):
        return f'ไม่พบไฟล์ "{path}" ค่ะ'

    ext = os.path.splitext(target)[1].lower()
    if ext not in _IMAGE_EXTS and ext not in _CONVERTIBLE_EXTS:
        files._log_activity("analyze_image", path, False, f"not an image ext {ext}")
        return f"ไฟล์นามสกุล {ext or '(ไม่มีนามสกุล)'} นี้ไม่ใช่รูปภาพที่ดูได้ค่ะ (รองรับ .png .jpg .jpeg .webp)"

    data, mime, err = _prep_bytes(target, ext)
    if err:
        files._log_activity("analyze_image", path, False, err)
        return err

    prompt = question.strip() or "บรรยายว่าในรูปนี้มีอะไรบ้าง"
    try:
        resp = _get_client().models.generate_content(
            model=os.environ.get("VISION_MODEL", "gemini-3.5-flash-lite"),
            contents=[types.Part.from_bytes(data=data, mime_type=mime), prompt],
            config=types.GenerateContentConfig(
                # ตอบกลับเป็น tool result ที่ จัสมิน เอาไปเรียบเรียงต่อ — ให้สั้น เป็นข้อความล้วน
                system_instruction=(
                    "ตอบเป็นภาษาไทย สั้นกระชับ ใช้คำลงท้ายแบบผู้หญิง (ค่ะ) "
                    "เป็นข้อความธรรมดา ห้ามใช้ markdown (**, #, - นำหน้าบรรทัด)"
                ),
                # ปิด AFC — ไม่มี tool ให้เรียกอยู่แล้ว + กัน warning รก log ทุกครั้งที่เรียก
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            ),
        )
        text = (resp.text or "").strip()
    except Exception as e:
        files._log_activity("analyze_image", path, False, f"{type(e).__name__}")
        return f"ดูรูปไม่สำเร็จค่ะ ({type(e).__name__}) — ลองใหม่อีกทีนะคะ"

    files._log_activity("analyze_image", path, True)
    return text or "ดูรูปแล้วแต่ยังสรุปเป็นข้อความไม่ได้ค่ะ"
