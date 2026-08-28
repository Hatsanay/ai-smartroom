import { S } from './state.js';
import { muteBtn, voiceSelect, engineSelect, voiceField } from './dom.js';
import { pauseWakeListening, resumeWakeListeningAfterDelay } from './voice.js';
import { duckYoutubeVolume, restoreYoutubeVolume } from './youtube.js';

/* ---------- เสียง (Web Audio, ไม่ต้องมีไฟล์เสียงภายนอก) ---------- */

let muted = localStorage.getItem('jusmin_muted') === '1';
let audioCtx = null;

function updateMuteBtn() {
  muteBtn.textContent = muted ? '🔇' : '🔊';
}
updateMuteBtn();

muteBtn.addEventListener('click', () => {
  muted = !muted;
  localStorage.setItem('jusmin_muted', muted ? '1' : '0');
  updateMuteBtn();
});

function beep(freq, duration, type = 'sine', gain = 0.05) {
  if (muted) return;
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    const osc = audioCtx.createOscillator();
    const g = audioCtx.createGain();
    osc.type = type;
    osc.frequency.value = freq;
    g.gain.value = gain;
    osc.connect(g).connect(audioCtx.destination);
    const now = audioCtx.currentTime;
    g.gain.setValueAtTime(gain, now);
    g.gain.exponentialRampToValueAtTime(0.0001, now + duration);
    osc.start(now);
    osc.stop(now + duration);
  } catch (err) {
    // เบราว์เซอร์บางตัวอาจบล็อก AudioContext ก่อน user gesture ก็แค่เงียบไว้
  }
}

export const sendBeep = () => beep(880, 0.08, 'sine', 0.04);
export const receiveBeep = () => beep(520, 0.15, 'sine', 0.05);

/* ---------- Text-to-Speech: จัสมิน พูดตอบกลับด้วยเสียงจริงจาก server (PyThaiTTS/vachana) ----------
   เปลี่ยนจากใช้เสียง browser (speechSynthesis) มาเป็นให้ server สร้างไฟล์เสียงส่งมาเล่นแทน
   เพราะเสียง SAPI ของ Windows ฟังดูหุ่นยนต์เกินไป ทดสอบเทียบเสียงจริงหลายแบบแล้วเลือก engine
   นี้ (ปรับ noise_scale/noise_w_scale ให้จังหวะพูดนิ่งขึ้นด้วย ดู tts.py) */

const THAI_VOICES = [
  { id: 'th_f_1', label: 'เสียงหญิง 1' },
  { id: 'th_m_1', label: 'เสียงชาย 1' },
  { id: 'th_f_2', label: 'เสียงหญิง 2' },
  { id: 'th_m_2', label: 'เสียงชาย 2' },
];

let selectedVoiceId = localStorage.getItem('jusmin_voice') || 'th_f_1';

function populateVoiceOptions() {
  voiceSelect.innerHTML = '';
  THAI_VOICES.forEach((v) => {
    const opt = document.createElement('option');
    opt.value = v.id;
    opt.textContent = v.label;
    voiceSelect.appendChild(opt);
  });
  voiceSelect.value = selectedVoiceId;
}
populateVoiceOptions();

voiceSelect.addEventListener('change', () => {
  selectedVoiceId = voiceSelect.value;
  localStorage.setItem('jusmin_voice', selectedVoiceId);
});

// engine เสียง: ค่าเริ่มต้น 'google' (Google Translate TTS ตามที่ผู้ใช้ขอ) — สลับกลับไป 'vachana'
// (เสียงคุณภาพสูงในเครื่อง) ได้จากเมนู "ตั้งค่า" ใน sidebar จำค่าที่เลือกไว้ใน localStorage
let selectedEngine = localStorage.getItem('jusmin_tts_engine') || 'google';

// Google Translate TTS (ผ่าน gTTS) ไม่มีพารามิเตอร์ปรับความเร็วให้ปรับเหมือน vachana (API ของ
// Google เองมีแค่ normal/slow ไม่มี "เร็วขึ้น" ให้เลือก) วัดจริงเทียบประโยคเดียวกัน: vachana ~3.66 วิ
// vs google ~6.79 วิ (ช้ากว่าเกือบ 2 เท่า) เลยเร่ง playback rate ของ <audio> element เอาแทน —
// เบราว์เซอร์คง pitch ให้อัตโนมัติ (ไม่ใช่เสียงติ๊งต๊องแบบเร่งเทป) ไม่ต้องประมวลผลเสียงเพิ่มฝั่ง server
const GOOGLE_PLAYBACK_RATE = 1.4;


