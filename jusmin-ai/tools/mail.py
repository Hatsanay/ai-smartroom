"""อีเมล — อ่าน/ค้น/ส่ง ผ่าน IMAP+SMTP (stdlib ล้วน ไม่ต้อง API key). ตั้งค่าใน .env:
    EMAIL_ADDRESS=you@gmail.com
    EMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx   (Gmail: สร้าง App Password ที่ myaccount.google.com/apppasswords)
    EMAIL_IMAP_HOST=imap.gmail.com        (ไม่บังคับ)
    EMAIL_SMTP_HOST=smtp.gmail.com        (ไม่บังคับ)
    EMAIL_SMTP_PORT=587                   (ไม่บังคับ, STARTTLS)

หมายเหตุ: อ่าน os.environ ตอน "เรียกใช้" ไม่ใช่ตอน import (เพราะ tools ถูก import ก่อน load_dotenv() ใน server.py)

ครอบคลุมทุกกล่อง: inbox / sent (ที่ส่งออกไป) / drafts / all (ทุกฉบับ) / spam / trash / starred
- เลือกกล่องด้วยพารามิเตอร์ folder (รับได้ทั้งคำไทย/อังกฤษ ผ่าน _ALIAS)
- หากล่องจริงจาก IMAP SPECIAL-USE flag (Sent / Drafts / All ...) เลย ไม่ยึดชื่อ "[Gmail]/..." ที่เปลี่ยนตามภาษาบัญชี
- ค้นหา: บน Gmail ใช้ X-GM-RAW (พิมพ์ from:/to:/in:sent/subject:/after: ได้เต็มรูปแบบ), ที่อื่น fallback เป็น IMAP SEARCH ปกติ
"""
import imaplib
import mimetypes
import os
import smtplib
import time
from email import message_from_bytes
from email.header import decode_header, make_header
from email.message import EmailMessage

from . import files  # ใช้ _allowed_folder + _resolve_safe_path + audit log ร่วมกับ tool ไฟล์ในคอม

_MAX_ATTACH_BYTES = 25 * 1024 * 1024  # 25MB — เพดานของ Gmail ทั้งขาดาวน์โหลดและขาส่ง

_NOT_SET = (
    "ยังไม่ได้ตั้งค่าอีเมลค่ะ ใส่ EMAIL_ADDRESS กับ EMAIL_APP_PASSWORD (Gmail App Password) "
    "ในไฟล์ .env แล้ว restart server ก่อนนะคะ"
)

# จำ seq ของเมลที่เพิ่งแสดง + กล่องที่มันอยู่ -> read_email("2") อ้างลำดับจากลิสต์นั้นได้
_last_uids: list[bytes] = []
_last_mailbox: str = "inbox"

# คำที่ผู้ใช้ (หรือ LLM) อาจใช้เรียกแต่ละกล่อง -> ชื่อ kind มาตรฐาน
_ALIAS = {
    "": "inbox", "inbox": "inbox", "in": "inbox", "กล่องเข้า": "inbox", "เข้า": "inbox", "ขาเข้า": "inbox",
    "sent": "sent", "send": "sent", "sentmail": "sent", "sent mail": "sent", "outbox": "sent",
    "ส่งแล้ว": "sent", "ที่ส่ง": "sent", "ส่งออก": "sent", "เมลที่ส่ง": "sent", "ส่ง": "sent", "ขาออก": "sent",
    "draft": "drafts", "drafts": "drafts", "ร่าง": "drafts", "แบบร่าง": "drafts", "ฉบับร่าง": "drafts",
    "all": "all", "allmail": "all", "all mail": "all", "everything": "all", "any": "all",
    "ทั้งหมด": "all", "ทุกกล่อง": "all", "ทุกฉบับ": "all", "archive": "all", "archived": "all",
    "เก็บถาวร": "all", "คลัง": "all", "เก็บเข้าคลัง": "all",
    "spam": "spam", "junk": "spam", "สแปม": "spam", "ขยะ": "spam", "เมลขยะ": "spam",
    "trash": "trash", "bin": "trash", "deleted": "trash", "ถังขยะ": "trash", "ลบแล้ว": "trash",
    "starred": "starred", "star": "starred", "flagged": "starred", "ติดดาว": "starred", "ดาว": "starred",
    "important": "important", "priority": "important", "สำคัญ": "important",
}

