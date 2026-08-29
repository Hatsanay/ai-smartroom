# Plan 02 — ค้น / ดาวน์โหลด / เปิดดู รูปและวิดีโอ

> Phase 1 · แทรกก่อน Tier 1 #2 (Telegram) · [ROADMAP.md](../../ROADMAP.md) ข้อ 1.5
> **สถานะ: CODE-COMPLETE บน branch `phase1-tier1` (ยังไม่ commit) — รอ user เทสเบราว์เซอร์**
> เป้าคุณภาพ (ผู้ใช้สั่ง 2026-08-29): สวย · ยืดหยุ่น · ครอบคลุม
>
> เปลี่ยนจากแผนเดิม: video search ใช้ `yt-dlp ytsearch` (ddgs.videos คืน No results ตลอด) · เพิ่ม dep `imageio-ffmpeg`
> (yt-dlp ต้องมี ffmpeg ต่อ video+audio) · `_show_viewer` ส่ง gallery ทั้งชุด (`list`+`index`) ให้ client เลื่อนเองได้ทันที

**ผู้ใช้ขอ:** จัสมิน ค้นรูป/วิดีโอบนเว็บ → ดาวน์โหลดเก็บ → เปิดดูในหน้าเว็บ (ทั้งที่โหลดมาและจากผลค้นตรงๆ) → ปิดได้

**ตัดสินใจ (ถาม user):**
- เซฟที่ไหน: **จัสมิน เลือกโฟลเดอร์ย่อยเองต่อครั้ง** (`dest` free-form, ว่าง = root) — บังคับ containment ในโฟลเดอร์ที่อนุญาตเสมอ
- cap วิดีโอ: **ไม่จำกัด** คุณภาพ/ขนาด
- viewer: **overlay เต็มจอ** — ✕ / Esc / คลิกพื้นหลัง ปิด

chat tools: 26 → 29 · dep เดิมทั้งหมด (`ddgs` / `requests` / `yt-dlp`)

---

## ยืดหยุ่น + ครอบคลุม (สิ่งที่ต้องรองรับ)

| แกน | ครอบคลุม |
|---|---|
| ค้น | รูป · วิดีโอ |
| เปิดดู — จากเว็บตรงๆ (ไม่ต้องโหลด) | รูป · วิดีโอ (เบราว์เซอร์โหลด URL เอง) |
| เปิดดู — ไฟล์ที่โหลดมาแล้ว | รูป · วิดีโอ (ผ่าน `/api/media` + Range) |
| โหลด | รูป (sync) · วิดีโอ (async + notify) · **หลายอันพร้อมกัน** (`#1,#3` / `all`) |
| ใน viewer | เลื่อน prev/next ทั้ง gallery · ← → คีย์บอร์ด · ปุ่ม ⬇ โหลดอันที่กำลังดู · zoom รูป (คลิกสลับ 1x/2x) |
| ปิด | ✕ · Esc · คลิก backdrop · `view_media(action="close")` |
| อ้างอิงสิ่งที่จะทำ | `#N` (จากผลค้นล่าสุด) · `#1,#3` · `all` · URL เต็ม · `"current"` (อันที่เปิดอยู่ใน viewer) |

---

## Tools — `tools/media.py` (ไฟล์ใหม่)

### `search_media(query, kind="image")`  ✅ Step 1 done
- `kind="image"` → `ddgs.images(query, max_results=_IMG_N=12)` (retry 1 ครั้งถ้า hiccup)
- `kind="video"` → **`yt-dlp ytsearch{_VID_N=8}:{query}` (`_yt_search_videos`)** — เปลี่ยนจาก `ddgs.videos` ที่ทดสอบแล้วคืน `DDGSException: No results found.` ตลอด · yt-dlp เชื่อถือได้กว่า + โหลดคลิปได้จริงตอน `download_media` อยู่แล้ว · YouTube-only (พอ) · คืน dict รูปแบบเดียวกับ ddgs.videos ให้ `_norm_video` ใช้ต่อ
- normalize → `{n, title, thumb, url, kind, source, duration?}` (image: thumb=thumbnail, url=image, source=จาก url host · video: thumb=images.large/medium, url=content, duration, source=publisher)
- เก็บ `_last_results` + `_last_kind` (module-level) → `download_media` / `view_media` / คลิก grid / prev-next อ้างได้
- `_state.pending_action = {"type": "show_media_results", "kind", "query", "items": [...]}` → HUD grid
- return: "เจอ N \<รูป/วิดีโอ\>: 1. \<title\> (\<source\>) …" (จัสมิน เล่าให้ผู้ใช้ + ผู้ใช้สั่งต่อ)
- `DDGSException` / ว่าง → string graceful (เหมือน `search_web`)

