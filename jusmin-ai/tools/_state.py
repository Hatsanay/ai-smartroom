"""state ที่ share ข้ามโมดูล tools — ตอนนี้มีแค่ pending_action: "คำสั่งที่ tool ล่าสุดสั่งให้ app.js
ลงมือทำจริงในเบราว์เซอร์" (เปิด/เล่น/คุม YouTube, โชว์การ์ดอากาศ). weather.py กับ youtube.py เขียนค่านี้;
server.py's chat_endpoint เรียก pop_pending_action() หลัง chat.send_message() เพื่อดึงออกแล้วเคลียร์ทิ้ง

เดิมเป็น module-global `_pending_action` ตัวเดียวใน tools.py — พอแยกไฟล์เลยย้ายมาไว้ที่นี่ให้ weather/
youtube import ร่วมกันได้ (พฤติกรรมเท่าเดิม: process เดียว รัน personal use คนเดียว ไม่ต้อง thread-safe)
"""

pending_action: dict | None = None


def pop_pending_action() -> dict | None:
    """ดึง action ที่ tool ล่าสุดสั่งไว้ (ถ้ามี) ออกมาแล้วเคลียร์ทิ้ง กันหลงเหลือข้ามไปโผล่ใน request ถัดไป"""
    global pending_action
    action, pending_action = pending_action, None
    return action