# kind -> IMAP SPECIAL-USE flag (RFC 6154) ที่ใช้หากล่องจริง (lowercase, มี backslash เดียว)
_SPECIAL = {
    "sent": rb"\sent", "drafts": rb"\drafts", "all": rb"\all",
    "spam": rb"\junk", "trash": rb"\trash", "starred": rb"\flagged",
    "important": rb"\important", "archive": rb"\all",
}
# เผื่อหา flag ไม่เจอ -> เดาชื่อแบบอังกฤษของ Gmail
_GMAIL_NAME = {
    "sent": b'"[Gmail]/Sent Mail"', "drafts": b'"[Gmail]/Drafts"', "all": b'"[Gmail]/All Mail"',
    "spam": b'"[Gmail]/Spam"', "trash": b'"[Gmail]/Trash"', "starred": b'"[Gmail]/Starred"',
    "important": b'"[Gmail]/Important"',
}
_LABEL_TH = {
    "inbox": "เมลใหม่", "sent": "เมลที่ส่ง", "drafts": "ฉบับร่าง", "all": "เมลทั้งหมด",
    "spam": "เมลขยะ", "trash": "เมลในถังขยะ", "starred": "เมลติดดาว", "important": "เมลสำคัญ",
}

import re

_LIST_RE = re.compile(rb'^\((?P<flags>[^)]*)\)\s+(?:"[^"]*"|NIL|\S+)\s+(?P<name>.+?)\s*$')


def _cfg():
    addr = os.environ.get("EMAIL_ADDRESS", "").strip()
    # Google แสดง App Password เป็น 4 กลุ่มมีเว้นวรรค ("xxxx xxxx xxxx xxxx") — ผู้ใช้มักก๊อปมาทั้งวรรค
    # ตัดช่องว่างในตัวออกให้เลย (App Password ไม่มีเว้นวรรคจริง) จะได้ไม่ต้องมาบอกผู้ใช้ลบเอง
    pw = "".join(os.environ.get("EMAIL_APP_PASSWORD", "").split())
    if not addr or not pw:
        return None
    return {
        "addr": addr,
        "pw": pw,
        "imap": os.environ.get("EMAIL_IMAP_HOST", "imap.gmail.com").strip(),
        "smtp": os.environ.get("EMAIL_SMTP_HOST", "smtp.gmail.com").strip(),
        "port": int(os.environ.get("EMAIL_SMTP_PORT", "587") or 587),
    }


def _is_gmail(cfg) -> bool:
    h = (cfg.get("imap") or "").lower()
    return h.endswith("gmail.com") or h.endswith("googlemail.com")


def _canon_folder(folder) -> str:
    key = (folder or "").strip().lower()
    return _ALIAS.get(key, key or "inbox")


def _dec(raw) -> str:
    """decode RFC2047 header (=?UTF-8?B?..?=) เป็น str ปกติ"""
    if raw is None:
        return ""
    try:
        return str(make_header(decode_header(raw))).strip()
    except Exception:
        return str(raw).strip()


def _parse_list_line(raw):
    """แยกบรรทัดจาก IMAP LIST -> (flags bytes lowercase, mailbox-name bytes ตามที่ server ส่งมา ไม่แตะ encoding)"""
    if isinstance(raw, (list, tuple)):
        raw = b" ".join(p if isinstance(p, bytes) else str(p).encode() for p in raw)
    if not isinstance(raw, bytes):
        raw = str(raw).encode()
    mm = _LIST_RE.match(raw.strip())
    if not mm:
        return b"", b""
    name = mm.group("name").strip()
    if len(name) >= 2 and name[:1] == b'"' and name[-1:] == b'"':
        name = name[1:-1]
    return mm.group("flags").lower(), name


def _resolve_mailbox(m, kind: str) -> bytes:
    """kind -> ชื่อกล่อง IMAP (bytes, ใส่ quote ให้แล้วถ้ามีช่องว่าง). inbox = INBOX เสมอ"""
    if kind == "inbox":
        return b"INBOX"
    want = _SPECIAL.get(kind)
    if want:
        try:
            typ, data = m.list()
            if typ == "OK":
                for raw in data or []:
                    if not raw:
                        continue
                    flags, name = _parse_list_line(raw)
                    if want in flags and name:
                        return b'"' + name + b'"' if b" " in name else name
        except Exception:
            pass
    return _GMAIL_NAME.get(kind, b"INBOX")


def _open(cfg, kind: str = "inbox"):
    """login + select กล่องที่ต้องการ -> (imap, message_count, kind ที่ใช้จริง)"""
    m = imaplib.IMAP4_SSL(cfg["imap"])
    m.login(cfg["addr"], cfg["pw"])
    mbox = _resolve_mailbox(m, kind)
    typ, d = m.select(mbox)
    if typ != "OK":
        m.select("INBOX")
        return m, 0, "inbox"
    try:
        count = int(d[0])
    except Exception:
        count = 0
    return m, count, kind


