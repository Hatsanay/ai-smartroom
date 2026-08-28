import json
import os
import shutil
from datetime import datetime

# เข้าถึงไฟล์ในคอม — ผู้ใช้ขอชัดเจนว่าต้อง "จำกัดแค่โฟลเดอร์ที่กำหนดไว้" เท่านั้น (ไม่ใช่ทั้งเครื่อง)
# เลือกโฟลเดอร์ผ่านปุ่มใน UI (native folder picker ของ Windows ผ่าน tkinter — ใช้ได้เพราะ server กับ
# browser รันอยู่บนเครื่องเดียวกัน ถ้าย้ายไป Pi ในอนาคตกลไกนี้ใช้ไม่ได้แล้ว ต้องคิดใหม่) เก็บ path ไว้ใน
# _allowed_folder ตัวเดียว (personal use คนเดียวเหมือน state อื่นๆ ในไฟล์นี้)
#
# **จุด security ที่สำคัญที่สุดของ tool ชุดนี้**: ทุก path ที่ LLM ส่งมาต้อง resolve เป็น absolute path
# จริงแล้วเช็คด้วย os.path.commonpath() ว่าอยู่ใต้ _allowed_folder จริงๆ เท่านั้น — ไม่ใช้ str.startswith()
# เทียบ prefix ตรงๆ เพราะพลาดง่าย (เช่น "/allowed" จะ match ผิดกับ "/allowed-secret" ที่จริงเป็นคนละ
# โฟลเดอร์กันเลย) กัน LLM ใช้ "../" หรือ absolute path หลอกให้อ่านไฟล์นอกขอบเขตที่ผู้ใช้อนุญาตไว้
_allowed_folder: str | None = None

_ALLOWED_TEXT_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".csv", ".json", ".py", ".log", ".yaml", ".yml", ".xml", ".ini", ".cfg",
}
_MAX_FILE_READ_BYTES = 200_000  # ~200KB กันไฟล์ใหญ่เกินไปจนบวม context ของ Gemini

# โฟลเดอร์โปรเจกต์ (jusmin-ai/) = แม่ของ tools/ ที่ไฟล์นี้อยู่ — logs/ กับ file_access_config.json
# ต้องอยู่ที่ระดับโปรเจกต์เหมือนเดิม ไม่ใช่ใน tools/ (ตอนแยก tools.py -> package `__file__` เลื่อนลงมา 1 ชั้น)
_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ไฟล์ log กิจกรรมเกี่ยวกับข้อมูลในเครื่อง — ผู้ใช้ขอไว้เป็นกลไกความโปร่งใส เพราะตอนนี้ จัสมิน แก้ไข/
# ลบไฟล์ได้จริงแล้ว (ไม่ใช่แค่อ่าน) เก็บไว้ที่ jusmin-ai/logs/ (แยกจากโฟลเดอร์ที่ผู้ใช้เลือก ตั้งใจไม่
# เอาไปแปะปนกับไฟล์จริงของผู้ใช้) สร้างไฟล์ log **ใหม่** ทุกครั้งที่เลือกโฟลเดอร์ใหม่ (ตามที่ผู้ใช้ขอ) —
# ตั้งชื่อด้วย timestamp กันไฟล์เก่าถูกเขียนทับ เก็บประวัติทุกรอบการอนุญาตไว้ครบ
_LOG_DIR = os.path.join(_PROJECT_DIR, "logs")
_current_log_path: str | None = None

# จำโฟลเดอร์ที่อนุญาตไว้ข้าม restart — เก็บ path ลงไฟล์ config เล็กๆ (อยู่ใน .gitignore เพราะเป็น
# absolute path เฉพาะเครื่องของผู้ใช้ ไม่ใช่ค่าที่ควร commit) พอ server เริ่มใหม่แล้ว import module นี้
# จะอ่านกลับมาให้เอง ถ้าโฟลเดอร์นั้นยังมีอยู่จริง — ไม่ต้องกดปุ่มเลือกโฟลเดอร์ใหม่ทุกครั้งที่ restart
_FILE_ACCESS_CONFIG = os.path.join(_PROJECT_DIR, "file_access_config.json")


