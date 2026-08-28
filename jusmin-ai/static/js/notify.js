/* poll /api/notifications ทุก 10 วิ — reminder ที่ถึงเวลา (scheduler ฝั่ง server เป็นคน push)
   เด้งเฉพาะตอนแท็บนี้เปิดอยู่ (เหมือน weather/youtube panel). reuse announceSystemNotice (โชว์ในแชท +
   เปิดสีเขียว + เริ่มช่วงคุยต่อเนื่อง) + speak (พูดออกเสียง) */
import { announceSystemNotice } from './chatui.js';
import { speak } from './sound.js';

const NOTIFY_POLL_MS = 10000;

async function pollNotifications() {
  try {
    const res = await fetch('/api/notifications', { cache: 'no-store' });
    if (!res.ok) return;
    const data = await res.json();
    const items = data.items || [];
    for (const it of items) {
      announceSystemNotice('⏰ ' + it.text); // ⏰
    }
    // พูดออกเสียงแค่ตัวสุดท้าย (ttsAudio เล่นทีละอัน — reminder เด้งพร้อมกันหลายอันเป็นเคสหายาก)
    if (items.length) speak(items[items.length - 1].text);
  } catch (err) {
    // เน็ต/server สะดุดชั่วคราว — รอบหน้าค่อยลองใหม่
  }
}

setInterval(pollNotifications, NOTIFY_POLL_MS);