def _search_seqs(m, query: str, is_gmail: bool):
    """คืน list ของ sequence number (bytes) ที่ตรงกับ query — Gmail ใช้ X-GM-RAW, ที่อื่น IMAP SEARCH ปกติ"""
    query = (query or "").strip()
    if not query:
        typ, data = m.search(None, "ALL")
        return data[0].split() if typ == "OK" and data and data[0] else []
    if is_gmail:
        try:
            if query.isascii():
                esc = query.replace("\\", "\\\\").replace('"', '\\"')
                typ, data = m.search(None, "X-GM-RAW", '"%s"' % esc)
            else:
                m.literal = query.encode("utf-8")
                typ, data = m.search("UTF-8", "X-GM-RAW")
            if typ == "OK":
                return data[0].split() if data and data[0] else []
        except Exception:
            pass  # ตกไปใช้ SEARCH ปกติ
    try:
        if query.isascii():
            q = query.replace('"', "")
            crit = '(OR (OR (OR FROM "%s" TO "%s") CC "%s") SUBJECT "%s")' % (q, q, q, q)
            typ, data = m.search(None, crit)
        else:
            m.literal = query.encode("utf-8")
            typ, data = m.search("UTF-8", "TEXT")
        if typ == "OK":
            return data[0].split() if data and data[0] else []
    except Exception:
        pass
    return []


def _newest_seqs(count: int, n: int):
    """seq ของ n ฉบับล่าสุด (ใหม่ก่อน) โดยไม่ต้อง SEARCH — ใช้กับกล่องที่ไม่ต้องกรอง"""
    if count <= 0:
        return []
    lo = max(1, count - max(1, n) + 1)
    return [str(x).encode() for x in range(count, lo - 1, -1)]


def _fmt_row(m, seq, i: int, my_addr: str, force_sent: bool = False) -> str:
    """หนึ่งบรรทัดในลิสต์ — โชว์ 'ถึง <ผู้รับ>' ถ้าเป็นเมลที่เราส่งเอง ไม่งั้นโชว์ 'จาก <ผู้ส่ง>'"""
    _t, hd = m.fetch(seq, "(BODY.PEEK[HEADER.FIELDS (FROM TO SUBJECT DATE)])")
    try:
        msg = message_from_bytes(hd[0][1])
    except Exception:
        return f"{i}. (อ่านหัวเมลไม่ได้)"
    frm, to = _dec(msg.get("From")), _dec(msg.get("To"))
    mine = force_sent or (my_addr and my_addr.lower() in frm.lower())
    who = f"ถึง {to or '-'}" if mine else f"จาก {frm or '-'}"
    subj = _dec(msg.get("Subject")) or "(ไม่มีหัวข้อ)"
    return f"{i}. {who} — {subj}  [{_dec(msg.get('Date'))}]"


def check_email(n: int = 5, folder: str = "inbox") -> str:
    """ดูอีเมลล่าสุดในกล่องที่ต้องการ ใช้เมื่อผู้ใช้ถาม "มีเมลใหม่ไหม" / "ขอดูเมลที่เพิ่งส่งไป" /
    "ดูฉบับร่าง" / "เมลในถังขยะ"

    Args:
        n: จำนวนฉบับล่าสุดที่จะแสดง (ค่าเริ่มต้น 5)
        folder: กล่องเมล — "inbox" (ค่าเริ่มต้น, เฉพาะที่ยังไม่อ่าน) / "sent" (ที่เราส่งออกไป) /
            "drafts" (ฉบับร่าง) / "all" (ทุกฉบับรวมที่อ่านแล้ว) / "spam" / "trash" / "starred" (ติดดาว)

    Returns:
        จำนวนรวม + รายการ (ลำดับ, ผู้ส่งหรือผู้รับ, หัวข้อ, วันเวลา)
    """
    global _last_uids, _last_mailbox
    cfg = _cfg()
    if not cfg:
        return _NOT_SET
    kind = _canon_folder(folder)
    label = _LABEL_TH.get(kind, "เมล")
    try:
        m, count, kind = _open(cfg, kind)
        try:
            if kind == "inbox":
                _t, data = m.search(None, "UNSEEN")
                seqs = data[0].split() if data and data[0] else []
                if not seqs:
                    return "ไม่มีเมลใหม่ที่ยังไม่ได้อ่านค่ะ"
                total = len(seqs)
                pick = seqs[-max(1, n):][::-1]
            else:
                if count <= 0:
                    return f"ไม่มี{label}ค่ะ"
                total = count
                pick = _newest_seqs(count, n)
            _last_uids = pick
            _last_mailbox = kind
            force_sent = kind in ("sent", "drafts")
            lines = [_fmt_row(m, s, i, cfg["addr"], force_sent) for i, s in enumerate(pick, 1)]
            head = f"{label} {total} ฉบับค่ะ" + (
                f" (แสดง {len(pick)} ล่าสุด)" if total > len(pick) else ""
            )
            return head + ":\n" + "\n".join(lines)
        finally:
            m.logout()
    except Exception as e:
        return f"เช็คเมลไม่สำเร็จค่ะ ({type(e).__name__}) — ลองใหม่อีกทีนะคะ"


