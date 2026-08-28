"""tool registry ของ จัสมิน — LLM (Gemini) เรียกใช้ผ่าน function calling

แยกเป็นไฟล์ย่อยตาม feature: web (ค้นเว็บ) / weather / youtube / files (เข้าถึงไฟล์ในคอม)
+ _state (pending_action ที่ weather/youtube share กัน)

server.py และ jusmin.py ยัง `from tools import ...` / `import tools` / `tools.xxx()` ได้เหมือนเดิม
เพราะ re-export ทุกชื่อ public ที่นี่
"""

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
]
