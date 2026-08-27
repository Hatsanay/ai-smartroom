import os
import time
import tkinter
from datetime import date
from tkinter import filedialog
from typing import Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel

import tools
from personality import SYSTEM_PROMPT, strip_markdown
from tools import (
    control_youtube,
    create_folder,
    delete_path,
    get_weather,
    list_files,
    open_youtube,
    pop_pending_action,
    read_file,
    search_web,
    write_file,
)
from tts import synthesize as tts_synthesize

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

MODEL_NAME = "gemini-3.5-flash-lite"

app = FastAPI()

# ผู้ใช้คนเดียว เลยเก็บ chat session เดียวไว้ในหน่วยความจำพอ
chat = client.chats.create(
    model=MODEL_NAME,
    config=types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[
            search_web,
            open_youtube,
            control_youtube,
            get_weather,
            list_files,
            read_file,
            create_folder,
            write_file,
            delete_path,
        ],
    ),
)

# ติดตามโควตาฟรีของ Gemini เอง เพราะ API ไม่มี endpoint ให้เช็กโควตาที่เหลือตรงๆ
# limit จะรู้ค่าจริงก็ต่อเมื่อโดน 429 ครั้งแรกเท่านั้น (Google ไม่บอกไว้ล่วงหน้า)
# used_today รีเซ็ตทุกเที่ยงคืนตามเวลาเครื่อง เป็นค่าประมาณ ไม่ใช่เวลารีเซ็ตจริงของ Google
quota_state = {
    "used_today": 0,
    "limit": None,
    "day": date.today().isoformat(),
    "cooldown_until": None,
}


def _reset_if_new_day() -> None:
    today = date.today().isoformat()
    if quota_state["day"] != today:
        quota_state["day"] = today
        quota_state["used_today"] = 0
        quota_state["cooldown_until"] = None


def _parse_quota_error(e: genai_errors.ClientError) -> tuple[Optional[int], float]:
    """ดึง quota limit และเวลาที่ต้องรอ จาก error 429 ของ Gemini"""
    details = e.details if isinstance(e.details, dict) else {}
    if "details" not in details and isinstance(details.get("error"), dict):
        details = details["error"]

    limit = None
    retry_seconds = 60.0
    for part in details.get("details", []):
        type_name = part.get("@type", "")
        if type_name.endswith("QuotaFailure"):
            violations = part.get("violations", [])
            if violations and violations[0].get("quotaValue") is not None:
                limit = int(violations[0]["quotaValue"])
        elif type_name.endswith("RetryInfo"):
            raw = part.get("retryDelay", "")
            if raw.endswith("s"):
                try:
                    retry_seconds = float(raw[:-1])
                except ValueError:
                    pass
    return limit, retry_seconds


class ChatRequest(BaseModel):
    message: str
    # พิกัดจาก navigator.geolocation ของเบราว์เซอร์ (ถ้าผู้ใช้อนุญาต) — {"lat": .., "lon": .., "label": ..}
    # ส่งมาให้ get_weather() ใช้ตอนผู้ใช้ถามอากาศโดยไม่ระบุชื่อเมือง ดู tools.set_client_location()
    geo: Optional[dict] = None


class ChatResponse(BaseModel):
    reply: str
    action: Optional[dict] = None


class QuotaStatus(BaseModel):
    used: int
    limit: Optional[int]
    remaining: Optional[int]
    cooldown_seconds: int


class TTSRequest(BaseModel):
    text: str
    voice: str = "th_f_1"
    engine: str = "vachana"