### `download_media(ref, dest="")`
- `ref`: `"#N"` · `"#1,#3,#5"` · `"all"` · URL เต็ม · `"current"` (อันที่เปิดใน viewer — client แนบ index มาใน request ถัดไป? → ง่ายกว่า: `"current"` = ใช้ `_viewer_index` ที่ `view_media` เก็บไว้)
- resolve เป็นรายการ `(url, kind, title)` — `#N`/`all` จาก `_last_results` · URL → เดา kind (host youtube/vimeo/tiktok/fb/ig หรือ yt-dlp รับได้ → video · ext / content-type `image/*` → image)
- `dest` = โฟลเดอร์ย่อยนับจากโฟลเดอร์ที่อนุญาต (จัสมิน เลือกให้เหมาะกับเนื้อหา เช่น `"รูป/แมว"`, `"คลิป"`) · ว่าง = root
  - `files._resolve_safe_path(dest)` → ไม่ผ่าน = ปฏิเสธ · `os.makedirs(target_dir, exist_ok=True)`
- ชื่อไฟล์: basename ของ URL / title → `files._safe_name()` + `files._uniq()` *(ย้าย 2 helper จาก `mail.py` → `files.py` ใช้ร่วม)*
- **รูป (sync):**
  - `web._url_is_safe(url)` (SSRF guard, reuse)
  - `requests.get(url, stream=True, timeout=15, headers={"User-Agent": _UA})` · `Content-Type` ต้อง `image/*` · ext จาก content-type
  - stream ลงไฟล์ · **soft-ceiling ~60MB** (เกิน → abort + ลบไฟล์ค้าง; safety stop กัน disk เต็ม)
  - `files._log_activity("download_media", relpath, ok, detail)` · เสร็จ → ถ้าโหลด**อันเดียว** ตั้ง `_state.pending_action = {"type":"show_media", ...}` เปิดให้ดูเลย
- **วิดีโอ (async — thread + notify):**
  - `web._url_is_safe(url)` · `threading.Thread(daemon=True)`:
    `yt_dlp.YoutubeDL({"outtmpl": <target_dir>/%(title).200s.%(ext)s, "noplaylist": True, "quiet": True, "no_warnings": True}).download([url])`
  - เสร็จ → `notify.push(f"โหลดวิดีโอ '{title}' เสร็จแล้ว เก็บที่ {relpath}", "media")` (→ `notify.js` พูด) · error → `notify.push("โหลดวิดีโอ … ไม่สำเร็จค่ะ")`
  - in-flight set (module-level) จำกัด **2 อันพร้อมกัน** (เกิน → เข้าคิว / ตอบ "ต่อคิวไว้ให้แล้ว")
  - return ทันที "กำลังโหลดวิดีโอ '\<title\>' … เดี๋ยวบอกตอนเสร็จ"
- batch: ตอบสรุป "โหลดรูป 3 / วิดีโอ 1 (วิดีโอกำลังโหลด)"