def _persist_allowed_folder(path: str | None) -> None:
    try:
        with open(_FILE_ACCESS_CONFIG, "w", encoding="utf-8") as f:
            json.dump({"allowed_folder": path}, f, ensure_ascii=False, indent=2)
    except OSError:
        pass  # เขียน config ไม่ได้ก็แค่ไม่จำข้าม restart ไม่ควรทำให้ feature หลักพังตาม


def _start_new_activity_log(folder: str, action: str = "folder_selected") -> None:
    global _current_log_path
    os.makedirs(_LOG_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    _current_log_path = os.path.join(_LOG_DIR, f"file_activity_{ts}.json")
    _write_log_entries([
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "action": action,
            "path": folder,
            "success": True,
            "detail": None,
        }
    ])


def _write_log_entries(entries: list[dict]) -> None:
    if not _current_log_path:
        return
    try:
        with open(_current_log_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
    except OSError:
        pass  # log เขียนไม่ได้ก็ไม่ควรทำให้ tool หลักพังตาม แค่เสียประวัติไปบรรทัดนั้น


def _log_activity(action: str, path: str, success: bool, detail: str | None = None) -> None:
    if not _current_log_path:
        return
    try:
        with open(_current_log_path, "r", encoding="utf-8") as f:
            entries = json.load(f)
    except (OSError, json.JSONDecodeError):
        entries = []
    entries.append(
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "action": action,
            "path": path,
            "success": success,
            "detail": detail,
        }
    )
    _write_log_entries(entries)


def set_allowed_folder(path: str) -> None:
    """เรียกจาก server.py หลังผู้ใช้เลือกโฟลเดอร์ผ่าน native folder picker ใน UI — เริ่ม log กิจกรรม
    รอบใหม่ทุกครั้งที่เรียก (ไฟล์ log เดิมของรอบก่อนหน้ายังอยู่ครบ ไม่ได้ถูกลบ) และจำ path ไว้ข้าม
    restart ผ่านไฟล์ config"""
    global _allowed_folder
    _allowed_folder = path
    _persist_allowed_folder(path)
    _start_new_activity_log(path)


def get_allowed_folder() -> str | None:
    return _allowed_folder


def _resolve_safe_path(subpath: str) -> tuple[bool, str]:
    """resolve subpath เทียบกับ _allowed_folder แล้วเช็คว่ายังอยู่ในขอบเขตจริง คืน (ปลอดภัยไหม, path เต็ม)"""
    if not _allowed_folder:
        return False, ""
    subpath = (subpath or "").strip().lstrip("/\\")
    try:
        allowed_root = os.path.realpath(_allowed_folder)
        target = os.path.realpath(os.path.join(allowed_root, subpath))
        common = os.path.commonpath([allowed_root, target])
    except (ValueError, OSError):
        # ValueError: คนละ drive กันบน Windows (เช่น C:\ vs D:\) ก็ถือว่าไม่ปลอดภัยเลย
        return False, ""
    return common == allowed_root, target


