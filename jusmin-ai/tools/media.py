"""ค้น / ดาวน์โหลด / เปิดดู รูปและวิดีโอ

- search_media  : ddgs images/videos -> เก็บผลไว้ + สั่ง HUD โชว์ grid
- download_media: รูป = requests (sync) / วิดีโอ = yt-dlp ใน thread + notify.push ตอนเสร็จ
- view_media    : สั่ง HUD เปิด/ปิด/เลื่อน overlay เต็มจอ (ดูจากเว็บตรงๆ หรือไฟล์ที่โหลดมา)

ทุก path ที่เขียน/เปิดไฟล์ ผ่าน files._resolve_safe_path (จำกัดในโฟลเดอร์ที่ผู้ใช้อนุญาตเท่านั้น)
"""
import os
import shutil
import threading
import time
from urllib.parse import quote, urlparse

import requests
import yt_dlp
from ddgs import DDGS
from ddgs.exceptions import DDGSException

from . import _state, files, notify
from .web import _url_is_safe

_ddgs = DDGS()
_IMG_N = 12
_VID_N = 8

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
_MAX_IMG_BYTES = 60 * 1024 * 1024  # safety stop กัน disk เต็ม (ไม่ใช่ quality cap — วิดีโอไม่จำกัด)
_MAX_VIDEO_JOBS = 2


def _ffmpeg_path():
    """ffmpeg จำเป็นสำหรับต่อ video+audio ของ YouTube ยุคใหม่ (progressive ถูกถอดแล้ว) —
    ใช้ระบบถ้ามี ไม่งั้นใช้ binary ที่ imageio-ffmpeg บันเดิลมา (อยู่ใน requirements.txt)"""
    p = shutil.which("ffmpeg")
    if p:
        return p
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


_FFMPEG = _ffmpeg_path()

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".avif"}
_VIDEO_EXTS = {".mp4", ".webm", ".mkv", ".mov", ".m4v"}
_MEDIA_EXTS = _IMAGE_EXTS | _VIDEO_EXTS
_CT_EXT = {
    "image/jpeg": ".jpg", "image/jpg": ".jpg", "image/png": ".png", "image/webp": ".webp",
    "image/gif": ".gif", "image/bmp": ".bmp", "image/avif": ".avif", "image/x-icon": ".ico",
}
_VIDEO_HOSTS = ("youtube.com", "youtu.be", "vimeo.com", "tiktok.com", "dailymotion.com",
                "facebook.com", "fb.watch", "instagram.com", "twitter.com", "x.com")


