# Plan 01 — `read_url` + `analyze_image`

> Phase 1 · Tier 1 ข้อ 1 · ตาม [ROADMAP.md](../../ROADMAP.md)
> สถานะ: ยังไม่เริ่ม (รอผู้ใช้สั่ง → แยก branch → ลงมือ)

**สรุป:** เพิ่ม 2 tool
- `read_url` — อ่าน/สรุปหน้าเว็บจากลิงก์
- `analyze_image` — ดู/วิเคราะห์รูปในโฟลเดอร์ที่ผู้ใช้อนุญาต

~ครึ่งวัน · ไม่แตะ JS สำหรับ MVP (HUD panel = follow-up แยก)

**ลำดับ:** ทำ `read_url` ก่อน (ง่ายกว่า) → แล้ว `analyze_image`

---

## 1. `read_url` — เพิ่มใน `tools/web.py` (ข้าง `search_web`)

**dep ใหม่:** `trafilatura` (ฟรี ไม่ต้อง key · ดึงเนื้อหลัก ตัดเมนู/โฆษณา · รองรับไทย) → `requirements.txt`

```python
def read_url(url: str) -> str:
    """อ่านเนื้อหาหลักของหน้าเว็บจาก URL (บทความ/ข่าว/บล็อก) ใช้เมื่อผู้ใช้ให้ลิงก์มาแล้วขอให้
    อ่าน/สรุป/ตอบคำถามจากหน้านั้น — ดึงเฉพาะเนื้อหาหลัก

    Args:
        url: ลิงก์เต็ม (ขึ้นต้น http:// หรือ https://)

    Returns:
        หัวข้อ + เนื้อหาหลัก (ตัดถ้ายาวเกิน) หรือข้อความบอกว่าอ่านไม่ได้
    """
```

**รายละเอียด:**
- validate: ต้องขึ้นต้น `http://` / `https://` (บล็อก `file://`, `gopher://` ฯลฯ)
- **SSRF guard** (สำคัญ — LLM ชี้ URL ไปไหนก็ได้): `socket.getaddrinfo(host)` → ถ้า resolve เป็น private / loopback / link-local
  (`ipaddress.ip_address(...).is_private / is_loopback / is_link_local`) → ปฏิเสธ ·
  กันชี้ไป `127.0.0.1:8000` (server ตัวเอง) / `169.254.169.254` (cloud metadata) / IP ในวง LAN
- `trafilatura.fetch_url(url)` → `trafilatura.extract(html, include_comments=False, include_tables=True, favor_precision=True)`
- timeout ~10 วิ (ตั้งผ่าน `trafilatura.settings` / env) — กัน chat turn ค้าง
- หัวข้อจาก `trafilatura.extract_metadata(html).title` fallback `<title>`
- ตัดที่ `_MAX_URL_CHARS = 8000` + ต่อท้าย "...(ตัดไว้)"
- error (เน็ตหลุด / 404 / ไม่ใช่ HTML เช่น PDF) → คืน string graceful
- **ไม่มี `pending_action`** — คืน string ให้ Gemini สรุปเอง

---

## 2. `analyze_image` — `tools/vision.py` (ไฟล์ใหม่)

**dep ใหม่:** ไม่มี (มี `google-genai` แล้ว) · `Pillow` *optional* — มีก็ย่อรูปใหญ่ก่อนส่ง (ประหยัด quota/token), ไม่มีก็ส่งดิบ

```python
def analyze_image(path: str, question: str = "") -> str:
    """ดู/วิเคราะห์ไฟล์รูปในโฟลเดอร์ที่ผู้ใช้อนุญาต ใช้เมื่อผู้ใช้ขอให้ดูรูป บอกว่าในรูปมีอะไร
    อ่านข้อความในรูป (OCR) เทียบรูป ฯลฯ

    Args:
        path: path ของไฟล์รูป นับจากโฟลเดอร์ที่อนุญาต (เช่น "screenshot.png", "รูป/ใบเสร็จ.jpg")
        question: สิ่งที่อยากรู้จากรูป (เว้นว่าง = บรรยายทั่วไป)
    """
```

**รายละเอียด:**
- guard: `files.get_allowed_folder()` ยังไม่ตั้ง → บอกให้กดปุ่ม 📁 ก่อน
- **security ฟรี:** `ok, target = files._resolve_safe_path(path)` — containment check ตัวเดียวกับ file tools
  (กัน `../`, sibling-prefix) · ไม่ผ่าน → `files._log_activity("analyze_image", path, False, "outside allowed scope")`
- นามสกุล: `_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}` (gif/bmp → แปลงด้วย Pillow ถ้ามี ไม่งั้นปฏิเสธ)
- ขนาด: `_MAX_IMAGE_BYTES = 12 * 1024 * 1024` · Pillow มี + รูปใหญ่ → ย่อ longest edge ≤ 1024px
- **circular import:** `tools/vision.py` ห้าม `import server` (server import tools) → สร้าง client เองแบบ lazy + cache:

  ```python
  _client = None
  def _get_client():
      global _client
      if _client is None:
          _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
      return _client
  ```

  (อ่าน env ตอนเรียก เหมือน `mail.py`)