@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest) -> ChatResponse:
    _reset_if_new_day()

    now = time.time()
    if quota_state["cooldown_until"] and now < quota_state["cooldown_until"]:
        remaining = int(quota_state["cooldown_until"] - now)
        return ChatResponse(reply=f"โควตา Gemini เต็มชั่วคราวค่ะ กรุณารออีก {remaining} วินาที")

    # พิกัดเบราว์เซอร์มีผลแค่ระหว่าง request นี้ — เซ็ตก่อนเรียก LLM แล้วล้างทิ้งใน finally ทุกทางออก
    # (เหมือน pop_pending_action) กันพิกัดเก่าค้างไปโผล่ใน request ถัดไปที่อาจไม่ได้ส่ง geo มา
    tools.set_client_location(req.geo)
    try:
        response = chat.send_message(req.message)
        quota_state["used_today"] += 1
        return ChatResponse(reply=strip_markdown(response.text), action=pop_pending_action())
    except genai_errors.ClientError as e:
        pop_pending_action()  # เคลียร์ทิ้งถ้ามี tool เรียกไปก่อนโดน error กัน action หลงเหลือไปโผล่ request ถัดไป
        if e.code == 429:
            limit, retry_seconds = _parse_quota_error(e)
            if limit is not None:
                quota_state["limit"] = limit
            quota_state["cooldown_until"] = time.time() + retry_seconds
            return ChatResponse(
                reply=f"โควตา Gemini เต็มชั่วคราวค่ะ กรุณารออีกประมาณ {int(retry_seconds)} วินาที"
            )
        raise
    except genai_errors.ServerError:
        # 503 UNAVAILABLE ฯลฯ — เกิดจาก Gemini เองโหลดสูงชั่วคราว ไม่ใช่โควตาเรา (ServerError เป็นคนละ
        # class กับ ClientError ที่ 429 ใช้ ไม่ได้สืบทอดกัน เลยต้อง catch แยก ไม่งั้นหลุดเป็น 500 ดิบๆ
        # ให้ client แบบไม่มีข้อความที่เข้าใจได้ — เจอจริงจาก log จริงของผู้ใช้)
        pop_pending_action()
        return ChatResponse(reply="ตอนนี้ Gemini กำลังมีผู้ใช้งานเยอะชั่วคราวค่ะ ลองถามใหม่อีกครั้งสักครู่นะคะ")
    finally:
        tools.set_client_location(None)


@app.get("/api/quota", response_model=QuotaStatus)
def quota_status(response: Response) -> QuotaStatus:
    response.headers["Cache-Control"] = "no-store"
    _reset_if_new_day()
    now = time.time()
    cooldown = (
        max(0, int(quota_state["cooldown_until"] - now))
        if quota_state["cooldown_until"]
        else 0
    )
    limit = quota_state["limit"]
    used = quota_state["used_today"]
    return QuotaStatus(
        used=used,
        limit=limit,
        remaining=(limit - used) if limit is not None else None,
        cooldown_seconds=cooldown,
    )


@app.post("/api/tts")
def tts_endpoint(req: TTSRequest) -> Response:
    audio_bytes, media_type = tts_synthesize(req.text, req.voice, req.engine)
    return Response(content=audio_bytes, media_type=media_type)


class FolderStatus(BaseModel):
    path: Optional[str] = None


@app.get("/api/file_access_status", response_model=FolderStatus)
def file_access_status() -> FolderStatus:
    return FolderStatus(path=tools.get_allowed_folder())


@app.post("/api/browse_folder", response_model=FolderStatus)
def browse_folder_endpoint() -> FolderStatus:
    # เปิด native folder picker ของ Windows จริงๆ ผ่าน tkinter (มากับ Python อยู่แล้ว ไม่ต้องลง lib
    # เพิ่ม) — ใช้ได้เพราะ server รันอยู่บนเครื่องเดียวกับที่ผู้ใช้เห็นหน้าเว็บ (ยังไม่ใช่ Pi) เรียกนี้
    # เป็น blocking call รอจนผู้ใช้เลือก/ปิดหน้าต่างก่อนถึงจะ return กลับไป
    root = tkinter.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected = filedialog.askdirectory(title="เลือกโฟลเดอร์ที่ให้ FRIDAY เข้าถึงไฟล์ได้")
    finally:
        root.destroy()

    if selected:
        tools.set_allowed_folder(selected)
        return FolderStatus(path=selected)
    return FolderStatus(path=tools.get_allowed_folder())


app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