def list_files(subpath: str = "") -> str:
    """แสดงรายชื่อไฟล์/โฟลเดอร์ในโฟลเดอร์ที่ผู้ใช้อนุญาตให้ จัสมิน เข้าถึงได้เท่านั้น (ตั้งค่าจากปุ่ม
    เลือกโฟลเดอร์ในหน้าเว็บ) ใช้เมื่อผู้ใช้ขอให้ดูว่ามีไฟล์อะไรบ้าง หรือหาไฟล์ในโฟลเดอร์ที่อนุญาตไว้

    Args:
        subpath: โฟลเดอร์ย่อยที่จะดู (ปล่อยว่างไว้ถ้าจะดูโฟลเดอร์หลักที่อนุญาตไว้เลย)

    Returns:
        รายชื่อไฟล์และโฟลเดอร์ย่อย
    """
    if not _allowed_folder:
        return "ยังไม่ได้ตั้งค่าโฟลเดอร์ที่อนุญาตให้เข้าถึงเลยค่ะ กดปุ่ม 📁 เลือกโฟลเดอร์ มุมขวาบนของหน้าเว็บก่อนนะคะ"

    ok, target = _resolve_safe_path(subpath)
    if not ok:
        _log_activity("list_files", subpath, False, "outside allowed scope")
        return "ไม่สามารถเข้าถึงโฟลเดอร์นี้ได้ค่ะ อยู่นอกขอบเขตที่อนุญาตไว้"
    if not os.path.isdir(target):
        return f'"{subpath}" ไม่ใช่โฟลเดอร์ค่ะ'

    try:
        entries = sorted(os.listdir(target))
    except OSError:
        _log_activity("list_files", subpath, False, "OSError listing directory")
        return "เปิดโฟลเดอร์นี้ไม่สำเร็จค่ะ"

    _log_activity("list_files", subpath, True)
    if not entries:
        return "โฟลเดอร์นี้ว่างเปล่าค่ะ"

    lines = []
    for name in entries[:200]:  # กันโฟลเดอร์ที่มีไฟล์เยอะมากจนตอบยาวเกินไป
        full = os.path.join(target, name)
        if os.path.isdir(full):
            lines.append(f"[โฟลเดอร์] {name}")
        else:
            try:
                size_kb = os.path.getsize(full) / 1024
                lines.append(f"[ไฟล์] {name} ({size_kb:.0f} KB)")
            except OSError:
                lines.append(f"[ไฟล์] {name}")
    return "\n".join(lines)


def read_file(path: str) -> str:
    """อ่านเนื้อหาไฟล์ข้อความ — จำกัดแค่ไฟล์ในโฟลเดอร์ที่ผู้ใช้อนุญาตให้ จัสมิน เข้าถึงได้เท่านั้น
    (ตั้งค่าจากปุ่มเลือกโฟลเดอร์ในหน้าเว็บ) ใช้เมื่อผู้ใช้ขอให้อ่าน/สรุปเนื้อหาไฟล์ในโฟลเดอร์ที่อนุญาตไว้
    รองรับเฉพาะไฟล์ข้อความเท่านั้น (.txt, .md, .csv, .json, .py ฯลฯ) ไม่รองรับรูปภาพ/วิดีโอ/ไฟล์ไบนารี

    Args:
        path: path ของไฟล์ นับจากโฟลเดอร์ที่อนุญาตไว้ (เช่น "notes.txt" หรือ "sub/data.csv")

    Returns:
        เนื้อหาไฟล์ (ตัดถ้ายาวเกินไป)
    """
    if not _allowed_folder:
        return "ยังไม่ได้ตั้งค่าโฟลเดอร์ที่อนุญาตให้เข้าถึงเลยค่ะ กดปุ่ม 📁 เลือกโฟลเดอร์ มุมขวาบนของหน้าเว็บก่อนนะคะ"

    ok, target = _resolve_safe_path(path)
    if not ok:
        _log_activity("read_file", path, False, "outside allowed scope")
        return "ไม่สามารถเข้าถึงไฟล์นี้ได้ค่ะ อยู่นอกขอบเขตที่อนุญาตไว้"
    if not os.path.isfile(target):
        return f'ไม่พบไฟล์ "{path}" ค่ะ'

    ext = os.path.splitext(target)[1].lower()
    if ext not in _ALLOWED_TEXT_EXTENSIONS:
        _log_activity("read_file", path, False, f"disallowed extension {ext}")
        return f"ไฟล์นามสกุล {ext or '(ไม่มีนามสกุล)'} นี้อ่านไม่ได้ค่ะ รองรับแค่ไฟล์ข้อความ (.txt, .md, .csv, .json, .py ฯลฯ)"

    try:
        size = os.path.getsize(target)
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(_MAX_FILE_READ_BYTES)
    except OSError:
        _log_activity("read_file", path, False, "OSError reading file")
        return "อ่านไฟล์นี้ไม่สำเร็จค่ะ"

    _log_activity("read_file", path, True)
    if size > _MAX_FILE_READ_BYTES:
        content += "\n\n...(เนื้อหายาวเกินไป ตัดไว้แค่นี้ค่ะ)"
    return content