- เรียก vision:

  ```python
  resp = _get_client().models.generate_content(
      model=os.environ.get("VISION_MODEL", "gemini-3.5-flash-lite"),
      contents=[
          types.Part.from_bytes(data=img, mime_type=mime),
          question.strip() or "บรรยายว่าในรูปนี้มีอะไร ตอบภาษาไทยสั้นๆ",
      ],
  )
  return resp.text.strip()
  ```

- **ต้องเช็ค:** รุ่น `-flash-lite` รับ image input ไหม — ถ้าไม่ ตั้ง `VISION_MODEL=gemini-3.5-flash` ใน `.env` (เลยแยกเป็น env var)
- **quota drift:** นี่เป็น Gemini call ที่ 2 ต่อการเรียก (ซ้อนใน tool call) · `server.py`'s `quota_state["used_today"]`
  จะไม่เห็น (นับแค่ `chat.send_message`) → รับได้สำหรับ MVP, note ไว้
- error → "ดูรูปไม่สำเร็จค่ะ ({type})" · สำเร็จ → `files._log_activity("analyze_image", path, True)`

---

## 3. Wiring

| ไฟล์ | แก้ |
|---|---|
| `requirements.txt` | +`trafilatura` (comment: `Pillow` optional สำหรับ analyze_image) |
| `tools/web.py` | +`read_url()` + `_MAX_URL_CHARS` + SSRF helper |
| `tools/vision.py` | **ใหม่** — `analyze_image()` + `_get_client()` |
| `tools/__init__.py` | `from .web import read_url, search_web` · `from .vision import analyze_image` · +`__all__` 2 ชื่อ |
| `server.py` | `from tools import (... analyze_image, read_url ...)` (alpha) · +2 ตัวใน `chat = client.chats.create(tools=[...])` |
| `personality.py` | +1 บรรทัด SYSTEM_PROMPT: "อ่าน/สรุปหน้าเว็บจากลิงก์ (`read_url`) และดู/วิเคราะห์รูปในโฟลเดอร์ที่อนุญาต (`analyze_image`) ได้" |
| `.env.example` + `.env` | `# VISION_MODEL=gemini-3.5-flash   (ใส่ถ้ารุ่น default ไม่รับรูป)` |
| `jusmin-ai/CLAUDE.md` | section ใหม่: 2 tool + pattern "vision = nested Gemini call" + SSRF guard ของ read_url + อัปเดต tree (`web.py` มี read_url, `vision.py` ใหม่) |

---

## 4. Test

```
./venv/Scripts/python.exe -W error::SyntaxWarning -m py_compile server.py tools/*.py
```

**`read_url`:**
- `tools.read_url("https://en.wikipedia.org/wiki/J.A.R.V.I.S.")` → หัวข้อ + เนื้อ
- `tools.read_url("ftp://x")` → ปฏิเสธสุภาพ
- `tools.read_url("http://127.0.0.1:8000/")` → SSRF บล็อก
- `tools.read_url("https://<ข่าวไทยสักเว็บ>/...")` → ดึงข้อความไทยได้
- URL ตาย / 404 → graceful

**`analyze_image`:** (วางรูปทดสอบในโฟลเดอร์ที่อนุญาตก่อน)
- `tools.analyze_image("test.png", "มีข้อความอะไรในรูป")` → คำตอบ
- `tools.analyze_image("../../secret.png")` → ปฏิเสธ (นอกขอบเขต)
- `tools.analyze_image("notes.txt")` → ปฏิเสธ (ไม่ใช่รูป)
- ยังไม่ตั้งโฟลเดอร์ → บอกให้เลือกก่อน
- รูป 20MB → ย่อ (ถ้ามี Pillow) หรือ reject ขนาด

**เบราว์เซอร์จริง:** "จัสมิน อ่านลิงก์นี้ให้หน่อย \<url\>" → สรุปเป็นเสียง · "ดูรูป screenshot.png ว่าเขียนอะไร" → ตอบเป็นเสียง

**regression:** tool เดิม 24 ตัวยังทำงาน · quota tracking ไม่พัง (note vision call ไม่ถูกนับ)

---

## 5. แรง / เสี่ยง

| | แรง | เสี่ยง | จุดที่ต้องระวัง |
|---|---|---|---|
| `read_url` | ~2 ชม. | ต่ำ | SSRF guard, timeout |
| `analyze_image` | ~3 ชม. | ต่ำ-กลาง | circular import (client เอง), รุ่นต้องรับรูป, quota drift, path safety (ใช้ `_resolve_safe_path` ฟรี) |

**HUD panel** (แสดง thumbnail + คำตอบ / reader panel) = **follow-up แยก** ~ครึ่งวัน/อัน ·
ต้องมี endpoint `GET /api/allowed-file` (เช็ค containment ฝั่ง server อีกรอบ ห้ามเชื่อ path จาก client) + `pending_action`