def search_email(query: str, folder: str = "all", limit: int = 10) -> str:
    """ค้นอีเมล "ทุกกล่อง" (รวมที่ส่งออกไปแล้ว ที่อ่านแล้ว ที่เก็บเข้าคลัง) จากผู้ส่ง/ผู้รับ/หัวข้อ/เนื้อหา
    ใช้เมื่อผู้ใช้ถามหา "เมลจาก X" / "เมลที่ผมส่งหา Y" / "เคยส่งเมลเรื่อง Z ไปไหม"

    Args:
        query: คำค้น — พิมพ์เปล่าๆ ก็ได้ หรือใช้รูปแบบของ Gmail เพื่อเจาะจง เช่น
            from:someone@x.com , to:boss , subject:ใบเสนอราคา , in:sent , after:2026/8/1 , has:attachment
            (ต่อกันได้ เช่น "in:sent to:boss ใบเสนอราคา")
        folder: ค่าเริ่มต้น "all" = ค้นทุกกล่อง; ระบุ "sent"/"inbox"/... เพื่อจำกัดเฉพาะกล่องนั้น
        limit: จำนวนผลลัพธ์สูงสุด (ค่าเริ่มต้น 10)

    Returns:
        รายการเมลที่ตรง (ล่าสุดก่อน)
    """
    global _last_uids, _last_mailbox
    cfg = _cfg()
    if not cfg:
        return _NOT_SET
    query = (query or "").strip()
    if not query:
        return "จะค้นเมลด้วยคำว่าอะไรคะ"
    kind = _canon_folder(folder or "all")
    is_gmail = _is_gmail(cfg)
    try:
        m, _count, kind = _open(cfg, kind)
        try:
            seqs = _search_seqs(m, query, is_gmail)
            if not seqs:
                where = "" if kind == "all" else f"ในกล่อง{_LABEL_TH.get(kind, kind)} "
                return f'ไม่เจอเมล{where}ที่ตรงกับ "{query}" ค่ะ'
            pick = seqs[-max(1, limit):][::-1]
            _last_uids = pick
            _last_mailbox = kind
            force_sent = kind in ("sent", "drafts")
            lines = [_fmt_row(m, s, i, cfg["addr"], force_sent) for i, s in enumerate(pick, 1)]
            return f"เจอ {len(seqs)} ฉบับ (แสดง {len(pick)} ล่าสุด):\n" + "\n".join(lines)
        finally:
            m.logout()
    except Exception as e:
        return f"ค้นเมลไม่สำเร็จค่ะ ({type(e).__name__})"