function applyEngineUI() {
  engineSelect.value = selectedEngine;
  // ตัวเลือกเสียง (th_f_1 ฯลฯ) มีความหมายเฉพาะ engine vachana เท่านั้น ซ่อนทั้งแถว (label+select) ตอนเลือก google
  voiceField.classList.toggle('hidden', selectedEngine !== 'vachana');
}
applyEngineUI();

engineSelect.addEventListener('change', () => {
  selectedEngine = engineSelect.value;
  localStorage.setItem('jusmin_tts_engine', selectedEngine);
  applyEngineUI();
});

let currentOnDone = null;
let currentTtsUrl = null;

function callDone() {
  const cb = currentOnDone;
  currentOnDone = null;
  if (cb) cb();
}

const ttsAudio = new Audio();
let ttsAudioCtx = null;
export let ttsAnalyser = null;
export let ttsDataArray = null;

function ensureTtsAnalyser() {
  if (ttsAnalyser) return;
  try {
    ttsAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const source = ttsAudioCtx.createMediaElementSource(ttsAudio);
    ttsAnalyser = ttsAudioCtx.createAnalyser();
    ttsAnalyser.fftSize = 128;
    ttsAnalyser.smoothingTimeConstant = 0.6;
    ttsDataArray = new Uint8Array(ttsAnalyser.frequencyBinCount);
    source.connect(ttsAnalyser);
    ttsAnalyser.connect(ttsAudioCtx.destination); // ต้องต่อกลับไป destination ไม่งั้นไม่มีเสียงออกลำโพง
  } catch (err) {
    // ต่อ analyser ไม่ได้ก็แค่ไม่มี waveform จริงตอนพูด เสียงยังเล่นได้ปกติ
  }
}
ttsAudio.addEventListener('play', () => {
  S.ttsSpeaking = true;
  pauseWakeListening(); // ปิดไมค์จริงๆ ตอน จัสมิน พูด กัน STT หยิบเสียงตัวเองมาตีความ
  duckYoutubeVolume();
});
ttsAudio.addEventListener('ended', () => {
  S.ttsSpeaking = false;
  resumeWakeListeningAfterDelay();
  restoreYoutubeVolume();
  callDone();
});
ttsAudio.addEventListener('error', () => {
  S.ttsSpeaking = false;
  resumeWakeListeningAfterDelay();
  restoreYoutubeVolume();
  callDone();
});

export function speak(text, onDone) {
  // เรียก onDone เสมอไม่ว่าจะพูดจริงได้หรือไม่ (มิวท์/error) เพราะโค้ดฝั่งเรียกใช้
  // (เช่น เปิดช่วงคุยต่อเนื่อง 15 วิ) ต้องทำงานต่อได้แม้เสียงพูดจะมีปัญหา ไม่ควรค้าง
  if (muted || !text.trim()) {
    if (onDone) onDone();
    return;
  }
  currentOnDone = onDone || null;

  fetch('/api/tts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, voice: selectedVoiceId, engine: selectedEngine }),
  })
    .then((res) => {
      if (!res.ok) throw new Error(`TTS HTTP ${res.status}`);
      return res.blob();
    })
    .then((blob) => {
      ensureTtsAnalyser();
      if (currentTtsUrl) URL.revokeObjectURL(currentTtsUrl);
      currentTtsUrl = URL.createObjectURL(blob);
      ttsAudio.src = currentTtsUrl;
      ttsAudio.playbackRate = selectedEngine === 'google' ? GOOGLE_PLAYBACK_RATE : 1.0;
      if (ttsAudioCtx && ttsAudioCtx.state === 'suspended') ttsAudioCtx.resume();
      return ttsAudio.play();
    })
    .catch(() => {
      // fetch หรือ play ล้มเหลว -> ต้องเรียก onDone เองเพราะ event 'ended' จะไม่มีทางยิง
      callDone();
    });
}