def create_folder(path: str) -> str:
    """สร้างโฟลเดอร์ใหม่ (รวมถึงโฟลเดอร์แม่ที่ยังไม่มีด้วย) — จำกัดแค่ในโฟลเดอร์ที่ผู้ใช้อนุญาตให้
    จัสมิน เข้าถึงได้เท่านั้น ใช้เมื่อผู้ใช้ขอให้สร้างโฟลเดอร์ใหม่

    Args:
        path: path ของโฟลเดอร์ใหม่ นับจากโฟลเดอร์ที่อนุญาตไว้ (เช่น "งาน/โปรเจกต์ใหม่")

    Returns:
        ข้อความยืนยันสั้นๆ
    """
    if not _allowed_folder:
        return "ยังไม่ได้ตั้งค่าโฟลเดอร์ที่อนุญาตให้เข้าถึงเลยค่ะ กดปุ่ม 📁 เลือกโฟลเดอร์ มุมขวาบนของหน้าเว็บก่อนนะคะ"

    ok, target = _resolve_safe_path(path)
    if not ok:
        _log_activity("create_folder", path, False, "outside allowed scope")
        return "ไม่สามารถสร้างโฟลเดอร์นี้ได้ค่ะ อยู่นอกขอบเขตที่อนุญาตไว้"

    try:
        os.makedirs(target, exist_ok=True)
    except OSError:
        _log_activity("create_folder", path, False, "OSError creating directory")
        return "สร้างโฟลเดอร์นี้ไม่สำเร็จค่ะ"

    _log_activity("create_folder", path, True)
    return f'สร้างโฟลเดอร์ "{path}" ให้แล้วค่ะ'


def write_file(path: str, content: str) -> str:
    """สร้างไฟล์ข้อความใหม่ หรือแก้ไข (เขียนทับทั้งไฟล์) ไฟล์ที่มีอยู่แล้ว — จำกัดแค่ในโฟลเดอร์ที่
    ผู้ใช้อนุญาตให้ จัสมิน เข้าถึงได้เท่านั้น ใช้เมื่อผู้ใช้ขอให้สร้างไฟล์ใหม่หรือแก้ไขเนื้อหาไฟล์เดิม
    ถ้าจะแก้ไขไฟล์ที่มีอยู่แล้ว ให้เรียก read_file() อ่านเนื้อหาเดิมมาก่อนเสมอ แล้วค่อยส่งเนื้อหาฉบับ
    เต็มที่แก้ไขแล้วมาที่นี่ (tool นี้เขียนทับทั้งไฟล์เสมอ ไม่ใช่แค่ต่อท้ายหรือแก้บางส่วน) รองรับเฉพาะ
    ไฟล์ข้อความเท่านั้น

    Args:
        path: path ของไฟล์ นับจากโฟลเดอร์ที่อนุญาตไว้ (เช่น "notes.txt")
        content: เนื้อหาทั้งหมดของไฟล์ที่ต้องการให้เป็นหลังบันทึก

    Returns:
        ข้อความยืนยันสั้นๆ
    """
    if not _allowed_folder:
        return "ยังไม่ได้ตั้งค่าโฟลเดอร์ที่อนุญาตให้เข้าถึงเลยค่ะ กดปุ่ม 📁 เลือกโฟลเดอร์ มุมขวาบนของหน้าเว็บก่อนนะคะ"

    ok, target = _resolve_safe_path(path)
    if not ok:
        _log_activity("write_file", path, False, "outside allowed scope")
        return "ไม่สามารถเขียนไฟล์นี้ได้ค่ะ อยู่นอกขอบเขตที่อนุญาตไว้"

    ext = os.path.splitext(target)[1].lower()
    if ext not in _ALLOWED_TEXT_EXTENSIONS:
        _log_activity("write_file", path, False, f"disallowed extension {ext}")
        return f"ไฟล์นามสกุล {ext or '(ไม่มีนามสกุล)'} นี้เขียนไม่ได้ค่ะ รองรับแค่ไฟล์ข้อความ (.txt, .md, .csv, .json, .py ฯลฯ)"

    existed = os.path.isfile(target)
    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
    except OSError:
        _log_activity("write_file", path, False, "OSError writing file")
        return "เขียนไฟล์นี้ไม่สำเร็จค่ะ"

    _log_activity("write_file", path, True, "overwritten" if existed else "created")
    return f'{"แก้ไข" if existed else "สร้าง"}ไฟล์ "{path}" ให้แล้วค่ะ'