def save_attachment(query: str, name: str = "", dest: str = "") -> str:
    """ดาวน์โหลด/บันทึกไฟล์แนบจากอีเมลลงเครื่อง — ลงได้เฉพาะในโฟลเดอร์ที่ผู้ใช้อนุญาต (ปุ่ม 📁 ในหน้าเว็บ
    ตัวเดียวกับ list_files/read_file) ใช้เมื่อผู้ใช้บอก "ดาวน์โหลดไฟล์แนบ" / "เซฟไฟล์ในเมลนั้นไว้ให้หน่อย"

    Args:
        query: จะเอาไฟล์แนบจากเมลฉบับไหน — ลำดับจากลิสต์ที่เพิ่งแสดง (เช่น "2") หรือคำในผู้ส่ง/หัวข้อ
        name: ระบุชื่อไฟล์แนบที่ต้องการ (เว้นว่าง = เอาทุกไฟล์แนบในเมลฉบับนั้น) จับแบบมีคำนี้อยู่ในชื่อ
        dest: โฟลเดอร์ย่อยปลายทางนับจากโฟลเดอร์ที่อนุญาต (เว้นว่าง = ลงโฟลเดอร์หลักเลย)

    Returns:
        รายชื่อไฟล์ที่บันทึก + ขนาด + ที่อยู่ (หรือบอกว่าไม่มีไฟล์แนบ)
    """
    cfg = _cfg()
    if not cfg:
        return _NOT_SET
    if not files.get_allowed_folder():
        return "ยังไม่ได้ตั้งค่าโฟลเดอร์ปลายทางค่ะ กดปุ่ม 📁 เลือกโฟลเดอร์ในหน้าเว็บก่อนนะคะ"
    want = (name or "").strip().lower()
    is_gmail = _is_gmail(cfg)
    kind = _pick_kind(query, "", cfg)
    try:
        m, _c, _k = _open(cfg, kind)
        try:
            seq = _locate_seq(m, query, "", is_gmail)
            if seq is None:
                return "ไม่แน่ใจว่าจะเอาไฟล์แนบจากเมลฉบับไหน ลองเช็ค/ค้นเมลก่อนแล้วบอกลำดับหรือชื่อผู้ส่งค่ะ"
            _t, data = m.fetch(seq, "(RFC822)")
            msg = message_from_bytes(data[0][1])
        finally:
            m.logout()
    except Exception as e:
        return f"ดึงไฟล์แนบไม่สำเร็จค่ะ ({type(e).__name__})"

    root = os.path.realpath(files.get_allowed_folder())
    saved, skipped = [], []
    for fname, payload in _iter_attachments(msg):
        if want and want not in fname.lower():
            continue
        if len(payload) > _MAX_ATTACH_BYTES:
            skipped.append(f"{fname} (ใหญ่เกิน 25MB)")
            continue
        sub = ((dest or "").strip().strip("/\\") + "/" + files._safe_name(fname)).lstrip("/")
        ok, tgt = files._resolve_safe_path(sub)
        if not ok:
            files._log_activity("save_attachment", sub, False, "outside allowed scope")
            skipped.append(f"{fname} (นอกขอบเขตที่อนุญาต)")
            continue
        tgt = files._uniq(tgt)
        try:
            os.makedirs(os.path.dirname(tgt), exist_ok=True)
            with open(tgt, "wb") as fh:
                fh.write(payload)
        except OSError:
            files._log_activity("save_attachment", sub, False, "OSError writing file")
            skipped.append(f"{fname} (เขียนไฟล์ไม่สำเร็จ)")
            continue
        try:
            rel = os.path.relpath(tgt, root)
        except ValueError:
            rel = os.path.basename(tgt)
        files._log_activity("save_attachment", rel, True)
        saved.append((os.path.basename(tgt), len(payload)))

    if not saved and not skipped:
        return (
            f'ไม่เจอไฟล์แนบที่ชื่อมีคำว่า "{name}" ในเมลฉบับนี้ค่ะ'
            if want else "อีเมลฉบับนี้ไม่มีไฟล์แนบค่ะ"
        )
    out = []
    if saved:
        out.append("บันทึกแล้ว: " + ", ".join(f"{n} ({_human(sz)})" for n, sz in saved))
    if skipped:
        out.append("ข้ามไป: " + ", ".join(skipped))
    where = root + (("\\" + dest.strip().strip("/\\")) if (dest or "").strip() else "")
    out.append(f"อยู่ในโฟลเดอร์ {where}")
    return "\n".join(out)


def read_email(query: str, folder: str = "") -> str:
    """อ่านเนื้อหาเต็มของอีเมลหนึ่งฉบับ ใช้หลัง check_email/search_email แล้วผู้ใช้บอก "อ่านฉบับที่ 2" /
    "อ่านจากหัวหน้า" / "เปิดเมลที่ผมส่งหา X" — การอ่านจะมาร์คเมลนั้นว่าอ่านแล้ว

    Args:
        query: ลำดับจากลิสต์ล่าสุด (เช่น "2") หรือคำในผู้ส่ง/ผู้รับ/หัวข้อ (หรือรูปแบบ Gmail เช่น to:boss)
        folder: เว้นว่าง = กล่องเดียวกับที่เพิ่งแสดง (ถ้าอ้างด้วยลำดับ) หรือค้นทุกกล่อง (ถ้าอ้างด้วยคำ);
            ระบุ "sent"/"inbox"/"all"/... เพื่อเจาะจงกล่อง

    Returns:
        ผู้ส่ง + ผู้รับ + หัวข้อ + เนื้อหา (ตัดถ้ายาวเกิน)
    """
    cfg = _cfg()
    if not cfg:
        return _NOT_SET
    query = (query or "").strip()
    key = query.lstrip("#")
    by_index = key.isdigit() and bool(_last_uids) and not (folder or "").strip()
    if (folder or "").strip():
        kind = _canon_folder(folder)
    elif by_index:
        kind = _last_mailbox or "inbox"
    else:
        kind = "all" if _is_gmail(cfg) else "inbox"
    is_gmail = _is_gmail(cfg)
    try:
        m, _count, kind = _open(cfg, kind)
        try:
            seq = None
            if by_index and kind == (_last_mailbox or "inbox"):
                idx = int(key) - 1
                if 0 <= idx < len(_last_uids):
                    seq = _last_uids[idx]
            if seq is None and query:
                found = _search_seqs(m, query, is_gmail)
                if found:
                    seq = found[-1]
            if seq is None:
                return (
                    "ไม่แน่ใจว่าจะอ่านฉบับไหน ลองเช็คเมลก่อนแล้วบอกลำดับ "
                    "หรือบอกชื่อผู้ส่ง/ผู้รับ/หัวข้อค่ะ"
                )
            _t, data = m.fetch(seq, "(RFC822)")
            msg = message_from_bytes(data[0][1])
            body = _plain_body(msg)
            if len(body) > 4000:
                body = body[:4000] + "\n\n...(ตัดไว้แค่นี้ค่ะ)"
            atts = [f"{fn} ({_human(len(pl))})" for fn, pl in _iter_attachments(msg)]
            tail = (
                "\n\nไฟล์แนบ: " + ", ".join(atts) + '\n(บอก "ดาวน์โหลดไฟล์แนบ" ถ้าอยากเก็บลงเครื่อง)'
                if atts else ""
            )
            return (
                f"จาก: {_dec(msg.get('From'))}\n"
                f"ถึง: {_dec(msg.get('To')) or '-'}\n"
                f"หัวข้อ: {_dec(msg.get('Subject')) or '(ไม่มีหัวข้อ)'}\n"
                f"วันที่: {_dec(msg.get('Date'))}\n\n{body}{tail}"
            )
        finally:
            m.logout()
    except Exception as e:
        return f"อ่านเมลไม่สำเร็จค่ะ ({type(e).__name__})"