### `view_media(target="", action="open", seconds=0)`
- `action`:
  - `"open"` — `target` = local path · **ชื่อโฟลเดอร์** (รูป/วิดีโอทุกไฟล์) · `"#N"` (เปิดผลค้นจากเว็บตรงๆ) · ว่าง = ผลค้น/viewer ล่าสุด · `"current"`
  - `"close"` (ปิด viewer + grid) · `"next"` · `"prev"`
  - **`"slideshow"`** — เล่นสไลด์อัตโนมัติวนไปเรื่อยๆ (`seconds` = ช่วงเปลี่ยน, default 6, "ช้าๆ" = 8-10) · **`"stop"`** — หยุดสไลด์ ยังดูค้างอยู่
  - slideshow เล่นฝั่ง client (`setInterval` + wrap modulo) · เลื่อนเอง = รีเซ็ตนาฬิกา เล่นต่อ · `search_media` เคลียร์ `_viewer_list` → สไลด์หลังค้น = อิงผลค้นชุดใหม่
- local path → `files._resolve_safe_path` + ext ∈ whitelist → `src = "/api/media?path=" + quote(path)`
- `#N` / result → `src` = URL เว็บตรงๆ (image/video)
- เก็บ `_viewer_list` + `_viewer_index` (module scope) ให้ next/prev + `"current"` ทำงาน
- `_state.pending_action = {"type":"show_media" | "hide_media", "kind", "src", "name", "pos": "i/n", "source"}`
- return confirmation สั้นๆ

---

## Endpoint — `server.py`

```python
@app.get("/api/media")
def media_endpoint(path: str):
    ok, target = tools.files._resolve_safe_path(path)   # containment — ห้ามเชื่อ query param
    if not ok or not os.path.isfile(target):
        raise HTTPException(status_code=404)
    if os.path.splitext(target)[1].lower() not in _MEDIA_EXTS:
        raise HTTPException(status_code=415)
    return FileResponse(target)   # FileResponse รองรับ Range เอง → <video> seek ได้
```
- `_MEDIA_EXTS` = รูป `.png .jpg .jpeg .webp .gif .bmp .avif` + วิดีโอ `.mp4 .webm .mkv .mov .m4v`
- ไม่มี auth (personal use / localhost เหมือน endpoint อื่น)

---

## HUD — `static/` (เป้า: สวย เข้าธีม HUD, ลื่น)

**`js/media.js` (ใหม่):**
- `showMediaResults(data)` — สร้าง `#mediaGrid` จาก `data.items`:
  - responsive grid · แต่ละ tile = thumbnail + เลข badge + title ตัดสั้น + ไอคอน ▶ ถ้าเป็นวิดีโอ + duration
  - skeleton shimmer จนรูป thumb โหลดเสร็จ · `onerror` → tile "ดูตัวอย่างไม่ได้"
  - hover → ยกเด้งเล็กน้อย · คลิก → `openViewer(list, i)`
  - พาเนล spring-in (`cubic-bezier(0.34,1.56,0.64,1)`) เหมือน weather panel
- `showMedia(data)` / `openViewer(list, i)` — `#mediaViewer` overlay:
  - backdrop ดำเบลอ · กรอบสื่อมี cyan glow บางๆ เข้าธีม · `<img>` (`object-fit:contain`) หรือ `<video controls autoplay playsinline>`
  - แถบล่าง: title · ตัวนับ `i / n` · source domain · ปุ่ม **⬇ ดาวน์โหลด** (ยิง `form` ด้วยข้อความ "โหลดอันที่เปิดอยู่" → จัสมิน เรียก `download_media("current")`) · ปุ่ม ✕
  - ปุ่ม ‹ › ซ้าย-ขวา (โผล่เมื่อ list > 1) → prev/next
  - คีย์: `Esc` ปิด · `←/→` เลื่อน · คลิก backdrop ปิด
  - รูป: คลิกที่รูป → สลับ zoom 1x/2x (2x = `cursor:grab` ลากดูได้)
  - spring-in scale animation
- `hideMedia()` — ซ่อน overlay · `<video>` → `pause()` + `removeAttribute('src')` + `load()` (ปล่อย stream)
- export 3 ตัว, import ใน `main.js`

