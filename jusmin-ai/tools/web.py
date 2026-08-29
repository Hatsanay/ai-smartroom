import ipaddress
import socket
from urllib.parse import quote, urlparse, urlsplit, urlunsplit

import trafilatura
from ddgs import DDGS
from ddgs.exceptions import DDGSException
from trafilatura.settings import use_config as _tf_use_config

# สร้างครั้งเดียวใช้ซ้ำทุก request แทนสร้างใหม่ทุกครั้งที่ค้น (server เป็น process เดียวรันยาว)
_ddgs = DDGS()

_MAX_URL_CHARS = 8000  # ตัดเนื้อหาหน้าเว็บกันบวม context ของ Gemini
_URL_TIMEOUT_S = 10  # กัน chat turn ค้างเพราะเว็บช้า (default ของ trafilatura คือ 30)

_tf_cfg = _tf_use_config()
_tf_cfg.set("DEFAULT", "DOWNLOAD_TIMEOUT", str(_URL_TIMEOUT_S))


def search_web(query: str) -> str:
    """ค้นหาข้อมูลบนอินเทอร์เน็ตแบบเรียลไทม์ ใช้เมื่อ user ถามเรื่องที่ต้องการข้อมูลล่าสุด
    เช่น ข่าว ราคาสินค้า สภาพอากาศ หรือเรื่องที่ไม่แน่ใจว่าข้อมูลในตัวเองยังทันสมัยอยู่ไหม

    Args:
        query: คำค้นหา ภาษาไทยหรืออังกฤษก็ได้

    Returns:
        สรุปผลการค้นหา 5 อันดับแรก (หัวข้อ, เนื้อหาย่อ, ลิงก์)
    """
    try:
        results = _ddgs.text(query, max_results=5)
    except DDGSException:
        # ddgs (ตั้งแต่รุ่นที่ใช้อยู่) ยิง exception ตอนไม่เจอผลลัพธ์/โดน rate-limit/timeout แทนที่จะคืน
        # list ว่างเหมือนที่โค้ดเดิมคาดไว้ — เจอจริงตอนทดสอบ (DDGSException: No results found.)
        # ไม่ครอบ try/except ไว้ตรงนี้ = Gemini function calling เจอ exception ดิบ ตอบลูกค้าแบบกำกวม
        return "ไม่พบผลการค้นหาสำหรับคำนี้ค่ะ (หรือระบบค้นหาอาจติดขัดชั่วคราว)"

    if not results:
        return "ไม่พบผลการค้นหาสำหรับคำนี้"

    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}\n   {r['body']}\n   {r['href']}")
    return "\n".join(lines)


def _normalize_url(url: str) -> str:
    """percent-encode path/query ที่มีอักขระ non-ASCII (URL ภาษาไทยที่ paste มาดิบ) + IDNA hostname + ตัด fragment
    (% อยู่ใน safe ด้วย เลยไม่ double-encode ลิงก์ที่ encode มาแล้ว)"""
    try:
        p = urlsplit(url)
        host = (p.hostname or "").encode("idna").decode("ascii") if p.hostname else ""
        netloc = host + (f":{p.port}" if p.port else "")
        if p.username:
            netloc = p.username + (f":{p.password}" if p.password else "") + "@" + netloc
        path = quote(p.path, safe="/%:@!$&'()*+,;=~-._")
        query = quote(p.query, safe="=&/%:@!$'()*+,;~-._")
        return urlunsplit((p.scheme, netloc, path, query, ""))
    except Exception:
        return url


def _url_is_safe(url: str) -> tuple[bool, str]:
    """ต้องเป็น http/https + hostname ที่ resolve แล้วไม่ตกไป private/loopback/link-local/reserved
    กัน LLM ชี้ url ไป 127.0.0.1:8000 (server ตัวเอง) / 169.254.169.254 (cloud metadata) / IP ในวง LAN — SSRF
    หมายเหตุ: ยังมีช่อง TOCTOU + redirect ตาม (trafilatura ไม่เปิดให้ปิด redirect) — พอสำหรับใช้ส่วนตัวในบ้าน"""
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        return False, "ใส่ลิงก์ที่ขึ้นต้นด้วย http:// หรือ https:// นะคะ"
    try:
        infos = socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == "https" else 80))
    except socket.gaierror:
        return False, f'เปิดลิงก์ไม่ได้ค่ะ หาที่อยู่ของ "{p.hostname}" ไม่เจอ'
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return False, "ลิงก์นี้ชี้ไปที่อยู่ภายในเครือข่าย เปิดให้ไม่ได้ค่ะ"
    return True, ""


def read_url(url: str) -> str:
    """อ่านเนื้อหาหลักของหน้าเว็บจาก URL (บทความ/ข่าว/บล็อก) ใช้เมื่อผู้ใช้ให้ลิงก์มาแล้วขอให้
    อ่าน / สรุป / ตอบคำถามจากหน้านั้น — ดึงเฉพาะเนื้อหาหลัก ตัดเมนู/โฆษณา/คอมเมนต์ออก

    Args:
        url: ลิงก์เต็ม (ขึ้นต้น http:// หรือ https://)

    Returns:
        หัวข้อ + เนื้อหาหลัก (ตัดถ้ายาวเกิน) หรือข้อความบอกว่าอ่านไม่ได้
    """
    url = _normalize_url((url or "").strip())
    ok, msg = _url_is_safe(url)
    if not ok:
        return msg

    try:
        html = trafilatura.fetch_url(url, config=_tf_cfg)
    except Exception:
        html = None
    if not html:
        return "โหลดหน้าเว็บนี้ไม่สำเร็จค่ะ (เข้าไม่ได้ / ช้าเกินไป / ต้องล็อกอิน)"

    text = trafilatura.extract(
        html, include_comments=False, include_tables=True, favor_precision=True
    )
    if not text or not text.strip():
        return "ดึงเนื้อหาจากหน้านี้ไม่ได้ค่ะ (อาจเป็นหน้าที่ต้องรัน JavaScript หรือไม่มีบทความ)"

    title = ""
    try:
        meta = trafilatura.extract_metadata(html)
        if meta and getattr(meta, "title", None):
            title = meta.title.strip()
    except Exception:
        pass

    text = text.strip()
    if len(text) > _MAX_URL_CHARS:
        text = text[:_MAX_URL_CHARS] + "\n\n...(ตัดไว้แค่นี้ค่ะ)"
    return (f"หัวข้อ: {title}\n\n" if title else "") + text