def _plain_body(msg) -> str:
    """ดึงเนื้อหา text/plain (ถ้าไม่มีก็ text/html แบบตัด tag หยาบๆ)"""
    html = None
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition") or "")
            if "attachment" in disp:
                continue
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            charset = part.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            if ctype == "text/plain":
                return text.strip()
            if ctype == "text/html" and html is None:
                html = text
    else:
        payload = msg.get_payload(decode=True)
        if payload is not None:
            text = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
            if msg.get_content_type() == "text/html":
                html = text
            else:
                return text.strip()
    if html:
        return re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style).*?</\1>", "", html)).strip()
    return "(ไม่มีเนื้อหาข้อความ)"


def _human(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.0f} KB"
    return f"{n / 1024 / 1024:.1f} MB"


def _iter_attachments(msg):
    """yield (ชื่อไฟล์ str, bytes) ของทุก part ที่เป็นไฟล์แนบ (มี filename หรือ Content-Disposition: attachment)"""
    for part in msg.walk():
        if part.is_multipart():
            continue
        fname = part.get_filename()
        disp = str(part.get("Content-Disposition") or "").lower()
        if not fname and "attachment" not in disp:
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        yield (_dec(fname) or "attachment.bin"), payload


def _pick_kind(query: str, folder: str, cfg) -> str:
    """กล่องที่ควร select เพื่อไปหาเมล 1 ฉบับตาม query (เหมือน logic ใน read_email)"""
    key = (query or "").strip().lstrip("#")
    if (folder or "").strip():
        return _canon_folder(folder)
    if key.isdigit() and _last_uids:
        return _last_mailbox or "inbox"
    return "all" if _is_gmail(cfg) else "inbox"


def _locate_seq(m, query: str, folder: str, is_gmail: bool):
    """คืน seq ของเมล 1 ฉบับ ตาม query (ลำดับจากลิสต์ล่าสุด หรือคำค้น) — ต้อง select กล่องไว้แล้ว"""
    key = (query or "").strip().lstrip("#")
    if key.isdigit() and _last_uids and not (folder or "").strip():
        idx = int(key) - 1
        if 0 <= idx < len(_last_uids):
            return _last_uids[idx]
    if (query or "").strip():
        found = _search_seqs(m, query, is_gmail)
        if found:
            return found[-1]
    return None


def _resolve_attachments(spec: str):
    """spec = "a.pdf, sub/b.png" (นับจากโฟลเดอร์ที่อนุญาต) -> (list[(basename, bytes, maintype, subtype)], list[str ข้อผิดพลาด])"""
    out, errs = [], []
    for raw in (spec or "").replace(";", ",").split(","):
        rel = raw.strip().strip("/\\")
        if not rel:
            continue
        if not files.get_allowed_folder():
            errs.append(f"{rel} (ยังไม่ได้ตั้งโฟลเดอร์ในเว็บ)")
            continue
        ok, tgt = files._resolve_safe_path(rel)
        if not ok or not os.path.isfile(tgt):
            errs.append(f"{rel} (หาไฟล์ไม่เจอ/นอกขอบเขต)")
            continue
        try:
            with open(tgt, "rb") as fh:
                blob = fh.read()
        except OSError:
            errs.append(f"{rel} (อ่านไฟล์ไม่ได้)")
            continue
        if len(blob) > _MAX_ATTACH_BYTES:
            errs.append(f"{rel} (ใหญ่เกิน 25MB)")
            continue
        ctype, _enc = mimetypes.guess_type(tgt)
        maintype, _, subtype = (ctype or "application/octet-stream").partition("/")
        out.append((os.path.basename(tgt), blob, maintype, subtype or "octet-stream"))
    return out, errs


