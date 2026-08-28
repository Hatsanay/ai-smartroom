from ddgs import DDGS
from ddgs.exceptions import DDGSException

# สร้างครั้งเดียวใช้ซ้ำทุก request แทนสร้างใหม่ทุกครั้งที่ค้น (server เป็น process เดียวรันยาว)
_ddgs = DDGS()


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
