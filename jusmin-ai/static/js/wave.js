import { S } from './state.js';
import { coreWrap, log, waveRing } from './dom.js';
import { ttsAnalyser, ttsDataArray } from './sound.js';
import { exitYoutubeFullscreen } from './youtube.js';

/* ---------- คลื่นเสียงรอบวง: ข้อมูลจริงเท่าที่ browser API ให้ได้ ----------
   ตอนฟัง: amplitude จริงจากไมค์ผ่าน Web Audio AnalyserNode
   ตอนพูด: เบราว์เซอร์ไม่มี API ให้ดึง waveform จริงของเสียง TTS ที่สังเคราะห์ออกมา
   เลยใช้จังหวะคำพูดจริงจาก utterance.onboundary (ยิงตามคำ/ประโยคจริง) มาขับคลื่นแทน
   ไม่ใช่ amplitude แท้ๆ แต่ยังเป็นสัญญาณจริงจากการพูดจริง ไม่ใช่ของสุ่มเล่นๆ */

const WAVE_BAR_COUNT = 40;
const WAVE_BASE_RADIUS = 168;
const waveBars = [];

for (let i = 0; i < WAVE_BAR_COUNT; i++) {
  const bar = document.createElement('div');
  bar.className = 'wave-bar';
  const angle = (360 / WAVE_BAR_COUNT) * i;
  bar.dataset.angle = angle;
  waveRing.appendChild(bar);
  waveBars.push(bar);
}

let micStream = null;
let micAnalyser = null;
let micDataArray = null;

export async function ensureMicAnalyser() {
  if (micAnalyser || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return;
  try {
    micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const audioCtxForMic = new (window.AudioContext || window.webkitAudioContext)();
    const source = audioCtxForMic.createMediaStreamSource(micStream);
    micAnalyser = audioCtxForMic.createAnalyser();
    micAnalyser.fftSize = 128;
    micAnalyser.smoothingTimeConstant = 0.75;
    micDataArray = new Uint8Array(micAnalyser.frequencyBinCount);
    source.connect(micAnalyser);
  } catch (err) {
    // ผู้ใช้ปฏิเสธสิทธิ์ไมค์ หรือเบราว์เซอร์ไม่รองรับ - แค่ไม่มีคลื่นให้โชว์ ไม่กระทบฟีเจอร์อื่น
  }
}

function isMicOpen() {
  return S.listening || (S.wakeMode && !S.ttsSpeaking);
}

let prevEngagedActive = false; // rising edge ของ S.engagedActive (ย่อจอ YouTube ตอนถูกเรียก) — ใช้ที่นี่ที่เดียว
export function renderWaveRing() {
  requestAnimationFrame(renderWaveRing);

  // สีเขียว = S.engagedActive: เริ่มทันทีที่ได้ยินคำว่า "จัสมิน" (ครอบคลุมช่วงประมวลผล+ตอบด้วย)
  // แล้วค้างไว้จนกว่าจะเงียบครบ 15 วิหลังตอบเสร็จจริงๆ ถึงจะกลับสีเดิม (ต้องเรียก "จัสมิน" ใหม่)
  coreWrap.classList.toggle('mic-listening', S.engagedActive);
  // แชท: โชว์เฉพาะตอนกำลังเรียก/ใช้งาน จัสมิน อยู่จริง (S.engagedActive) ส่วน :hover คุมเองด้วย CSS แล้ว
  log.classList.toggle('chat-active', S.engagedActive);

  // YouTube เต็มจออยู่แล้วผู้ใช้เพิ่งเรียก จัสมิน (S.engagedActive ขึ้นขอบ) -> ย่อจอชั่วคราวให้เห็น HUD หลัก
  // เต็มรูปแบบ (เวฟ/สี/แชท เหมือนหน้าหลักเป๊ะ) — พอคุยจบ + เงียบครบ 15 วิ (expireFollowUpWindow) กลับไปเต็มจอเอง
  if (S.engagedActive && !prevEngagedActive && S.ytMaximized) {
    exitYoutubeFullscreen();          // เคลียร์ S.ytWasMaximizedBeforeEngage ด้วย
    S.ytWasMaximizedBeforeEngage = true; // ...แล้วตั้งใหม่ทีหลัง = "กลับไปเต็มจอเมื่อคุยจบ"
  }
  prevEngagedActive = S.engagedActive;

  const micOpen = isMicOpen();
  const active = micOpen || S.ttsSpeaking;
  waveRing.classList.toggle('active', active);
  if (!active) return;

  if (S.ttsSpeaking) {
    if (ttsAnalyser) {
      // เสียงพูดตอนนี้มาจาก server จริงๆ เลยดึง amplitude จริงจาก audio element ได้เหมือนฝั่งไมค์
      ttsAnalyser.getByteFrequencyData(ttsDataArray);
      waveBars.forEach((bar, i) => {
        const dataIdx = Math.floor((i / waveBars.length) * ttsDataArray.length);
        const level = ttsDataArray[dataIdx] / 255;
        const radius = WAVE_BASE_RADIUS + level * 32;
        bar.style.transform = `rotate(${bar.dataset.angle}deg) translateY(-${radius}px) scaleY(${1 + level * 4})`;
        bar.style.opacity = 0.4 + level * 0.6;
      });
    } else {
      renderIdleWave();
    }
  } else if (micOpen && micAnalyser) {
    micAnalyser.getByteFrequencyData(micDataArray);
    waveBars.forEach((bar, i) => {
      const dataIdx = Math.floor((i / waveBars.length) * micDataArray.length);
      const level = micDataArray[dataIdx] / 255;
      const radius = WAVE_BASE_RADIUS + level * 40;
      bar.style.transform = `rotate(${bar.dataset.angle}deg) translateY(-${radius}px) scaleY(${1 + level * 5})`;
      bar.style.opacity = 0.35 + level * 0.65;
    });
  } else {
    // เปิดไมค์/กำลังพูดอยู่ แต่ยังไม่มี analyser พร้อม (เช่น ผู้ใช้ยังไม่กด allow) โชว์นิ่งๆ เบาๆ ไว้ก่อน
    renderIdleWave();
  }
}

function renderIdleWave() {
  waveBars.forEach((bar) => {
    bar.style.transform = `rotate(${bar.dataset.angle}deg) translateY(-${WAVE_BASE_RADIUS}px) scaleY(1)`;
    bar.style.opacity = 0.3;
  });
}

ensureMicAnalyser();