def unread_count():
    """จำนวนเมลใหม่ในกล่องเข้า (int) หรือ None ถ้ายังไม่ตั้งค่า / ต่อไม่ได้ — ใช้ใน daily_briefing (ไม่ใช่ tool)"""
    cfg = _cfg()
    if not cfg:
        return None
    try:
        m, _c, _k = _open(cfg, "inbox")
        try:
            _t, data = m.search(None, "UNSEEN")
            return len(data[0].split()) if data and data[0] else 0
        finally:
            m.logout()
    except Exception:
        return None


# ร่างเมลที่ผ่านขั้น "พรีวิว" แล้วรอผู้ใช้ยืนยัน — send_email จะ "ส่งจริง" ได้ต่อเมื่อมีร่างนี้ค้างอยู่
# จากการเรียกครั้งก่อนเท่านั้น (บังคับให้ผ่านพรีวิว >=1 รอบเสมอ ต่อให้ LLM ยิง confirm=True มาแต่แรก)
_pending_send: dict | None = None
_PENDING_TTL = 600  # วินาที — ร่างเก่ากว่านี้ถือว่าหมดอายุ ต้องพรีวิวใหม่


def _norm_to(to: str) -> str:
    return ", ".join(sorted(a.strip() for a in (to or "").split(",") if a.strip()))


# ต่อท้ายทุกเมลที่ JUSMIN ส่ง (ผู้ใช้ขอ) — "ชื่อ" มาจาก EMAIL_SENDER_NAME ใน .env ถ้ามี ไม่งั้นใช้อีเมล
_SIG_MARKER = "J.U.S.M.I.N ผู้ช่วย AI ของคุณ"


def _signature(cfg) -> str:
    who = os.environ.get("EMAIL_SENDER_NAME", "").strip() or cfg["addr"]
    return f"\n\n—\nนี่คือการส่งอีเมลจาก {_SIG_MARKER}\n{who}"


def _with_signature(body: str, cfg) -> str:
    body = body or ""
    if _SIG_MARKER in body:  # LLM อาจ echo ลายเซ็นจากพรีวิวกลับมาในรอบ confirm — กันต่อซ้ำ
        return body
    return body.rstrip() + _signature(cfg)


def _send_preview(to: str, subject: str, body: str, att_line: str = "") -> str:
    b = (body or "").strip() or "(ไม่มีเนื้อหา)"
    return (
        "ขอทวนก่อนส่งนะคะ —\n"
        f"ถึง: {to}\n"
        f"หัวข้อ: {subject or '(ไม่มีหัวข้อ)'}\n"
        + (f"แนบไฟล์: {att_line}\n" if att_line else "")
        + f"เนื้อหา:\n{b}\n"
        "— จบเนื้อหา —\n\n"
        'ถ้าถูกต้องแล้วบอก "ยืนยันส่ง" ค่ะ ถ้าจะแก้บอกได้เลย'
    )


