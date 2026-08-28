/* entry point — import ทุกโมดูล (บางอันแค่ side-effect: ต่อ event listener/เริ่ม loop ตอนโหลด)
   แล้ววาง form submit handler (ตัวประสานงานหลัก) + bootstrap ที่ท้าย */
import { S } from './state.js';
import { form, input } from './dom.js';
import { addLine, setThinking, openUrlWithFallback } from './chatui.js';
import { sendBeep, receiveBeep, speak } from './sound.js';
import { recordLatency, refreshQuota, renderQuotaDisplay, runBoot, QUOTA_SYNC_MS } from './hud.js';
import { playYoutubeVideo, controlYoutube } from './youtube.js';
import { showWeather, scheduleWeatherHide } from './weather.js';
import { startWakeMode, startFollowUpWindow } from './voice.js';
import { renderWaveRing } from './wave.js';
import { refreshClientGeo, GEO_MAX_AGE_MS, GEO_RETRY_MS } from './geo.js';
import './settings.js';
import './notify.js'; // poll /api/notifications -> reminder ที่ถึงเวลาเด้ง

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const message = input.value.trim();
  if (!message) return;

  S.engagedActive = true; // กำลังใช้งาน จัสมิน อยู่จริง (พิมพ์/กดพูด/สั่งผ่าน wake mode) โชว์แชท+เขียวไว้ก่อน
  addLine('you', message);
  input.value = '';
  setThinking(true);
  sendBeep();

  const t0 = performance.now();
  try {
    // ยังไม่มีพิกัด (ขอตอนโหลดหน้าไม่สำเร็จ / เพิ่งกดอนุญาต) หรือพิกัดเก่าเกิน 10 นาที -> ขอใหม่แบบ
    // ไม่รอ (request นี้ใช้ค่าที่มีอยู่ รอบหน้าค่อยได้ค่าสด) — rate-limit ไว้กันยิงทุก submit ตอนโดนปฏิเสธ
    const geoStale = S.clientGeo && Date.now() - S.clientGeoFetchedAt > GEO_MAX_AGE_MS;
    if ((!S.clientGeo || geoStale) && Date.now() - S.geoLastAttemptAt > GEO_RETRY_MS) refreshClientGeo();
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(S.clientGeo ? { message, geo: S.clientGeo } : { message }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    recordLatency(performance.now() - t0);
    addLine('jusmin', data.reply);
    receiveBeep();
    // เปิดก่อน speak() เสมอ (ไม่รอ TTS โหลด/เล่นจบ) เพราะ browser อนุญาต window.open() แบบไม่โดน
    // popup blocker ได้แค่ช่วงสั้นๆ หลัง user gesture (transient activation) รอ TTS ก่อนมักเลยเวลานั้นไปแล้ว
    if (data.action?.type === 'open_url' && data.action.url) {
      openUrlWithFallback(data.action.url);
    } else if (data.action?.type === 'play_youtube' && data.action.video_id) {
      playYoutubeVideo(data.action.video_id, data.action.title, data.action.reset_volume);
    } else if (data.action?.type === 'youtube_control' && data.action.action) {
      controlYoutube(data.action.action);
    } else if (data.action?.type === 'show_weather' && data.action.data) {
      showWeather(data.action.data);
    }
    const wasWeatherShown = data.action?.type === 'show_weather' && !!data.action.data;
    // นับ 15 วิ "หลังเสียงพูดหยุดจริง" (ผ่าน callback ตอน speak() จบ) ไม่ใช่นับตั้งแต่ได้คำตอบมา
    // ไม่งั้นคำตอบยาวๆ ที่พูดนาน จะโดนกินเวลาช่วงคุยต่อเนื่องไปตั้งแต่ยังพูดไม่จบ — เรียกไม่ว่าจะพิมพ์
    // หรือคุยผ่านเสียง กันแชทกับสีเขียวหายไปกลางคันตอนยังตอบไม่จบ — panel สภาพอากาศก็นับแบบเดียวกัน
    speak(data.reply, () => {
      startFollowUpWindow();
      if (wasWeatherShown) scheduleWeatherHide();
    });
  } catch (err) {
    addLine('jusmin', `เชื่อมต่อไม่ได้: ${err.message}`);
    startFollowUpWindow(); // ให้เวลาอ่าน error สักพักก่อนแชทจะหายไปเอง แทนที่จะค้าง S.engagedActive ตลอดไป
  } finally {
    setThinking(false);
    refreshQuota();
  }
});

runBoot();
refreshQuota();
setInterval(refreshQuota, QUOTA_SYNC_MS); // sync ค่าจริงกับ server เป็นระยะ + เป็น heartbeat เช็ค LINK OK/LOST ด้วย
setInterval(renderQuotaDisplay, 1000); // อัปเดตแค่ตัวเลขนับถอยหลัง cooldown ให้ลื่น ไม่ยิง request
startWakeMode(); // ฟังตลอดเป็นค่าเริ่มต้น (เบราว์เซอร์จะขอสิทธิ์ไมค์เองถ้ายังไม่เคยอนุญาต)
renderWaveRing();
