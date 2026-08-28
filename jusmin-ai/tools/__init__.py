"""tool registry ของ จัสมิน — LLM (Gemini) เรียกใช้ผ่าน function calling

แยกเป็นไฟล์ย่อยตาม feature: web (ค้นเว็บ) / weather / youtube / files (เข้าถึงไฟล์ในคอม)
+ _state (pending_action ที่ weather/youtube share กัน)

server.py และ jusmin.py ยัง `from tools import ...` / `import tools` / `tools.xxx()` ได้เหมือนเดิม
เพราะ re-export ทุกชื่อ public ที่นี่
"""

from . import notify, reminders  # submodule เข้าถึงได้เป็น tools.notify / tools.reminders (server.py ใช้)
from ._state import pop_pending_action
from .files import (
    create_folder,
    delete_path,
    get_allowed_folder,
    list_files,
    read_file,
    set_allowed_folder,
    write_file,
)
from .briefing import daily_briefing
from .mail import check_email, read_email, save_attachment, search_email, send_email
from .memory import forget, recall, remember
from .reminders import add_reminder, cancel_reminder, list_reminders
from .tasks import add_task, complete_task, list_tasks
from .weather import get_weather, set_client_location
from .web import search_web
from .youtube import control_youtube, open_youtube

__all__ = [
    "search_web",
    "get_weather",
    "set_client_location",
    "open_youtube",
    "control_youtube",
    "pop_pending_action",
    "list_files",
    "read_file",
    "create_folder",
    "write_file",
    "delete_path",
    "get_allowed_folder",
    "set_allowed_folder",
    # เลขา: ความจำ + งาน + เตือน (Group A)
    "remember",
    "recall",
    "forget",
    "add_task",
    "list_tasks",
    "complete_task",
    "add_reminder",
    "list_reminders",
    "cancel_reminder",
    "check_email",
    "read_email",
    "search_email",
    "save_attachment",
    "send_email",
    "daily_briefing",
]