def send_email(to: str, subject: str, body: str, attachments: str = "", confirm: bool = False) -> str:
    """ส่งอีเมล — **ทำงานเป็น 2 ขั้นเสมอ เพื่อให้ผู้ใช้เห็นเนื้อหาจริงและยืนยันก่อนถึงจะส่ง**

    ขั้นที่ 1 (พรีวิว): เรียกด้วย confirm=False (หรือไม่ใส่) — ยัง "ไม่ส่ง" แต่คืนข้อความทวนผู้รับ/หัวข้อ/
      ไฟล์แนบ/เนื้อหาทั้งหมด ให้เอาข้อความนั้นไปแสดง/อ่านให้ผู้ใช้ฟังครบถ้วน
    ขั้นที่ 2 (ส่งจริง): เรียกอีกครั้งด้วย confirm=True และ to/subject/body/attachments "ชุดเดิมเป๊ะ"
      เฉพาะหลังผู้ใช้ตอบตกลงชัดเจน (เช่น "ยืนยันส่ง" / "ส่งเลย" / "ใช่ ส่งได้")
    ถ้าผู้ใช้ขอแก้อะไร ให้กลับไปขั้นที่ 1 ใหม่ด้วยข้อมูลที่แก้แล้ว — ห้ามข้ามไป confirm=True เอง

    หมายเหตุ: ระบบจะต่อท้ายเนื้อหาด้วยลายเซ็น "นี่คือการส่งอีเมลจาก J.U.S.M.I.N ..." ให้อัตโนมัติทุกฉบับ
    (ผู้ใช้กำหนดไว้) — ไม่ต้องเขียนลายเซ็นนี้เองใน body และพรีวิวจะแสดงลายเซ็นนั้นให้เห็นอยู่แล้ว

    Args:
        to: อีเมลผู้รับ (คั่นด้วย , ได้ถ้าหลายคน)
        subject: หัวข้อ
        body: เนื้อหา (เขียนแค่ส่วนของผู้ใช้ ไม่ต้องใส่ลายเซ็น)
        attachments: ไฟล์แนบ — path นับจากโฟลเดอร์ที่ผู้ใช้อนุญาต (ปุ่ม 📁) คั่นด้วย , ได้ เช่น
            "report.pdf" หรือ "งาน/สรุป.xlsx, รูป.png" (เว้นว่าง = ไม่แนบไฟล์)
        confirm: ใส่ True เฉพาะตอนยืนยันส่งจริงหลังผู้ใช้ตกลงแล้วเท่านั้น

    Returns:
        ขั้น 1 = ข้อความทวนให้ผู้ใช้ยืนยัน · ขั้น 2 = ผลการส่ง
    """
    global _pending_send
    cfg = _cfg()
    if not cfg:
        return _NOT_SET
    to_n = _norm_to(to)
    if "@" not in to_n:
        return f'ที่อยู่ผู้รับ "{to}" ดูไม่ถูกต้องค่ะ'
    subj_n = (subject or "").strip()
    body_n = _with_signature(body, cfg)  # ต่อท้ายลายเซ็น JUSMIN ก่อนพรีวิว/เทียบ/ส่ง — ผู้ใช้เห็นในพรีวิวด้วย
    att_key = tuple(sorted(
        x.strip().strip("/\\") for x in (attachments or "").replace(";", ",").split(",") if x.strip()
    ))

    resolved, aerrs = _resolve_attachments(attachments)
    if att_key:
        att_line = ", ".join(f"{n} ({_human(len(b))})" for n, b, _mt, _st in resolved)
        if aerrs:
            att_line = (att_line + ", " if att_line else "") + ", ".join(f"⚠️{e}" for e in aerrs)
    else:
        att_line = ""

    now = time.time()
    p = _pending_send
    if p and now - p["at"] > _PENDING_TTL:
        p = _pending_send = None
    same = (
        bool(p)
        and p["to"] == to_n
        and p["subject"] == subj_n
        and p["body"].strip() == body_n.strip()
        and p.get("att", ()) == att_key
    )

    # ยังไม่ยืนยัน / เนื้อหาไม่ตรงร่าง / ไฟล์แนบมีปัญหา → พรีวิว (ไม่ส่ง) + เก็บร่างใหม่
    if not confirm or not same or aerrs:
        if aerrs and confirm:
            note = "ไฟล์แนบยังมีปัญหา ส่งไม่ได้จนกว่าจะแก้ให้ครบนะคะ\n\n"
        elif confirm and p and not same:
            note = "ข้อมูลไม่ตรงกับที่ทวนไว้ ขอทวนใหม่อีกรอบนะคะ\n\n"
        else:
            note = ""
        _pending_send = {"to": to_n, "subject": subj_n, "body": body_n, "att": att_key, "at": now}
        return note + _send_preview(to_n, subj_n, body_n, att_line)

    # confirm=True และตรงกับร่างที่เพิ่งทวน → ส่งจริง
    em = EmailMessage()
    em["From"] = cfg["addr"]
    em["To"] = to_n
    em["Subject"] = subj_n or "(ไม่มีหัวข้อ)"
    em.set_content(body_n or "")
    for fn, blob, maintype, subtype in resolved:
        em.add_attachment(blob, maintype=maintype, subtype=subtype, filename=fn)
    try:
        with smtplib.SMTP(cfg["smtp"], cfg["port"], timeout=15) as s:
            s.starttls()
            s.login(cfg["addr"], cfg["pw"])
            s.send_message(em)
    except Exception as e:
        return f"ส่งเมลไม่สำเร็จค่ะ ({type(e).__name__}) — เช็ค EMAIL_APP_PASSWORD กับการเชื่อมต่อดูนะคะ"
    _pending_send = None
    for _relp in att_key:  # audit: ไฟล์ที่ออกจากเครื่องไปกับเมล
        files._log_activity("email_attach", _relp, True, f"sent to {to_n}")
    # Gmail เซฟลง Sent Mail ให้เองอัตโนมัติ; ที่อื่นต้อง APPEND เอง (best-effort ไม่ให้ล้มผลการส่ง)
    if not _is_gmail(cfg):
        try:
            mm = imaplib.IMAP4_SSL(cfg["imap"])
            mm.login(cfg["addr"], cfg["pw"])
            box = _resolve_mailbox(mm, "sent")
            mm.append(box, r"(\Seen)", imaplib.Time2Internaldate(time.time()), em.as_bytes())
            mm.logout()
        except Exception:
            pass
    extra = f" พร้อมไฟล์แนบ {len(resolved)} ไฟล์" if resolved else ""
    return f'ส่งเมลถึง {to_n} หัวข้อ "{em["Subject"]}"{extra} เรียบร้อยค่ะ'
