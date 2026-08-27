import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

from personality import SYSTEM_PROMPT, strip_markdown
from tools import search_web

# โหลด API key จาก .env
load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

MODEL_NAME = "gemini-3.5-flash-lite"


def main():
    print("⚡ FRIDAY พร้อมทำงาน (พิมพ์ 'exit' หรือ 'quit' เพื่อออก)\n")

    # chats.create เก็บประวัติให้อัตโนมัติ -> จำบริบทเดิมได้
    chat = client.chats.create(
        model=MODEL_NAME,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[search_web],
        ),
    )

    while True:
        try:
            user_input = input("คุณ: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 บาย")
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", "ออก"}:
            print("👋 แล้วเจอกันครับ")
            break

        try:
            response = chat.send_message(user_input)
            print(f"FRIDAY: {strip_markdown(response.text)}\n")
        except Exception as e:
            print(f"⚠️  เกิดข้อผิดพลาด: {e}\n")


if __name__ == "__main__":
    main()