def _fmt_dur(sec) -> str:
    try:
        sec = int(float(sec))
    except (TypeError, ValueError):
        return ""
    h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _yt_search_videos(query: str, n: int) -> list[dict]:
    """ค้นวิดีโอด้วย yt-dlp (ytsearch) — เชื่อถือได้กว่า ddgs.videos ที่ชอบคืน "No results" + yt-dlp
    โหลดคลิปได้จริงตอน download_media อยู่แล้ว. คืน dict รูปแบบเดียวกับ ddgs.videos ให้ _norm_video ใช้ต่อได้"""
    opts = {"quiet": True, "no_warnings": True, "extract_flat": True, "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"ytsearch{n}:{query}", download=False)
    out = []
    for e in info.get("entries") or []:
        if not e.get("id"):
            continue
        thumbs = e.get("thumbnails") or []
        thumb = (thumbs[-1].get("url") if thumbs else "") or e.get("thumbnail") or ""
        out.append({
            "title": e.get("title") or "(ไม่มีชื่อ)",
            "content": e.get("url") or f"https://www.youtube.com/watch?v={e['id']}",
            "images": {"large": thumb},
            "duration": _fmt_dur(e.get("duration")),
            "publisher": e.get("channel") or e.get("uploader") or "YouTube",
        })
    return out

# ผลค้นล่าสุด — download_media("#3") / view_media("#3") / คลิก grid / prev-next อ้างจากนี้
_last_results: list[dict] = []
_last_kind: str = ""

_IMAGE_WORDS = {"image", "images", "img", "pic", "picture", "photo", "photos",
                "รูป", "ภาพ", "รูปภาพ", "รูปถ่าย"}
_VIDEO_WORDS = {"video", "videos", "vid", "clip", "movie",
                "วิดีโอ", "วีดีโอ", "คลิป", "หนัง"}


def _norm_kind(kind: str) -> str:
    k = (kind or "").strip().lower()
    if k in _VIDEO_WORDS:
        return "video"
    return "video" if any(w in k for w in _VIDEO_WORDS) else "image"


def _host(url: str) -> str:
    try:
        h = urlparse(url).hostname or ""
        return h[4:] if h.startswith("www.") else h
    except Exception:
        return ""


def _norm_image(i: int, r: dict) -> dict:
    return {
        "n": i,
        "kind": "image",
        "title": (r.get("title") or "").strip() or "(ไม่มีชื่อ)",
        "thumb": r.get("thumbnail") or r.get("image") or "",
        "url": r.get("image") or "",
        "page": r.get("url") or "",
        "source": _host(r.get("url") or r.get("image") or ""),
    }


def _norm_video(i: int, r: dict) -> dict:
    imgs = r.get("images") or {}
    thumb = ""
    if isinstance(imgs, dict):
        thumb = imgs.get("large") or imgs.get("medium") or imgs.get("motion") or imgs.get("small") or ""
    return {
        "n": i,
        "kind": "video",
        "title": (r.get("title") or "").strip() or "(ไม่มีชื่อ)",
        "thumb": thumb,
        "url": r.get("content") or "",
        "page": r.get("content") or "",
        "source": (r.get("publisher") or r.get("uploader") or _host(r.get("content") or "")),
        "duration": r.get("duration") or "",
    }


def search_media(query: str, kind: str = "image") -> str:
    """ค้นรูปภาพหรือวิดีโอบนอินเทอร์เน็ต ใช้เมื่อผู้ใช้อยากหา/ดู/โหลดรูปหรือวิดีโอ
    ผลลัพธ์จะโชว์เป็นตารางรูปย่อในหน้าเว็บด้วย — ผู้ใช้สั่งต่อได้ เช่น "เปิดอันที่ 3" / "โหลดอันที่ 2"

    Args:
        query: สิ่งที่อยากหา
        kind: "image" (รูป, ค่าเริ่มต้น) หรือ "video" (วิดีโอ)

    Returns:
        รายการผลมีเลขกำกับ (ชื่อ + แหล่งที่มา) — จำนวนรูป ~12, วิดีโอ ~8
    """
    global _last_results, _last_kind
    q = (query or "").strip()
    if not q:
        return "จะให้ค้นรูป/วิดีโอเรื่องอะไรคะ"
    k = _norm_kind(kind)
    try:
        if k == "video":
            raw = _yt_search_videos(q, _VID_N)
            items = [_norm_video(i, r) for i, r in enumerate(raw, 1)]
        else:
            raw = []
            for attempt in range(2):  # ddgs.images ก็ hiccup ได้บ้าง ลองซ้ำหนึ่งครั้ง
                try:
                    raw = _ddgs.images(q, max_results=_IMG_N)
                    break
                except DDGSException:
                    if attempt == 0:
                        time.sleep(1.5)
                    else:
                        raise
            items = [_norm_image(i, r) for i, r in enumerate(raw, 1)]
    except DDGSException:
        return f'ค้นรูป "{q}" ไม่สำเร็จค่ะ (ระบบค้นหาอาจติดขัดชั่วคราว ลองใหม่อีกทีนะคะ)'
    except Exception:
        return f'ค้น{"วิดีโอ" if k == "video" else "รูป"}ไม่สำเร็จค่ะ ลองใหม่อีกทีนะคะ'

    items = [it for it in items if it["url"]]
    if not items:
        return f'ไม่เจอ{"วิดีโอ" if k == "video" else "รูป"}สำหรับ "{q}" ค่ะ'

    _last_results = items
    _last_kind = k
    _viewer_list.clear()  # ค้นใหม่ = context ใหม่ -> "เล่นสไลด์"/"เปิด" (ไม่ระบุ) จะอิงผลค้นชุดนี้
    _state.pending_action = {
        "type": "show_media_results",
        "kind": k,
        "query": q,
        "items": items,
    }
    label = "วิดีโอ" if k == "video" else "รูป"
    lines = []
    for it in items:
        extra = f" · {it['duration']}" if it.get("duration") else ""
        src = f" ({it['source']})" if it["source"] else ""
        lines.append(f"{it['n']}. {it['title']}{src}{extra}")
    return f"เจอ {len(items)} {label} (โชว์เป็นตารางในหน้าเว็บแล้ว):\n" + "\n".join(lines)


# ---------- viewer state (แชร์ระหว่าง view_media / download_media auto-open) ----------
_viewer_list: list[dict] = []
_viewer_index: int = 0
_video_jobs: set[str] = set()


def _rel_to_root(abspath: str) -> str:
    try:
        return os.path.relpath(abspath, os.path.realpath(files.get_allowed_folder())).replace("\\", "/")
    except (ValueError, TypeError):
        return os.path.basename(abspath)


def _local_item(rel: str) -> dict:
    rel = rel.replace("\\", "/")
    ext = os.path.splitext(rel)[1].lower()
    return {
        "src": "/api/media?path=" + quote(rel),
        "kind": "video" if ext in _VIDEO_EXTS else "image",
        "name": os.path.basename(rel),
        "source": "",
        "page": "",
    }


def _remote_item(r: dict) -> dict:
    return {
        "src": r["url"],
        "kind": r["kind"],
        "name": r["title"],
        "source": r.get("source", ""),
        "page": r.get("page", ""),
        "ref": r.get("n"),  # ref = ลำดับใน _last_results -> ปุ่ม "⬇ ดาวน์โหลด" ใน viewer โผล่เฉพาะกรณีนี้
    }


def _show_viewer(items: list[dict], index: int, slideshow: int = 0) -> None:
    """ส่ง gallery ทั้งชุด + index ไปให้ HUD ทีเดียว -> เลื่อน prev/next ในเบราว์เซอร์ได้ทันทีไม่ต้อง round-trip
    slideshow > 0 = ให้ HUD เลื่อนอัตโนมัติทุก N วินาที วนไปเรื่อยๆ (0 = ปิดสไลด์/ดูปกติ)"""
    global _viewer_list, _viewer_index
    _viewer_list = items or []
    if not _viewer_list:
        _state.pending_action = {"type": "hide_media"}
        return
    _viewer_index = index % len(_viewer_list)
    _state.pending_action = {
        "type": "show_media",
        "index": _viewer_index,
        "list": _viewer_list,
        "slideshow": max(0, int(slideshow)),
    }


def _local_gallery(rel: str):
    """rel -> (list ของ _local_item, error). ถ้า rel ชี้โฟลเดอร์ = รวมรูป/วิดีโอทั้งหมดในนั้น (เรียงชื่อ)"""
    if not files.get_allowed_folder():
        return None, "ยังไม่ได้ตั้งค่าโฟลเดอร์ที่อนุญาตค่ะ"
    ok, tgt = files._resolve_safe_path(rel)
    if not ok:
        return None, f'"{rel}" อยู่นอกขอบเขตที่อนุญาตค่ะ'
    if os.path.isfile(tgt):
        if os.path.splitext(tgt)[1].lower() not in _MEDIA_EXTS:
            return None, "ไฟล์นี้ไม่ใช่รูป/วิดีโอที่เปิดดูได้ค่ะ"
        return [_local_item(rel)], ""
    if os.path.isdir(tgt):
        base = rel.replace("\\", "/").strip("/")
        items = []
        for name in sorted(os.listdir(tgt)):
            if os.path.splitext(name)[1].lower() in _MEDIA_EXTS and os.path.isfile(os.path.join(tgt, name)):
                items.append(_local_item(f"{base}/{name}" if base else name))
        return (items, "") if items else (None, f'ในโฟลเดอร์ "{rel}" ไม่มีรูป/วิดีโอค่ะ')
    return None, f'ไม่พบ "{rel}" ค่ะ'


# ---------- download ----------
def _sniff_kind(url: str) -> str:
    host = _host(url).lower()
    if any(h in host for h in _VIDEO_HOSTS):
        return "video"
    ext = os.path.splitext(urlparse(url).path)[1].lower()
    if ext in _VIDEO_EXTS:
        return "video"
    return "image"  # ที่เหลือลองเป็นรูป (จะเช็ค Content-Type อีกที)


def _resolve_refs(ref: str) -> list[dict]:
    """ref -> list ของ {url, kind, title} — '#3' / '3' / '#1,#3' / 'all' / 'current' / URL เต็ม"""
    ref = (ref or "").strip()
    if not ref:
        return []
    if ref.lower() in ("all", "ทั้งหมด", "หมด"):
        return [{"url": r["url"], "kind": r["kind"], "title": r["title"]} for r in _last_results if r["url"]]
    if ref.lower() == "current":
        if _viewer_list:
            c = _viewer_list[_viewer_index]
            return [{"url": c.get("page") or c["src"], "kind": c["kind"], "title": c.get("name", "media")}]
        return []
    out = []
    for tok in ref.replace(";", ",").split(","):
        t = tok.strip().lstrip("#").strip()
        if not t:
            continue
        if t.isdigit():
            i = int(t) - 1
            if 0 <= i < len(_last_results):
                r = _last_results[i]
                out.append({"url": r["url"], "kind": r["kind"], "title": r["title"]})
        elif t.startswith("http://") or t.startswith("https://"):
            out.append({"url": t, "kind": _sniff_kind(t), "title": os.path.basename(urlparse(t).path) or "media"})
    return out


def _download_image(url: str, target_dir: str, title: str):
    ok, msg = _url_is_safe(url)
    if not ok:
        return None, msg
    try:
        r = requests.get(url, stream=True, timeout=15, headers={"User-Agent": _UA})
        r.raise_for_status()
    except Exception as e:
        return None, f"โหลดไม่ได้ ({type(e).__name__})"
    ct = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
    if not ct.startswith("image/"):
        return None, f"ไม่ใช่รูปภาพ (Content-Type: {ct or 'ไม่ทราบ'})"
    ext = _CT_EXT.get(ct) or os.path.splitext(urlparse(url).path)[1].lower() or ".jpg"
    if ext not in _IMAGE_EXTS:
        ext = ".jpg"
    base = os.path.splitext(files._safe_name(title or os.path.basename(urlparse(url).path) or "image"))[0][:80]
    tgt = files._uniq(os.path.join(target_dir, (base or "image") + ext))
    total = 0
    try:
        with open(tgt, "wb") as f:
            for chunk in r.iter_content(65536):
                total += len(chunk)
                if total > _MAX_IMG_BYTES:
                    f.close()
                    os.remove(tgt)
                    return None, "ไฟล์ใหญ่เกิน 60MB"
                f.write(chunk)
    except OSError:
        return None, "เขียนไฟล์ไม่ได้"
    return tgt, ""


def _download_video_async(url: str, target_dir: str, title: str) -> str:
    if len(_video_jobs) >= _MAX_VIDEO_JOBS:
        return f"กำลังโหลดวิดีโออยู่ {_MAX_VIDEO_JOBS} อันแล้วค่ะ รอให้เสร็จก่อนนะคะ"
    ok, msg = _url_is_safe(url)
    if not ok:
        return f"'{title[:40]}': {msg}"
    _video_jobs.add(url)

    def _work():
        try:
            opts = {
                "outtmpl": os.path.join(target_dir, "%(title).180s [%(id)s].%(ext)s"),
                "noplaylist": True, "quiet": True, "no_warnings": True, "noprogress": True,
            }
            if _FFMPEG:
                opts["format"] = "bestvideo*+bestaudio/best"
                opts["merge_output_format"] = "mp4"
                opts["ffmpeg_location"] = _FFMPEG
            else:
                opts["format"] = "best[acodec!=none][vcodec!=none]/best"
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            notify.push(f"โหลดวิดีโอ '{title}' เสร็จแล้วค่ะ เก็บไว้ในโฟลเดอร์ที่เลือกไว้", "media")
            files._log_activity("download_media", title[:80], True, "video")
        except Exception as e:
            notify.push(f"โหลดวิดีโอ '{title}' ไม่สำเร็จค่ะ ({type(e).__name__})", "media")
            files._log_activity("download_media", title[:80], False, f"video {type(e).__name__}")
        finally:
            _video_jobs.discard(url)

    threading.Thread(target=_work, daemon=True, name="jusmin-vdl").start()
    return f"กำลังโหลดวิดีโอ '{title}' อยู่ค่ะ เดี๋ยวบอกตอนเสร็จ"


def download_media(ref: str, dest: str = "") -> str:
    """ดาวน์โหลดรูปหรือวิดีโอมาเก็บในโฟลเดอร์ที่ผู้ใช้อนุญาต (ปุ่ม 📁) ใช้หลัง search_media หรือเมื่อผู้ใช้
    ส่งลิงก์มา — รูปโหลดเสร็จทันทีและเปิดให้ดูเลย, วิดีโอโหลดอยู่เบื้องหลังแล้วจะบอกตอนเสร็จ

    Args:
        ref: จะโหลดอันไหน — ลำดับจากผลค้นล่าสุด ("3" หรือ "#3"), หลายอัน ("1,3,5"), "all" (ทั้งหมด),
            "current" (อันที่เปิดดูอยู่), หรือ URL รูป/วิดีโอเต็มๆ
        dest: โฟลเดอร์ย่อยปลายทางนับจากโฟลเดอร์ที่อนุญาต — เลือกให้เหมาะกับเนื้อหา เช่น "รูป/ดาวหาง",
            "คลิป" (เว้นว่าง = เก็บที่โฟลเดอร์หลักเลย)

    Returns:
        สรุปว่าบันทึกอะไรไปบ้าง + ที่อยู่
    """
    if not files.get_allowed_folder():
        return "ยังไม่ได้ตั้งค่าโฟลเดอร์ที่อนุญาตเลยค่ะ กดปุ่ม 📁 เลือกโฟลเดอร์ มุมขวาบนของหน้าเว็บก่อนนะคะ"
    dest = (dest or "").strip().strip("/\\")
    ok, target_dir = files._resolve_safe_path(dest)
    if not ok:
        return "โฟลเดอร์ปลายทางอยู่นอกขอบเขตที่อนุญาตค่ะ"
    try:
        os.makedirs(target_dir, exist_ok=True)
    except OSError:
        return "สร้างโฟลเดอร์ปลายทางไม่ได้ค่ะ"

    refs = _resolve_refs(ref)
    if not refs:
        return ("ไม่แน่ใจว่าจะโหลดอันไหน ลองค้นรูป/วิดีโอก่อนแล้วบอกลำดับ (เช่น \"โหลดอันที่ 2\") "
                "หรือส่งลิงก์มาก็ได้ค่ะ")

    saved, vids, errs = [], [], []
    for it in refs:
        if it["kind"] == "video":
            vids.append(_download_video_async(it["url"], target_dir, it["title"]))
        else:
            tgt, err = _download_image(it["url"], target_dir, it["title"])
            if tgt:
                rel = _rel_to_root(tgt)
                files._log_activity("download_media", rel, True, "image")
                saved.append(rel)
            else:
                errs.append(f"{it['title'][:36]}: {err}")
                files._log_activity("download_media", it["title"][:60], False, err)

    if saved:  # เปิด viewer ให้ดูรูปที่โหลดได้เลย
        _show_viewer([_local_item(r) for r in saved], 0)

    parts = []
    if saved:
        parts.append(f"บันทึกรูป {len(saved)} ไฟล์: " + ", ".join(os.path.basename(r) for r in saved))
    if vids:
        parts.append(" · ".join(vids))
    if errs:
        parts.append("ไม่สำเร็จ: " + " ; ".join(errs))
    if saved:
        where = os.path.realpath(files.get_allowed_folder()) + (("\\" + dest.replace("/", "\\")) if dest else "")
        parts.append(f"อยู่ที่ {where} — เปิดให้ดูแล้วค่ะ")
    return "\n".join(parts) if parts else "ไม่มีอะไรถูกบันทึกค่ะ"


_SLIDE_WORDS = ("slideshow", "slide", "สไลด์", "สไลด์โชว์", "สไลด์รูป", "วนรูป", "เล่นสไลด์", "play")
_STOP_WORDS = ("stop", "หยุด", "หยุดสไลด์", "pause", "พอ")


def view_media(target: str = "", action: str = "open", seconds: int = 0) -> str:
    """เปิด/ปิด/เลื่อน/เล่นสไลด์ หน้าต่างดูรูป-วิดีโอเต็มจอในหน้าเว็บ
    ใช้เมื่อผู้ใช้บอก "เปิดรูปที่ 3" / "ปิดรูป" / "รูปถัดไป" / "เล่นสไลด์รูปช้าๆ วนไปเรื่อยๆ" / "หยุดสไลด์"

    Args:
        target: จะเปิด/เล่นสไลด์อะไร — ลำดับจากผลค้นล่าสุด ("3"/"#3" = จากเว็บเลยไม่ต้องโหลด),
            path ไฟล์ ("รูป/ดาวหาง/x.jpg") หรือ "ทั้งโฟลเดอร์" ("รูป/ดาวหาง" = เอารูป/วิดีโอทุกไฟล์ในนั้น),
            "current" (อันที่เปิดอยู่), หรือเว้นว่าง = ผลค้น/แกลเลอรีล่าสุดทั้งชุด
        action: "open" (ค่าเริ่มต้น) / "close" (ปิด viewer + ตารางผลค้น) / "next" / "prev" /
            "slideshow" (เล่นสไลด์อัตโนมัติวนไปเรื่อยๆ) / "stop" (หยุดสไลด์ แต่ยังดูรูปค้างอยู่)
        seconds: ช่วงเปลี่ยนรูปตอนเล่นสไลด์ (วินาที) — เว้น/0 = 6 วิ ("ช้าๆ" ใส่ 8-10)

    Returns:
        ข้อความยืนยันสั้นๆ
    """
    global _viewer_index
    act = (action or "open").strip().lower()

    if act in ("close", "ปิด", "hide"):
        _state.pending_action = {"type": "hide_media"}
        return "ปิดหน้าต่างดูรูปแล้วค่ะ"

    if act in _STOP_WORDS:
        if not _viewer_list:
            return "ไม่มีสไลด์ที่เล่นอยู่ค่ะ"
        _show_viewer(_viewer_list, _viewer_index, slideshow=0)
        return "หยุดสไลด์แล้วค่ะ (ยังดูรูปนี้ค้างอยู่)"

    if act in ("next", "ถัดไป", "prev", "previous", "ก่อนหน้า", "back"):
        if not _viewer_list:
            return "ยังไม่มีรูป/วิดีโอเปิดอยู่ค่ะ"
        step = 1 if act in ("next", "ถัดไป") else -1
        _show_viewer(_viewer_list, _viewer_index + step)
        cur = _viewer_list[_viewer_index]
        return f"{cur.get('name', '')} ({_viewer_index + 1}/{len(_viewer_list)})"

    slide = (seconds if (seconds and seconds > 0) else 6) if act in _SLIDE_WORDS else 0
    t = (target or "").strip()

    if t == "" or t.lower() in ("current", "ปัจจุบัน"):
        if _viewer_list:
            gallery, start = _viewer_list, _viewer_index
        elif _last_results:
            gallery, start = [_remote_item(r) for r in _last_results], 0
        else:
            return "ยังไม่มีรูป/วิดีโอให้เปิดค่ะ ลองค้นก่อนนะคะ"
    elif t.lstrip("#").strip().isdigit():
        i = int(t.lstrip("#").strip()) - 1
        if not (0 <= i < len(_last_results)):
            return f"ไม่มีอันที่ {t} ในผลค้นล่าสุดค่ะ"
        gallery, start = [_remote_item(r) for r in _last_results], i
    else:
        gallery, err = _local_gallery(t)
        if err:
            return err
        start = 0

    _show_viewer(gallery, start, slideshow=slide)
    if slide:
        return (f"เริ่มเล่นสไลด์แล้วค่ะ ({len(gallery)} รายการ เปลี่ยนทุก {slide} วิ วนไปเรื่อยๆ "
                f"บอก 'หยุด' เพื่อหยุด)")
    if len(gallery) > 1:
        return f"เปิดให้ดูแล้วค่ะ ({start + 1}/{len(gallery)} — ใช้ 'ถัดไป'/'ก่อนหน้า' เลื่อนได้)"
    return f"เปิด {gallery[0].get('name', '')} ให้ดูแล้วค่ะ"