**`css/media.css` (ใหม่):** ใช้ตัวแปรสีของ HUD (cyan mono, พื้นโปร่งเบลอ) · `.media-grid` (`grid-template-columns: repeat(auto-fill, minmax(128px,1fr)); gap`) · tile (`aspect-ratio:1; object-fit:cover; border-radius; transition`) · number badge · `.media-viewer` (`position:fixed; inset:0; z-index:600; background:rgba(3,10,15,.94); backdrop-filter:blur; display:flex; flex-direction:column; align-items:center; justify-content:center`) · media frame glow · แถบ caption · ปุ่ม nav/close · `@media` มือถือ

**`static/style.css`:** `+@import url('css/media.css')`
**`index.html`:** `#mediaGrid` panel (ซ่อน default) + `#mediaViewer` (`hidden`) + markup ปุ่ม
**`js/main.js`:** dispatch `show_media_results` / `show_media` / `hide_media`
**`js/dom.js`:** refs element ใหม่

---

## Wiring

| ไฟล์ | แก้ |
|---|---|
| `tools/files.py` | **ย้าย `_safe_name` / `_uniq` มาจาก `mail.py`** (export) — `mail.py` เปลี่ยนเป็น import |
| `tools/__init__.py` | `from .media import search_media, download_media, view_media` + `__all__` |
| `server.py` | import 3 ตัว + ใส่ใน `chat` tools list (→ 29) + endpoint `/api/media` (+ `HTTPException`, `FileResponse`) |
| `personality.py` | +2 บรรทัด: ค้นรูป/วิดีโอ · โหลดเก็บ (เลือกโฟลเดอร์ย่อยให้เหมาะกับเนื้อหา, `#N`/`all`/URL) · เปิด/ปิด/เลื่อนดู (view_media open/close/next/prev) |
| `requirements.txt` | ไม่มี dep ใหม่ |

---

## Steps (ทีละ step)

1. ย้าย `_safe_name`/`_uniq` → `files.py` (mail.py import ตาม, เทสว่า mail ยังทำงาน) + `search_media` (ค้น image/video + normalize + เก็บผล + return) — test standalone (ddgs จริง)
2. `download_media` — image sync (SSRF, content-type, `_uniq`, audit, soft-ceiling, show_media action) + batch `#1,#3` + `all` — test URL รูปจริง + reject non-image
3. `download_media` — video async (thread + yt-dlp + `notify.push` + in-flight cap 2 + คิว) — test YouTube สั้น
4. `view_media` (open local / open `#N` remote / next / prev / close + `_viewer_list/_index`) + endpoint `/api/media` — test curl (containment / 404 / 415 / `Range`)
5. HUD — `media.js` + `media.css` + `index.html` + `main.js` + `dom.js` (grid + viewer + nav + zoom + keyboard) — `node --check` + ES-module load sanity
6. wire (`__init__`, `server.py`, `personality.py`) — regression: `py_compile` + `node --check` + 29 tools + smoke ทุก tool
7. docs (`CLAUDE.md` section + project tree) + user browser-test → commit

---

## Known limitations (flag)

- video download ไม่มี progress % — ผู้ใช้ได้ยินแค่ "เสร็จแล้ว" ตอนจบ (ผ่าน `notify.js`)
- `/api/media` ไม่มี auth (personal-use / localhost)
- image soft-ceiling ~60MB = safety stop กัน disk เต็ม (วิดีโอไม่จำกัดตามที่ผู้ใช้ขอ)
- concurrent video downloads = 2 (ที่เหลือเข้าคิว)
- `_pending_action` ยัง slot เดียว — feature นี้ 1 action/เทิร์นพอ
- `"current"` ใน `download_media`/`view_media` อ้าง state ฝั่ง server (`_viewer_index`) — ถ้าผู้ใช้คลิกเลื่อนรูปใน HUD เอง (ไม่ผ่าน จัสมิน) server จะไม่รู้ index ล่าสุด → client ต้องแนบ index มาด้วยตอนกดปุ่ม ⬇ (แก้ใน Step 5: ปุ่ม ⬇ ส่งข้อความ "โหลดรูปที่ N")