def delete_path(path: str) -> str:
    """ลบไฟล์หรือโฟลเดอร์ (ถ้าเป็นโฟลเดอร์จะลบของข้างในทั้งหมดด้วย) — จำกัดแค่ในโฟลเดอร์ที่ผู้ใช้
    อนุญาตให้ จัสมิน เข้าถึงได้เท่านั้น ใช้เมื่อผู้ใช้ขอให้ลบไฟล์/โฟลเดอร์ **อย่างชัดเจนเท่านั้น**
    การกระทำนี้ลบถาวร กู้คืนไม่ได้ — ห้ามเรียกเองถ้าไม่แน่ใจว่าผู้ใช้ต้องการลบจริงๆ ให้ถามยืนยันก่อน
    ถ้าคำสั่งของผู้ใช้ดูกำกวมหรือไม่ชัดเจนว่าจะลบอะไรแน่

    Args:
        path: path ของไฟล์หรือโฟลเดอร์ที่จะลบ นับจากโฟลเดอร์ที่อนุญาตไว้

    Returns:
        ข้อความยืนยันสั้นๆ
    """
    if not _allowed_folder:
        return "ยังไม่ได้ตั้งค่าโฟลเดอร์ที่อนุญาตให้เข้าถึงเลยค่ะ กดปุ่ม 📁 เลือกโฟลเดอร์ มุมขวาบนของหน้าเว็บก่อนนะคะ"

    ok, target = _resolve_safe_path(path)
    if not ok:
        _log_activity("delete_path", path, False, "outside allowed scope")
        return "ไม่สามารถลบสิ่งนี้ได้ค่ะ อยู่นอกขอบเขตที่อนุญาตไว้"

    # กันลบโฟลเดอร์หลักที่อนุญาตไว้ทั้งก้อนโดยไม่ตั้งใจ (path ว่าง/"." resolve กลับมาเป็น allowed_root เป๊ะ)
    if target == os.path.realpath(_allowed_folder):
        _log_activity("delete_path", path, False, "refused: target is the allowed root folder itself")
        return "ลบโฟลเดอร์หลักที่อนุญาตไว้ทั้งก้อนไม่ได้ค่ะ ต้องระบุไฟล์/โฟลเดอร์ย่อยข้างในแทนนะคะ"

    if not os.path.exists(target):
        return f'ไม่พบ "{path}" ค่ะ'

    try:
        if os.path.isdir(target):
            shutil.rmtree(target)
        else:
            os.remove(target)
    except OSError:
        _log_activity("delete_path", path, False, "OSError deleting")
        return "ลบไม่สำเร็จค่ะ"

    _log_activity("delete_path", path, True)
    return f'ลบ "{path}" ให้แล้วค่ะ'


def _restore_allowed_folder_from_config() -> None:
    """เรียกครั้งเดียวตอน import module (ตอน server เริ่ม) — คืนค่าโฟลเดอร์ที่เคยเลือกไว้รอบก่อน ถ้า
    ยังมีอยู่จริง แล้วเปิด activity log ไฟล์ใหม่ของรอบนี้ (action="folder_restored") ให้ audit trail
    ของแต่ละรอบการรัน server แยกไฟล์กันชัดเจน ถ้าโฟลเดอร์ถูกลบ/ย้าย/ถอด drive ไปแล้วก็ข้ามไปเงียบๆ
    (ผู้ใช้กดเลือกใหม่ผ่านปุ่ม 📁 ได้)"""
    global _allowed_folder
    try:
        with open(_FILE_ACCESS_CONFIG, "r", encoding="utf-8") as f:
            saved = json.load(f).get("allowed_folder")
    except (OSError, json.JSONDecodeError):
        return
    if isinstance(saved, str) and os.path.isdir(saved):
        _allowed_folder = saved
        _start_new_activity_log(saved, action="folder_restored")


_restore_allowed_folder_from_config()
