const form = document.getElementById('form');
const input = document.getElementById('input');
const log = document.getElementById('log');
const core = document.getElementById('core');
const coreWrap = document.getElementById('coreWrap');
const status = document.getElementById('status');
const quota = document.getElementById('quota');
const muteBtn = document.getElementById('muteBtn');
const bootOverlay = document.getElementById('boot');
const bootText = document.getElementById('bootText');

const latencyPoly = document.getElementById('latencyPoly');
const latencyLast = document.getElementById('latencyLast');
const latencyEmpty = document.getElementById('latencyEmpty');
const quotaBars = Array.from(document.getElementById('quotaBars').children);
const quotaGaugeLabel = document.getElementById('quotaGaugeLabel');
const radarSweep = document.getElementById('radarSweep');
const linkStatus = document.getElementById('linkStatus');
const clockTime = document.getElementById('clockTime');
const clockDate = document.getElementById('clockDate');
const micBtn = document.getElementById('micBtn');
const voiceSelect = document.getElementById('voiceSelect');
const engineSelect = document.getElementById('engineSelect');
const waveRing = document.getElementById('waveRing');
const ytPanel = document.getElementById('ytPanel');
const ytPanelTitle = document.getElementById('ytPanelTitle');
const ytPlayerMount = document.getElementById('ytPlayerMount');
const ytExitFs = document.getElementById('ytExitFs');
const weatherPanel = document.getElementById('weatherPanel');
const weatherLocation = document.getElementById('weatherLocation');
const weatherEmoji = document.getElementById('weatherEmoji');
const weatherTemp = document.getElementById('weatherTemp');
const weatherCondition = document.getElementById('weatherCondition');
const weatherFeelsLike = document.getElementById('weatherFeelsLike');
const weatherHumidity = document.getElementById('weatherHumidity');
const weatherWind = document.getElementById('weatherWind');
const weatherForecast = document.getElementById('weatherForecast');
const weatherFx = document.getElementById('weatherFx');
const folderBtn = document.getElementById('folderBtn');

/* ---------- เสียง (Web Audio, ไม่ต้องมีไฟล์เสียงภายนอก) ---------- */

let muted = localStorage.getItem('friday_muted') === '1';
let audioCtx = null;

function updateMuteBtn() {
  muteBtn.textContent = muted ? '🔇' : '🔊';
}
updateMuteBtn();

muteBtn.addEventListener('click', () => {
  muted = !muted;
  localStorage.setItem('friday_muted', muted ? '1' : '0');
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

const sendBeep = () => beep(880, 0.08, 'sine', 0.04);
const receiveBeep = () => beep(520, 0.15, 'sine', 0.05);

/* ---------- Text-to-Speech: FRIDAY พูดตอบกลับด้วยเสียงจริงจาก server (PyThaiTTS/vachana) ----------
   เปลี่ยนจากใช้เสียง browser (speechSynthesis) มาเป็นให้ server สร้างไฟล์เสียงส่งมาเล่นแทน
   เพราะเสียง SAPI ของ Windows ฟังดูหุ่นยนต์เกินไป ทดสอบเทียบเสียงจริงหลายแบบแล้วเลือก engine
   นี้ (ปรับ noise_scale/noise_w_scale ให้จังหวะพูดนิ่งขึ้นด้วย ดู tts.py) */

const THAI_VOICES = [
  { id: 'th_f_1', label: 'เสียงหญิง 1' },
  { id: 'th_m_1', label: 'เสียงชาย 1' },
  { id: 'th_f_2', label: 'เสียงหญิง 2' },
  { id: 'th_m_2', label: 'เสียงชาย 2' },
];

let selectedVoiceId = localStorage.getItem('friday_voice') || 'th_f_1';

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
  localStorage.setItem('friday_voice', selectedVoiceId);
});

// engine เสียง: ค่าเริ่มต้น 'google' (Google Translate TTS ตามที่ผู้ใช้ขอ) — สลับกลับไป 'vachana'
// (เสียงคุณภาพสูงในเครื่อง) ได้จากเมนู "ตั้งค่า" ใน sidebar จำค่าที่เลือกไว้ใน localStorage
let selectedEngine = localStorage.getItem('friday_tts_engine') || 'google';

// Google Translate TTS (ผ่าน gTTS) ไม่มีพารามิเตอร์ปรับความเร็วให้ปรับเหมือน vachana (API ของ
// Google เองมีแค่ normal/slow ไม่มี "เร็วขึ้น" ให้เลือก) วัดจริงเทียบประโยคเดียวกัน: vachana ~3.66 วิ
// vs google ~6.79 วิ (ช้ากว่าเกือบ 2 เท่า) เลยเร่ง playback rate ของ <audio> element เอาแทน —
// เบราว์เซอร์คง pitch ให้อัตโนมัติ (ไม่ใช่เสียงติ๊งต๊องแบบเร่งเทป) ไม่ต้องประมวลผลเสียงเพิ่มฝั่ง server
const GOOGLE_PLAYBACK_RATE = 1.4;

const voiceField = document.getElementById('voiceField');

function applyEngineUI() {
  engineSelect.value = selectedEngine;
  // ตัวเลือกเสียง (th_f_1 ฯลฯ) มีความหมายเฉพาะ engine vachana เท่านั้น ซ่อนทั้งแถว (label+select) ตอนเลือก google
  voiceField.classList.toggle('hidden', selectedEngine !== 'vachana');
}
applyEngineUI();

engineSelect.addEventListener('change', () => {
  selectedEngine = engineSelect.value;
  localStorage.setItem('friday_tts_engine', selectedEngine);
  applyEngineUI();
});

/* ---------- Sidebar: สไลด์เข้าจากขวา เปิดด้วยปุ่ม ⚙ — ปิดด้วยปุ่ม ✕ / คลิกฉากหลัง / กด Esc ---------- */

const settingsBtn = document.getElementById('settingsBtn');
const sidebar = document.getElementById('sidebar');
const sidebarScrim = document.getElementById('sidebarScrim');
const sidebarClose = document.getElementById('sidebarClose');

function setSidebar(open) {
  sidebar.classList.toggle('open', open);
  sidebarScrim.classList.toggle('visible', open);
  settingsBtn.classList.toggle('active', open);
  settingsBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
  sidebar.setAttribute('aria-hidden', open ? 'false' : 'true');
}

settingsBtn.addEventListener('click', () => setSidebar(!sidebar.classList.contains('open')));
sidebarClose.addEventListener('click', () => setSidebar(false));
sidebarScrim.addEventListener('click', () => setSidebar(false));
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && sidebar.classList.contains('open')) setSidebar(false);
});

/* ---------- โฟลเดอร์ที่อนุญาตให้ FRIDAY อ่านไฟล์ได้: state จริงจาก server เท่านั้น (ไม่ใช่แค่จำ
   ไว้ฝั่ง browser) เพราะ server เป็นคนตรวจ path จริงตอน list_files()/read_file() ถูกเรียก ต้อง sync
   กับ server เสมอไม่งั้นปุ่มจะโชว์ค่าที่ไม่ตรงกับที่ backend ใช้งานจริงอยู่ (ผิดหลักการ "ห้ามโชว์ข้อมูลปลอม") */

function updateFolderBtnLabel(path) {
  if (path) {
    const name = path.split(/[\\/]/).filter(Boolean).pop() || path;
    folderBtn.textContent = `📁 ${name}`;
    folderBtn.title = `FRIDAY เข้าถึงไฟล์ได้แค่ในนี้: ${path} (กดเพื่อเปลี่ยน)`;
    folderBtn.classList.add('configured');
  } else {
    folderBtn.textContent = '📁 เลือกโฟลเดอร์';
    folderBtn.title = 'ยังไม่ได้ตั้งค่า — กดเพื่อเลือกโฟลเดอร์ที่ให้ FRIDAY เข้าถึงไฟล์ได้';
    folderBtn.classList.remove('configured');
  }
}

async function refreshFolderStatus() {
  try {
    const res = await fetch('/api/file_access_status', { cache: 'no-store' });
    const data = await res.json();
    updateFolderBtnLabel(data.path);
  } catch (err) {
    // เช็คไม่สำเร็จก็แค่ปล่อยปุ่มไว้ตามค่าล่าสุดที่รู้ ไม่ใช่ปัญหาใหญ่
  }
}

folderBtn.addEventListener('click', async () => {
  // เรียก native folder picker ของ Windows ฝั่ง server (ดู /api/browse_folder ใน server.py) เป็น
  // blocking call รอจนผู้ใช้เลือก/ปิดหน้าต่างเลือกโฟลเดอร์ก่อน ปุ่มเลย disable รอไว้ระหว่างนั้น
  folderBtn.disabled = true;
  const prevText = folderBtn.textContent;
  folderBtn.textContent = 'กำลังเปิดหน้าต่างเลือกโฟลเดอร์...';
  try {
    const res = await fetch('/api/browse_folder', { method: 'POST' });
    const data = await res.json();
    updateFolderBtnLabel(data.path);
  } catch (err) {
    folderBtn.textContent = prevText;
  } finally {
    folderBtn.disabled = false;
  }
});

refreshFolderStatus();

/* ---------- ตำแหน่งปัจจุบันของเบราว์เซอร์: แนบไปกับ /api/chat ให้ get_weather() ใช้พิกัดจริงตอน
   ผู้ใช้ถามอากาศ "ที่นี่" โดยไม่ต้องพิมพ์ชื่อเมือง — มีแต่เบราว์เซอร์ที่รู้พิกัด (tool รันฝั่ง server)
   ถ้าผู้ใช้ไม่อนุญาต ก็ปล่อยเป็น null แล้ว get_weather() จะถามชื่อเมืองกลับตามเดิม (ไม่พังอะไร) */

let clientGeo = null; // { lat, lon, label } — label เป็น null ได้ถ้า reverse geocode ไม่สำเร็จ
let clientGeoFetchedAt = 0;
let geoInFlight = false; // กัน getCurrentPosition ซ้อนกันหลายเส้นทางที่เรียก refreshClientGeo()
let geoLastAttemptAt = 0; // rate-limit การ retry ตอนส่งข้อความ ไม่ให้ยิงทุก submit ถ้ายังไม่ได้พิกัด
const GEO_MAX_AGE_MS = 10 * 60 * 1000; // เกินนี้ถือว่าเก่า ค่อยขอพิกัดใหม่
const GEO_RETRY_MS = 20000; // เว้นอย่างน้อยเท่านี้ระหว่าง retry ตอน submit

async function reverseGeocodeLabel(lat, lon) {
  // BigDataCloud reverse-geocode-client: ฟรี ไม่ต้องขอ key ออกแบบมาให้เรียกจากเบราว์เซอร์โดยเฉพาะ
  // ใช้แค่หา "ชื่อพื้นที่" มาโชว์บนการ์ดอากาศ/พูดตอบ — เรียกไม่สำเร็จก็ไม่เป็นไร ใช้ "ตำแหน่งปัจจุบัน" แทน
  try {
    const opts = { cache: 'no-store' };
    if (typeof AbortSignal !== 'undefined' && AbortSignal.timeout) opts.signal = AbortSignal.timeout(6000);
    const res = await fetch(
      `https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${lat}&longitude=${lon}&localityLanguage=th`,
      opts
    );
    if (!res.ok) return null;
    const d = await res.json();
    return d.city || d.locality || d.principalSubdivision || null;
  } catch (err) {
    return null;
  }
}

function refreshClientGeo() {
  if (geoInFlight) return;
  if (!navigator.geolocation) {
    console.warn('[geo] เบราว์เซอร์นี้ไม่มี navigator.geolocation');
    return;
  }
  if (!window.isSecureContext) {
    // geolocation ใช้ได้เฉพาะ secure context — http://127.0.0.1 / http://localhost / https เท่านั้น
    // ถ้าเปิดผ่าน IP เครื่องในวง LAN (http://192.168.x.x:8000) เบราว์เซอร์จะบล็อกเงียบๆ
    console.warn('[geo] ไม่ใช่ secure context — เปิดหน้าเว็บผ่าน http://127.0.0.1:8000 (ไม่ใช่ IP เครื่อง)');
    return;
  }
  geoInFlight = true;
  geoLastAttemptAt = Date.now();
  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      geoInFlight = false;
      const lat = +pos.coords.latitude.toFixed(4); // ~11m พอสำหรับอากาศ + หยาบลงนิดเรื่อง privacy
      const lon = +pos.coords.longitude.toFixed(4);
      // เซ็ตพิกัดไว้ก่อนเลย เผื่อ reverse geocode ค้าง/ล่ม จะได้มีพิกัดส่งให้ server ทันที
      clientGeo = { lat, lon, label: null };
      clientGeoFetchedAt = Date.now();
      const label = await reverseGeocodeLabel(lat, lon);
      if (label && clientGeo && clientGeo.lat === lat && clientGeo.lon === lon) clientGeo.label = label;
    },
    (err) => {
      geoInFlight = false;
      // code 1 = ไม่อนุญาต, 2 = หาตำแหน่งไม่ได้, 3 = timeout — log ไว้ debug ได้ (F12 console)
      console.warn('[geo] getCurrentPosition ล้มเหลว:', err.code, err.message);
    },
    { enableHighAccuracy: false, timeout: 8000, maximumAge: 5 * 60 * 1000 }
  );
}

setTimeout(refreshClientGeo, 1200); // หน่วงนิดกันชนกับ prompt ขอสิทธิ์ไมค์ตอนโหลดหน้า

// Permissions API: ถ้าผู้ใช้กดอนุญาตตำแหน่งทีหลัง (จาก Site settings ของเบราว์เซอร์) ให้ดึงพิกัด
// ทันทีโดยไม่ต้องรีเฟรชหน้า — นี่คือเคสที่เจอจริง (อนุญาตแล้วแต่ระบบยังบอกว่าเข้าถึงไม่ได้)
if (navigator.permissions && navigator.permissions.query) {
  navigator.permissions.query({ name: 'geolocation' })
    .then((st) => {
      if (st.state === 'granted') refreshClientGeo();
      st.addEventListener('change', () => {
        if (st.state === 'granted') refreshClientGeo();
      });
    })
    .catch(() => {});
}

// กลับมาที่แท็บนี้ (เช่นสลับไปกดอนุญาตในตั้งค่าเบราว์เซอร์แล้วกลับมา) แล้วยังไม่มีพิกัด -> ลองใหม่
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible' && !clientGeo) refreshClientGeo();
});

let ttsSpeaking = false;
let currentOnDone = null;
let currentTtsUrl = null;

function callDone() {
  const cb = currentOnDone;
  currentOnDone = null;
  if (cb) cb();
}

const ttsAudio = new Audio();
let ttsAudioCtx = null;
let ttsAnalyser = null;
let ttsDataArray = null;

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

// ลดเสียงเพลง YouTube ลงชั่วคราวตอน FRIDAY พูด (เดิมเล่นทับกันเลย ฟังไม่รู้เรื่อง — ดู CLAUDE.md)
// setVolume() เป็นของ YT.Player เอง ปลอดภัยเรียกได้แม้ตอนยังไม่มี player (เช็ค guard ไว้แล้ว)
// restoreYoutubeVolume() ต้องกลับไปที่ ytVolume (ค่าที่ผู้ใช้ตั้งไว้ล่าสุดผ่านคำสั่ง volume_up/down)
// ไม่ใช่ค่าคงที่ 100 เสมอ ไม่งั้นถ้าผู้ใช้เคยหรี่เสียงไว้ พอ FRIDAY พูดจบเสียงจะดังกลับไป 100% เอง
// เช็ค ytPlayerReady ด้วยเสมอ (ไม่ใช่แค่ ytPlayer !== null) เพราะเมธอดของ YT.Player ใช้งานจริงไม่ได้
// ก่อน onReady แม้ตัว object จะถูกสร้างมาแล้วก็ตาม (ดูหมายเหตุที่ประกาศตัวแปรด้านบน) ถ้าไม่ ready
// ปล่อยผ่านเฉยๆ ได้ ไม่ต้องคิวรอเหมือน controlYoutube เพราะรอบพูดถัดไปจะ duck/restore ใหม่ให้เองอยู่แล้ว
const YT_DUCK_VOLUME = 15;
function duckYoutubeVolume() {
  if (ytPlayer && ytPlayerReady && typeof ytPlayer.setVolume === 'function') ytPlayer.setVolume(YT_DUCK_VOLUME);
}
function restoreYoutubeVolume() {
  if (ytPlayer && ytPlayerReady && typeof ytPlayer.setVolume === 'function') ytPlayer.setVolume(ytVolume);
}

ttsAudio.addEventListener('play', () => {
  ttsSpeaking = true;
  pauseWakeListening(); // ปิดไมค์จริงๆ ตอน FRIDAY พูด กัน STT หยิบเสียงตัวเองมาตีความ
  duckYoutubeVolume();
});
ttsAudio.addEventListener('ended', () => {
  ttsSpeaking = false;
  resumeWakeListeningAfterDelay();
  restoreYoutubeVolume();
  callDone();
});
ttsAudio.addEventListener('error', () => {
  ttsSpeaking = false;
  resumeWakeListeningAfterDelay();
  restoreYoutubeVolume();
  callDone();
});

function speak(text, onDone) {
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

async function ensureMicAnalyser() {
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
  return listening || (wakeMode && !ttsSpeaking);
}

function renderWaveRing() {
  requestAnimationFrame(renderWaveRing);

  // สีเขียว = engagedActive: เริ่มทันทีที่ได้ยินคำว่า "Friday" (ครอบคลุมช่วงประมวลผล+ตอบด้วย)
  // แล้วค้างไว้จนกว่าจะเงียบครบ 15 วิหลังตอบเสร็จจริงๆ ถึงจะกลับสีเดิม (ต้องเรียก "Friday" ใหม่)
  coreWrap.classList.toggle('mic-listening', engagedActive);
  // แชท: โชว์เฉพาะตอนกำลังเรียก/ใช้งาน FRIDAY อยู่จริง (engagedActive) ส่วน :hover คุมเองด้วย CSS แล้ว
  log.classList.toggle('chat-active', engagedActive);

  // YouTube เต็มจออยู่แล้วผู้ใช้เพิ่งเรียก Friday (engagedActive ขึ้นขอบ) -> ย่อจอชั่วคราวให้เห็น HUD หลัก
  // เต็มรูปแบบ (เวฟ/สี/แชท เหมือนหน้าหลักเป๊ะ) — พอคุยจบ + เงียบครบ 15 วิ (expireFollowUpWindow) กลับไปเต็มจอเอง
  if (engagedActive && !prevEngagedActive && ytMaximized) {
    exitYoutubeFullscreen();          // เคลียร์ ytWasMaximizedBeforeEngage ด้วย
    ytWasMaximizedBeforeEngage = true; // ...แล้วตั้งใหม่ทีหลัง = "กลับไปเต็มจอเมื่อคุยจบ"
  }
  prevEngagedActive = engagedActive;

  const micOpen = isMicOpen();
  const active = micOpen || ttsSpeaking;
  waveRing.classList.toggle('active', active);
  if (!active) return;

  if (ttsSpeaking) {
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

/* ---------- Speech-to-Text: พูดใส่ไมค์แทนพิมพ์ ---------- */

const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
let listening = false;

function setListening(on) {
  listening = on;
  micBtn.classList.toggle('listening', on);
  if (on) {
    status.textContent = 'LISTENING';
  } else if (status.textContent === 'LISTENING') {
    status.textContent = 'STANDBY';
  }
}

if (SpeechRecognitionCtor) {
  recognition = new SpeechRecognitionCtor();
  recognition.lang = 'th-TH';
  recognition.interimResults = true;
  recognition.continuous = false;

  recognition.onstart = () => setListening(true);
  recognition.onend = () => setListening(false);

  recognition.onresult = (e) => {
    let transcript = '';
    for (let i = 0; i < e.results.length; i++) {
      transcript += e.results[i][0].transcript;
    }
    input.value = transcript;
    const last = e.results[e.results.length - 1];
    if (last.isFinal && transcript.trim()) {
      form.requestSubmit();
    }
  };

  recognition.onerror = (e) => {
    if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
      announceSystemNotice('ขออนุญาตใช้ไมโครโฟนก่อนนะคะ เช็กสิทธิ์ในเบราว์เซอร์ด้วยค่ะ');
    } else if (e.error !== 'no-speech' && e.error !== 'aborted') {
      announceSystemNotice(`ฟังเสียงไม่สำเร็จค่ะ (${e.error})`);
    }
  };

  micBtn.addEventListener('click', () => {
    if (wakeMode) return; // โหมดฟังตลอดเปิดอยู่ ไม่ให้ใช้ปุ่มกดพูดซ้อนกัน
    if (listening) {
      recognition.stop();
    } else {
      input.value = '';
      recognition.start();
    }
  });
} else {
  micBtn.disabled = true;
  micBtn.title = 'เบราว์เซอร์นี้ไม่รองรับการพูด ลองใช้ Chrome หรือ Edge';
  wakeBtn.disabled = true;
  wakeBtn.title = 'เบราว์เซอร์นี้ไม่รองรับการพูด ลองใช้ Chrome หรือ Edge';
}

/* ---------- โหมดฟังตลอด: พูด "Friday" แล้วตามด้วยคำสั่งได้เลย ---------- */

const WAKE_WORD_PATTERNS = [/friday/i, /เฟรดเดย์/i, /เฟรเดย์/i, /ฟรายเดย์/i, /ไฟรเดย์/i];

// เรียกชื่อเฉยๆ ไม่มีคำสั่งตาม - ตอบรับสั้นๆ ด้วยเสียงจริง สุ่มสลับไว้กันซ้ำจำเจ
const WAKE_ACK_PHRASES = ['ค่ะ มีอะไรให้ช่วยคะ', 'ว่าไงคะบอส', 'ฟังอยู่ค่ะ', 'คะ พร้อมค่ะ'];

function extractWakeCommand(transcript) {
  for (const pattern of WAKE_WORD_PATTERNS) {
    const match = transcript.match(pattern);
    if (match) {
      return transcript.slice(match.index + match[0].length).trim();
    }
  }
  return null;
}

let wakeMode = false;
let wakeRecognition = null;
let wakeRestartTimer = null;

// ช่วงหน่วงก่อน restart session ฟังตลอดใหม่ทุกครั้งที่ session เดิมจบ (ปกติ ไม่ใช่แค่ตอน error —
// ดูหมายเหตุที่ onend ข้างล่าง) เก็บเป็นค่าน้อยที่สุดเท่าที่พอกันชนได้ กันไมค์ "หูหนวก" นานเกินจำเป็น
const WAKE_RESTART_DELAY_MS = 30;

// ช่วงคุยต่อเนื่องหลัง FRIDAY ตอบ: ไม่ต้องพูด "Friday" ซ้ำใน 15 วิถัดไป
const FOLLOWUP_MS = 15000;
const FOLLOWUP_STATUS_TEXT = 'STANDBY · ฟังต่อเนื่อง';
let followUpActive = false;
let followUpTimer = null;

// engagedActive คุมสีเขียว (core/wave/glow) กว้างกว่า followUpActive: เริ่มทันทีตั้งแต่ได้ยินคำว่า
// "Friday" (ครอบคลุมช่วงกำลังประมวลผล + กำลังตอบด้วย) แล้วค่อยนับ 15 วิถอยหลังหลังตอบเสร็จจริงๆ
// ถึงจะกลับเป็นสีเดิม ไม่ใช่แค่ตอนเข้าสู่ช่วง follow-up เท่านั้น
let engagedActive = false;
let prevEngagedActive = false; // ใช้จับ rising edge ของ engagedActive ใน renderWaveRing (ย่อจอ YouTube ตอนถูกเรียก)

// เรียกได้ทั้งตอนคุยผ่านเสียง (wake mode) และพิมพ์/กดพูดแบบธรรมดา — engagedActive ใช้คุม
// สีเขียว + การโชว์แชทเหมือนกันหมด ส่วนข้อความ "ฟังต่อเนื่อง"/ไม่ต้องพูด "Friday" ซ้ำ (followUpActive)
// มีความหมายเฉพาะตอน wake mode เปิดอยู่จริงเท่านั้น (ตอนนั้นถึงจะมี STT ฟังอยู่จริง)
function startFollowUpWindow() {
  clearTimeout(followUpTimer);
  followUpActive = wakeMode;
  engagedActive = true;
  if (wakeMode && status.textContent === 'STANDBY') status.textContent = FOLLOWUP_STATUS_TEXT;
  followUpTimer = setTimeout(expireFollowUpWindow, FOLLOWUP_MS);
}

// เรียกตอนเงียบเกิน 15 วิจริงๆ เท่านั้น -> ถือว่าเลิกคุยแล้ว กลับสีเดิม ต้องเรียก "Friday" ใหม่
function expireFollowUpWindow() {
  clearTimeout(followUpTimer);
  followUpActive = false;
  engagedActive = false;
  if (status.textContent === FOLLOWUP_STATUS_TEXT) status.textContent = 'STANDBY';
  // คุยกับ Friday จบแล้ว (พูดจบ + เงียบครบ 15 วิ ไม่มีถามต่อ) — ถ้าเมื่อกี้ย่อจอ YouTube ไว้เพราะโดนเรียก
  // ให้กลับไปเต็มจอเหมือนเดิม (เว้นแต่เพลงถูกปิดไปแล้ว — เช็คจาก .visible)
  if (ytWasMaximizedBeforeEngage) {
    ytWasMaximizedBeforeEngage = false;
    if (ytPlayer && ytPanel.classList.contains('visible')) requestYoutubeFullscreen();
  }
}

// เรียกตอนมีคนพูดต่อจริงๆ ภายใน 15 วิ (ยังคุยกันต่อ ไม่ใช่หมดเวลา) engagedActive เลยยังคงเป็น true ต่อ
function consumeFollowUpWindow() {
  clearTimeout(followUpTimer);
  followUpActive = false;
  if (status.textContent === FOLLOWUP_STATUS_TEXT) status.textContent = 'STANDBY';
}

// ผู้ใช้ขอให้รอ 5 วิหลังพูดจบก่อนค่อยส่งคำสั่งจริง เผื่อพูดต่อ (เดิมพอ recognition ตัดจบประโยคแรก
// ทันทีตอนหยุดพูดแป๊บนึงคิดคำ ระบบส่งคำสั่งที่ยังพูดไม่จบไปเลย) ทุกครั้งที่ได้ยินเสียงเพิ่มระหว่างรอ
// จะเอามาต่อท้ายแล้วรีเซ็ตนาฬิกา 5 วิใหม่ จนกว่าจะเงียบจริงๆ ถึงส่งเป็นข้อความเดียว
const COMMAND_DEBOUNCE_MS = 5000;
let pendingCommandText = '';
let commandDebounceTimer = null;
let isAccumulatingCommand = false; // true ระหว่างรอ debounce — ให้พูดต่อได้โดยไม่ต้องพูด "Friday" ซ้ำ

function queueWakeCommand(text) {
  pendingCommandText = pendingCommandText ? `${pendingCommandText} ${text}` : text;
  isAccumulatingCommand = true;
  engagedActive = true;
  clearTimeout(followUpTimer); // กันช่วงคุยต่อเนื่อง 15 วิเดิมหมดอายุกลางคันตอนกำลังรอฟังต่อ
  clearTimeout(commandDebounceTimer);
  commandDebounceTimer = setTimeout(flushWakeCommand, COMMAND_DEBOUNCE_MS);
}

function flushWakeCommand() {
  commandDebounceTimer = null;
  isAccumulatingCommand = false;
  const text = pendingCommandText.trim();
  pendingCommandText = '';
  if (!text) return;
  consumeFollowUpWindow(); // เคลียร์ state ช่วงคุยต่อเนื่องเดิมก่อนส่งจริง เผื่อยังตั้งค้างอยู่
  input.value = text;
  form.requestSubmit();
}

// ปิดไมค์จริงๆ ตอน FRIDAY พูด (ไม่ใช่แค่เช็ค flag) กัน STT หยิบเสียงตัวเองมาตีความ
// ข้อแลกเปลี่ยน: แทรกกลางประโยคไม่ได้ ต้องรอพูดจบก่อน — เคยลองแบบเทียบข้อความเสียงสะท้อนโดยไม่ปิดไมค์
// (ไม่ต้องรอ TTS จบ แทรกได้ทันที) แต่ไม่น่าเชื่อถือพอในสถานการณ์จริง เพราะ STT แปลงเสียงสะท้อนออกมาเพี้ยนบ่อย
// แผนในอนาคต: ใช้ getUserMedia({echoCancellation:true}) + STT backend จริง (เช่น Whisper) แทน
// ถึงจะแทรกกลางประโยคได้แบบเชื่อถือได้ ตอนนี้พอไม่ไหวก่อน
const TTS_RESUME_DELAY_MS = 500; // กันเสียงสะท้อน/หางเสียงจากลำโพงหลุดเข้าไมค์หลัง TTS จบ

function pauseWakeListening() {
  clearTimeout(wakeRestartTimer);
  if (wakeRecognition) {
    wakeRecognition.onend = null; // กัน onend เดิมสั่ง restart ซ้อนกับ resumeWakeListeningAfterDelay
    try {
      wakeRecognition.stop();
    } catch (err) {
      // เผื่อ stop() ซ้อนกับ state ที่ยังไม่พร้อม ปล่อยผ่านได้ ไม่กระทบอะไร
    }
  }
}

function resumeWakeListeningAfterDelay(delayMs = TTS_RESUME_DELAY_MS) {
  if (!wakeMode) return;
  clearTimeout(wakeRestartTimer);
  wakeRestartTimer = setTimeout(runWakeRecognition, delayMs);
}

function runWakeRecognition() {
  if (!wakeMode || !SpeechRecognitionCtor) return;

  wakeRecognition = new SpeechRecognitionCtor();
  wakeRecognition.lang = 'th-TH';
  wakeRecognition.interimResults = false;
  wakeRecognition.continuous = true;

  wakeRecognition.onresult = (e) => {
    if (ttsSpeaking) return; // เผื่อผลลัพธ์หลุดมาในช่วงเสี้ยววินาทีก่อน stop() มีผลจริง กันไว้อีกชั้น
    const result = e.results[e.results.length - 1];
    if (!result.isFinal) return;
    const transcript = result[0].transcript.trim();
    if (!transcript) return;

    // ระหว่างเพลง YouTube กำลังเล่นอยู่จริง (state จริงจาก YT.Player ไม่ใช่เดาเอง) ห้ามข้ามการพูด
    // "Friday" นำแม้จะอยู่ในช่วงคุยต่อเนื่อง/กำลังรอฟังต่อก็ตาม กันเนื้อเพลง/เสียงร้องถูกตีความเป็น
    // คำสั่งมั่วๆ — ปล่อยให้ตกไปเช็ค extractWakeCommand() ข้างล่างแทน ต้องมีคำว่า "Friday" อยู่จริง
    if ((followUpActive || isAccumulatingCommand) && !ytIsPlaying) {
      // อยู่ในช่วงคุยต่อเนื่อง หรือกำลังรอ debounce 5 วิเผื่อพูดต่ออยู่ พูดอะไรมาก็ถือเป็นส่วนหนึ่งของ
      // คำสั่งเดิมเลย ไม่ต้องพูด "Friday" ซ้ำ — queueWakeCommand() เอง (ไม่ส่งทันที รอ 5 วิเผื่อพูดต่อ)
      queueWakeCommand(transcript);
      return;
    }

    const command = extractWakeCommand(transcript);
    if (command === null) {
      // เก็บ log ไว้เผื่อ debug กรณี "พูด Friday แล้วไม่ติด" — บางทีสาเหตุคือ Google STT ถอดเสียง
      // "Friday" เป็นคำไทยที่สะกดต่างจาก WAKE_WORD_PATTERNS ที่มี ไม่ใช่ปัญหาจังหวะ/ไมค์เลย
      // เปิด DevTools console (F12) ดู "[wake] missed:" เทียบว่า STT ได้ยินเป็นคำว่าอะไรจริงๆ
      console.debug('[wake] missed:', transcript);
      return; // ไม่มีคำว่า Friday ในประโยคนี้ ข้ามไป
    }
    if (!command) {
      // เรียกชื่อเฉยๆ ไม่มีคำสั่งตาม -> ตอบรับด้วยเสียงจริง พอตอบเสร็จ (ไมค์เปิดกลับมาเอง) ค่อยรอฟังคำถามต่อ
      // โดยไม่ต้องพูด "Friday" ซ้ำ (ใช้กลไกช่วงคุยต่อเนื่องเดิม)
      // นับ 15 วิ "หลังเสียงพูดหยุดจริง" (ผ่าน callback ตอน speak() จบ) ไม่ใช่นับตั้งแต่เริ่มพูด
      // ไม่งั้นถ้าประโยคยาวจะโดนกินเวลาไปตั้งแต่ตอนยังพูดไม่จบ
      engagedActive = true; // ได้ยินคำว่า "Friday" แล้ว เขียวทันที ไม่ต้องรอพูดจบ
      const ack = WAKE_ACK_PHRASES[Math.floor(Math.random() * WAKE_ACK_PHRASES.length)];
      addLine('friday', ack);
      speak(ack, () => {
        if (wakeMode) startFollowUpWindow();
      });
      return;
    }
    // ได้ยินคำว่า "Friday" + คำสั่งแล้ว — ยังไม่ส่งทันที รอ 5 วิเผื่อพูดต่อ (queueWakeCommand ตั้ง
    // engagedActive/isAccumulatingCommand ให้เองแล้ว พูดต่อโดยไม่ต้องพูด "Friday" ซ้ำได้เลยในช่วงนี้)
    queueWakeCommand(command);
  };

  wakeRecognition.onerror = (e) => {
    if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
      stopWakeMode();
      announceSystemNotice('ขออนุญาตใช้ไมโครโฟนก่อนนะคะ ถึงจะเปิดโหมดฟังตลอดได้');
    }
    // no-speech / aborted / network ปล่อยให้ onend restart ให้เอง
  };

  wakeRecognition.onend = () => {
    if (wakeMode) {
      // เดิมหน่วง 250ms ก่อน restart — Chrome ตัดจบ session ของ continuous:true เองเป็นระยะแม้ไม่มี
      // error เลย (พฤติกรรมปกติของ Web Speech API ไม่ใช่แค่ตอน error) รอบ restart แบบนี้เลยเกิดขึ้น
      // บ่อยมากตอนใช้งานจริง ไม่ใช่กรณีพิเศษ — ช่วง 250ms ที่ไมค์ "หูหนวก" สนิทนี้แหละคือสาเหตุที่
      // พูด "Friday" คำเดียว (สั้นแค่ ~300-500ms) แล้วบางทีไม่ติดเลย เพราะจังหวะพูดดันตรงกับช่วงรีสตาร์ท
      // พอดี — ลดเหลือ RESTART_DELAY_MS สั้นลงมากเพื่อลดโอกาสพลาดแบบนี้ (ยังเหลือกันชนเล็กน้อยกัน
      // Chrome โยน "recognition already started" ถ้า start() ใหม่เร็วเกินไปก่อน browser คืนทรัพยากรไมค์)
      wakeRestartTimer = setTimeout(runWakeRecognition, WAKE_RESTART_DELAY_MS);
    }
  };

  try {
    wakeRecognition.start();
  } catch (err) {
    // start() ซ้อนกันได้ (เช่นช่วงสลับโหมด, หรือ browser ยังไม่คืนทรัพยากรไมค์จาก session ก่อนหน้า)
    // ลองใหม่อีกรอบสั้นๆ กันเคสที่ onend ของ session เดิมไม่มีทางยิงมาช่วยรีสตาร์ทให้ (session นี้ไม่เคย
    // start จริงเลยด้วยซ้ำ) ซึ่งจะทำให้โหมดฟังตลอดค้างเงียบไปเฉยๆ โดยไม่มี error ให้เห็นเลย
    if (wakeMode) wakeRestartTimer = setTimeout(runWakeRecognition, WAKE_RESTART_DELAY_MS);
  }
}

function startWakeMode() {
  if (!SpeechRecognitionCtor) return;
  if (listening) recognition.stop(); // เลิกโหมดกดพูดถ้าค้างอยู่
  wakeMode = true;
  wakeBtn.classList.add('active');
  micBtn.disabled = true;
  runWakeRecognition();
}

function stopWakeMode() {
  wakeMode = false;
  wakeBtn.classList.remove('active');
  micBtn.disabled = false;
  clearTimeout(wakeRestartTimer);
  expireFollowUpWindow();
  // กันคำสั่งที่กำลังรอ debounce 5 วิอยู่หลุดออกไปส่งทีหลัง ทั้งที่ปิดโหมดฟังตลอดไปแล้ว
  clearTimeout(commandDebounceTimer);
  pendingCommandText = '';
  isAccumulatingCommand = false;
  if (wakeRecognition) {
    wakeRecognition.onend = null; // กัน trigger restart ตอนสั่งปิดเอง
    wakeRecognition.stop();
  }
}

if (SpeechRecognitionCtor) {
  wakeBtn.addEventListener('click', () => {
    if (wakeMode) stopWakeMode();
    else startWakeMode();
  });
}

/* ---------- boot sequence ---------- */

const BOOT_LINES = [
  '> INITIALIZING F.R.I.D.A.Y CORE...',
  '> LOADING NEURAL MODULES........ OK',
  '> CONNECTING GEMINI LINK......... OK',
  '> SEARCH MODULE.................. OK',
  '> VOICE INTERFACE................ OK',
  '> SYSTEM ONLINE',
];

function runBoot() {
  let line = 0;
  let char = 0;
  let buffer = '';

  function typeNext() {
    if (line >= BOOT_LINES.length) {
      setTimeout(() => bootOverlay.classList.add('hidden'), 350);
      return;
    }
    const current = BOOT_LINES[line];
    if (char <= current.length) {
      bootText.textContent = buffer + current.slice(0, char) + '▌';
      char++;
      setTimeout(typeNext, 12);
    } else {
      buffer += current + '\n';
      bootText.textContent = buffer;
      line++;
      char = 0;
      setTimeout(typeNext, 180);
    }
  }
  typeNext();
}

/* ---------- particle field (ตกแต่งบรรยากาศ ไม่ใช่ panel ข้อมูล) ---------- */

const canvas = document.getElementById('particles');
const ctx = canvas.getContext('2d');
let particles = [];

function resizeCanvas() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
}

function initParticles() {
  const count = Math.round((window.innerWidth * window.innerHeight) / 18000);
  particles = Array.from({ length: count }, () => ({
    x: Math.random() * canvas.width,
    y: Math.random() * canvas.height,
    r: Math.random() * 1.6 + 0.4,
    vx: (Math.random() - 0.5) * 0.15,
    vy: (Math.random() - 0.5) * 0.15,
    a: Math.random() * 0.5 + 0.15,
  }));
}

function drawParticles() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  for (const p of particles) {
    p.x += p.vx;
    p.y += p.vy;
    if (p.x < 0) p.x = canvas.width;
    if (p.x > canvas.width) p.x = 0;
    if (p.y < 0) p.y = canvas.height;
    if (p.y > canvas.height) p.y = 0;

    ctx.beginPath();
    ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(77, 246, 255, ${p.a})`;
    ctx.fill();
  }
  requestAnimationFrame(drawParticles);
}

resizeCanvas();
initParticles();
drawParticles();
window.addEventListener('resize', () => {
  resizeCanvas();
  initParticles();
});

/* ---------- แกนกลางเอียงลอยเองตลอดเวลา (ไม่หันตามเมาส์แล้ว) ---------- */
// รอบแรกลองสุ่มมุมเป้าหมายใหม่เป็นช่วงๆ (jump ทุก 4-9 วิ) แต่ผู้ใช้ feedback ว่าดูนิ่งเกินไปไม่มีชีวิตชีวา
// เปลี่ยนมาขยับ "ตลอดเวลา" ทุกเฟรมแทน โดยผสมคลื่น sine 2 แกน (X/Y) คนละคาบเวลากัน (Lissajous curve)
// ทำให้เส้นทางการเอียงดูคดเคี้ยวเป็นธรรมชาติ ไม่ใช่วนเป็นวงกลมซ้ำๆ แบบเครื่องจักร — สุ่มคาบ/เฟสตอนโหลด
// หน้าเว็บแต่ละครั้งด้วย เลยได้จังหวะไม่ซ้ำกันทุกครั้งที่เปิดหน้าเว็บใหม่ตามที่ขอ ("สุ่มทิศทางช้าๆ")

const IDLE_TILT_MAX_DEG = 7;
const idleTiltPhaseX = Math.random() * Math.PI * 2;
const idleTiltPhaseY = Math.random() * Math.PI * 2;
const idleTiltPeriodX = 13000 + Math.random() * 7000; // ms ต่อรอบคลื่นเต็ม (13-20 วิ)
const idleTiltPeriodY = 17000 + Math.random() * 9000; // คาบต่างจากแกน X เจตนา กันดูเป็นวงกลมซ้ำ (17-26 วิ)

function renderIdleTilt(now) {
  requestAnimationFrame(renderIdleTilt);
  const rotX = Math.sin(((now / idleTiltPeriodX) * Math.PI * 2) + idleTiltPhaseX) * IDLE_TILT_MAX_DEG;
  const rotY = Math.sin(((now / idleTiltPeriodY) * Math.PI * 2) + idleTiltPhaseY) * IDLE_TILT_MAX_DEG;
  coreWrap.style.transform = `rotateX(${rotX.toFixed(2)}deg) rotateY(${rotY.toFixed(2)}deg)`;
}
requestAnimationFrame(renderIdleTilt);

/* ---------- นาฬิกาจริง ---------- */

function updateClock() {
  const now = new Date();
  clockTime.textContent = now.toLocaleTimeString('th-TH', { hour12: false });
  clockDate.textContent = now.toLocaleDateString('th-TH', { day: 'numeric', month: 'short', year: 'numeric' });
}
updateClock();
setInterval(updateClock, 1000);

/* ---------- กราฟเวลาตอบสนอง: ข้อมูลจริงจากการวัดรอบ fetch แต่ละครั้ง ---------- */

const latencyHistory = [];
const LATENCY_MAX_POINTS = 10;

function recordLatency(ms) {
  latencyHistory.push(ms);
  if (latencyHistory.length > LATENCY_MAX_POINTS) latencyHistory.shift();
  renderLatencyGraph();
}

function renderLatencyGraph() {
  if (latencyHistory.length === 0) {
    latencyEmpty.style.display = 'block';
    latencyPoly.setAttribute('points', '');
    latencyLast.textContent = '--';
    return;
  }
  latencyEmpty.style.display = 'none';
  const w = 120;
  const h = 36;
  const pad = 3;
  const max = Math.max(...latencyHistory, 1000); // ตั้งพื้นสเกลไว้ 1 วิ กันกราฟดูสูงเวอร์ตอนค่าน้อยมาก แต่ปรับตามค่าจริงถ้าเกิน
  const points = latencyHistory
    .map((v, i) => {
      const x = latencyHistory.length === 1 ? w / 2 : (i / (latencyHistory.length - 1)) * w;
      const y = h - pad - (v / max) * (h - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
  latencyPoly.setAttribute('points', points);
  latencyLast.textContent = `${(latencyHistory[latencyHistory.length - 1] / 1000).toFixed(1)}s`;
}

renderLatencyGraph();

/* ---------- quota gauge: สัดส่วนแท่งที่ติด = โควตาที่ใช้จริงจาก /api/quota ---------- */

function renderQuotaGauge(q) {
  if (q.limit == null) {
    // ยังไม่รู้ limit จริง เลยไม่เดาสัดส่วน ปล่อยแท่งดับไว้ตรงๆ ไม่ทำให้เข้าใจผิดว่ารู้ค่าที่ยังไม่รู้
    quotaBars.forEach((bar) => bar.classList.remove('lit', 'warn'));
    quotaGaugeLabel.textContent = `QUOTA USAGE · ใช้ ${q.used} ครั้ง`;
    return;
  }
  const frac = Math.min(1, q.used / q.limit);
  const litCount = Math.round(frac * quotaBars.length);
  const warn = frac >= 0.8;
  quotaBars.forEach((bar, i) => {
    bar.classList.toggle('lit', i < litCount);
    bar.classList.toggle('warn', i < litCount && warn);
  });
  quotaGaugeLabel.textContent = `QUOTA ${q.used}/${q.limit}`;
}

/* ---------- สถานะการเชื่อมต่อกับ server: heartbeat จริงจากผลของการ poll ---------- */

function setLinkHealthy(ok) {
  radarSweep.classList.toggle('lost', !ok);
  linkStatus.textContent = ok ? 'LINK OK' : 'LINK LOST';
  linkStatus.classList.toggle('lost', !ok);
}

/* ---------- แชท ---------- */

// เบราว์เซอร์จริง (ไม่เหมือน browser automation) มักบล็อก window.open() เงียบๆ ถ้าไม่ได้เกิดใกล้ๆ
// user gesture จริง (โดยเฉพาะตอนสั่งผ่านเสียง/wake mode ที่ไม่มี gesture เลย) — window.open() คืนค่า
// null ตอนโดนบล็อกแบบนี้ (ไม่ throw error) เลยตรวจแล้วเพิ่มลิงก์ให้กดเองเป็น fallback กันดูเหมือน
// "ใช้ไม่ได้" ทั้งที่จริงๆ backend ทำงานถูกแล้วแค่โดนเบราว์เซอร์เงียบๆ บล็อกไว้
//
// เจตนาไม่ใส่ 'noopener'/'noreferrer' ตรงนี้ (ต่างจากปกติที่ควรใส่เสมอ) เพราะ 2 อันนี้ทำให้
// window.open() คืนค่า null เสมอไม่ว่าจะเปิดสำเร็จหรือโดนบล็อกก็ตาม (ทดสอบยืนยันแล้ว) เลยใช้แยกแยะ
// ไม่ได้เลยถ้าใส่ไว้ — ยอมรับความเสี่ยงได้เพราะ url ที่เปิดมาจาก tools.py เอง ล็อกโดเมนไว้ที่
// youtube.com ตายตัวเสมอ (ดู CLAUDE.md) ไม่ใช่ url จากที่อื่นที่ควบคุมไม่ได้
function openUrlWithFallback(url) {
  const win = window.open(url, '_blank');
  if (!win || win.closed) {
    addLinkLine(url);
  }
}

function addLinkLine(url) {
  const div = document.createElement('div');
  div.className = 'friday-link';
  const a = document.createElement('a');
  a.href = url;
  a.target = '_blank';
  a.rel = 'noopener noreferrer';
  a.textContent = 'เบราว์เซอร์บล็อกการเปิดแท็บอัตโนมัติ — กดตรงนี้เพื่อเปิดเองค่ะ';
  div.appendChild(a);
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

/* ---------- เครื่องเล่น YouTube: ฝัง IFrame Player จริงในหน้า (ไม่ใช่เปิดแท็บแยก) เพื่อให้
   สั่งหยุด/เล่นต่อ/เปลี่ยนเพลงจากโค้ดเราได้จริง — แท็บที่เปิดแยกจาก window.open() สั่งควบคุมจาก
   ภายนอกไม่ได้เลย (คนละ browsing context) วิดีโอที่เล่นมาจาก yt_dlp ค้นหาจริงฝั่ง server (tools.py)
   ไม่ใช่ของสุ่ม/ปลอม ---------- */

let ytPlayer = null;
let ytApiReady = false;
let ytPlayerReady = false; // true หลัง onReady event จริงเท่านั้น — เมธอดของ YT.Player (setVolume ฯลฯ)
// ใช้งานไม่ได้แน่นอนก่อนหน้านี้ แม้ตัว object จะคืนกลับมาจาก `new YT.Player()` ทันทีแบบ synchronous แล้ว
// ก็ตาม (ตัว iframe ข้างในยังไม่ได้เชื่อมต่อ postMessage เสร็จ) เป็นเรื่องจริงที่เอกสาร YouTube ระบุไว้
let ytPendingVideo = null; // {id, title} รอเล่นถ้ายังโหลด IFrame API/player ไม่เสร็จตอนสั่งมา
let ytPendingCommand = null; // action ล่าสุดที่รอทำ ถ้า controlYoutube() ถูกเรียกก่อน player ready จริง
let ytIsPlaying = false; // สถานะจริงจาก YT.Player onStateChange event (ไม่ใช่แค่เดาจากว่าสั่ง playVideo() ไปแล้ว)
let ytVolume = 100; // baseline volume ที่ผู้ใช้ตั้งไว้ล่าสุดผ่าน volume_up/volume_down (คนละตัวกับตอน duck ชั่วคราว)
// หูมนุษย์รับรู้ความดังแบบ logarithmic ไม่ใช่ linear — ทดสอบยืนยันแล้วว่า setVolume() บน player จริง
// เปลี่ยนค่าไปตรงตามที่สั่งเป๊ะ (100->80 จริง) แต่ผู้ใช้รายงานว่า "สั่งลดแล้วไม่รู้สึกว่าลดเลย" เพราะ
// step เดิม (20) เล็กเกินไปจนหูแทบไม่รู้สึกถึงความต่าง — ปรับเป็น 25 ให้รู้สึกถึงการเปลี่ยนแปลงชัดเจนขึ้น
const YT_VOLUME_STEP = 25;

function loadYtApiScript() {
  if (document.getElementById('yt-iframe-api')) return;
  const tag = document.createElement('script');
  tag.id = 'yt-iframe-api';
  tag.src = 'https://www.youtube.com/iframe_api';
  document.head.appendChild(tag);
}

window.onYouTubeIframeAPIReady = function onYouTubeIframeAPIReady() {
  ytApiReady = true;
  if (ytPendingVideo) {
    const { id, title } = ytPendingVideo;
    ytPendingVideo = null;
    playYoutubeVideo(id, title);
  }
};

function playYoutubeVideo(videoId, title) {
  ytPanelTitle.textContent = title || videoId;
  ytPanel.classList.add('visible');

  if (!ytApiReady || (ytPlayer && !ytPlayerReady)) {
    // ยังโหลด script ไม่เสร็จ หรือ player ตัวเดิมยังไม่ ready จริง (รอ onReady) — เก็บคิวไว้ก่อน
    loadYtApiScript();
    ytPendingVideo = { id: videoId, title };
    return;
  }

  if (ytPlayer && typeof ytPlayer.loadVideoById === 'function') {
    ytPlayer.loadVideoById(videoId);
    return;
  }

  ytPlayer = new YT.Player(ytPlayerMount, {
    videoId,
    playerVars: { autoplay: 1, playsinline: 1 },
    events: { onReady: onYtPlayerReady, onStateChange: onYtStateChange },
  });
}

// onReady ยิงแค่ครั้งเดียวตอนสร้าง player ใหม่เท่านั้น (ไม่ยิงซ้ำตอน loadVideoById เปลี่ยนเพลง) —
// พอ ready แล้วค้างเป็น true ตลอดอายุ player ตัวนี้ ทำคิวที่ค้างไว้ระหว่างรอให้เรียบร้อย (ถ้ามี)
function onYtPlayerReady() {
  ytPlayerReady = true;
  if (ytPendingVideo) {
    const { id, title } = ytPendingVideo;
    ytPendingVideo = null;
    playYoutubeVideo(id, title);
  }
  if (ytPendingCommand) {
    const cmd = ytPendingCommand;
    ytPendingCommand = null;
    controlYoutube(cmd);
  }
}

// ตอนเพลงเล่นอยู่จริง (state จริงจาก YouTube เอง ไม่ใช่เดาเอง) ระงับช่วงคุยต่อเนื่อง 15 วิ
// (ที่ปกติไม่ต้องพูด "Friday" ซ้ำ) ไปก่อน กันเสียงร้อง/เนื้อเพลงถูกตีความเป็นคำสั่งมั่วๆ ดู
// เงื่อนไข !ytIsPlaying ใน wakeRecognition.onresult — ต้องพูด "Friday" นำทุกครั้งระหว่างเพลงเล่นอยู่
function onYtStateChange(event) {
  ytIsPlaying = event.data === YT.PlayerState.PLAYING;
}

function controlYoutube(action) {
  if (!ytPlayer) return; // ยังไม่เคยเปิดเพลงอะไรเลย ไม่มีอะไรให้คุม
  if (!ytPlayerReady) {
    // player กำลังโหลดอยู่ ยังสั่งจริงไม่ได้ (เมธอดของ YT.Player ใช้ไม่ได้จริงก่อน onReady แม้ตัว
    // object จะมีอยู่แล้วก็ตาม) รอไว้ก่อน พอ ready แล้ว onYtPlayerReady() จะทำคำสั่งนี้ให้เอง
    // (คำสั่งล่าสุดชนะ ไม่ใช่คิวสะสม — พอเพียงสำหรับ use case นี้)
    ytPendingCommand = action;
    return;
  }
  if (action === 'pause' && typeof ytPlayer.pauseVideo === 'function') {
    ytPlayer.pauseVideo();
    ytIsPlaying = false; // ไม่ต้องรอ onStateChange async กลับมา ตั้งทันทีกันช่วง follow-up ปลดล็อกเร็วเกินจริง
  } else if (action === 'resume' && typeof ytPlayer.playVideo === 'function') {
    ytPlayer.playVideo();
  } else if (action === 'stop') {
    if (typeof ytPlayer.stopVideo === 'function') ytPlayer.stopVideo();
    ytIsPlaying = false;
    ytVolume = 100; // เริ่มเซสชันฟังเพลงครั้งถัดไปที่ 100% เสมอ ไม่ค้างค่าที่เคยปรับไว้ข้ามเซสชันเก่า
    exitYoutubeFullscreen(); // ปิดเพลง -> ออกจากเต็มจอ + ยกเลิกแผนกลับไปเต็มจอ (ไม่ให้ค้างจอดำ/เด้งกลับ)
    ytPanel.classList.remove('visible');
  } else if (action === 'volume_up' || action === 'volume_down') {
    const delta = action === 'volume_up' ? YT_VOLUME_STEP : -YT_VOLUME_STEP;
    ytVolume = Math.max(0, Math.min(100, ytVolume + delta));
    // ถ้า FRIDAY กำลังพูดอยู่ (duck ค้างที่ YT_DUCK_VOLUME) อย่าเพิ่งใช้ค่าใหม่ทับตอนนี้ กันเสียงเพลง
    // ดังแทรกขึ้นมากลางที่ FRIDAY พูดอยู่ — เก็บ ytVolume ไว้ก่อน พอ TTS จบ restoreYoutubeVolume()
    // จะหยิบค่าล่าสุดไปใช้เอง
    if (!ttsSpeaking) restoreYoutubeVolume();
  } else if (action === 'fullscreen') {
    requestYoutubeFullscreen();
  } else if (action === 'exit_fullscreen') {
    exitYoutubeFullscreen();
  }
}

/* "เต็มจอ" = ขยายเครื่องเล่น YouTube ให้เต็ม viewport ของเบราว์เซอร์ด้วย CSS (คลาส .maximized บน
   #ytPanel) — ทำงานทันทีเสมอ ไม่ต้องมี user gesture เลย สั่งผ่านเสียงได้จริง (ต่างจาก Fullscreen API
   ที่ต้องมี gesture) ถ้าบังเอิญมี gesture อยู่ (พิมพ์คำสั่ง + Enter) จะลองขอ real fullscreen ซ้อนให้
   ด้วยเพื่อซ่อนแถบเบราว์เซอร์ — ไม่ได้ก็ไม่เป็นไร CSS ทำให้เต็มจอเบราว์เซอร์ไปแล้ว */

let ytMaximized = false;
let ytWasMaximizedBeforeEngage = false; // ย่อจอชั่วคราวเพราะผู้ใช้เรียก Friday -> กลับไปเต็มจอตอนคุยจบ (expireFollowUpWindow)

function ytFullscreenTarget() {
  if (ytPlayer && typeof ytPlayer.getIframe === 'function') {
    try {
      const f = ytPlayer.getIframe();
      if (f) return f;
    } catch (err) { /* getIframe เรียกก่อน player พร้อมได้ ปล่อยไปใช้ตัวสำรองข้างล่าง */ }
  }
  return document.getElementById('ytPlayerMount'); // YT API แทน div ด้วย <iframe> ที่ใช้ id เดิม — lookup ใหม่ ไม่ใช้ตัวแปรเก่าที่ค้าง
}

function doRequestFullscreen(el) {
  const req = el && (el.requestFullscreen || el.webkitRequestFullscreen || el.msRequestFullscreen);
  if (!req) return Promise.reject(new Error('no fullscreen api'));
  try {
    return Promise.resolve(req.call(el));
  } catch (err) {
    return Promise.reject(err);
  }
}

function requestYoutubeFullscreen() {
  if (!ytPanel) return;
  ytMaximized = true;
  ytPanel.classList.add('maximized');
  // bonus: ขอ real fullscreen ถ้ามี gesture (พิมพ์คำสั่ง) — สั่งด้วยเสียงจะ reject เฉยๆ ไม่ต้องทำอะไรต่อ
  doRequestFullscreen(ytFullscreenTarget()).catch(() => {});
}

function exitYoutubeFullscreen() {
  ytMaximized = false;
  ytWasMaximizedBeforeEngage = false; // สั่งออกชัดเจน (ผู้ใช้/ระบบ) -> ยกเลิกแผนกลับไปเต็มจออัตโนมัติด้วย
  if (ytPanel) ytPanel.classList.remove('maximized');
  if (document.fullscreenElement && document.exitFullscreen) {
    document.exitFullscreen().catch(() => {});
  } else if (document.webkitFullscreenElement && document.webkitExitFullscreen) {
    document.webkitExitFullscreen();
  }
}

if (ytExitFs) ytExitFs.addEventListener('click', exitYoutubeFullscreen);

// กด Esc = ออกจากเต็มจอ / ยกเลิกการกลับไปเต็มจออัตโนมัติ (นอกจากสั่งด้วยเสียง "ออกจากเต็มจอ") เผื่อ STT ฟังไม่ติด
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && (ytMaximized || ytWasMaximizedBeforeEngage)) exitYoutubeFullscreen();
});
// ผู้ใช้กด Esc ออกจาก real fullscreen (ที่ขอซ้อนไว้) -> เลิก .maximized ด้วย ไม่ให้ค้างเต็มจอครึ่งๆ
document.addEventListener('fullscreenchange', () => {
  if (!document.fullscreenElement && ytMaximized) exitYoutubeFullscreen();
});

/* ---------- สภาพอากาศ: ข้อมูลจริงจาก Open-Meteo ทั้งหมด (คำนวณ/แปล emoji มาจาก server แล้ว
   ดู tools.py) ฝั่งนี้แค่เอาไปแปะแสดงผลตรงๆ ไม่มีการเดา/เติมค่าเองเลย ---------- */

const WEATHER_DAY_NAMES = ['อา', 'จ', 'อ', 'พ', 'พฤ', 'ศ', 'ส'];

// ปิด panel เองอัตโนมัติ 30 วิ "หลัง FRIDAY พูดตอบจบจริง" (ไม่ใช่หลังได้ข้อมูลมา) ผู้ใช้ขอไว้ — เรียก
// scheduleWeatherHide() จาก onDone callback ของ speak() เดียวกับที่คุมช่วงคุยต่อเนื่อง 15 วิ ตรงกับ
// pattern เดิมของโปรเจกต์ (นับเวลาจากเสียงพูดหยุดจริง ไม่ใช่จากตอนได้คำตอบมา)
const WEATHER_AUTO_HIDE_MS = 30000;
let weatherHideTimer = null;

function scheduleWeatherHide() {
  clearTimeout(weatherHideTimer);
  weatherHideTimer = setTimeout(() => {
    weatherPanel.classList.remove('visible');
  }, WEATHER_AUTO_HIDE_MS);
}

// สร้าง element ของ animation พื้นหลังตาม "หมวดสภาพอากาศจริง" ที่ tools.py คำนวณมาให้ (data.fx)
// เท่านั้น ไม่ใช่ของสุ่มเล่นๆ ที่ไม่เกี่ยวกับข้อมูลจริง — ใช้ negative animation-delay สุ่มให้แต่ละ
// element เริ่มจากจุดกลางๆ ของ cycle ตัวเองทันที กันทุกเม็ดฝน/เกล็ดหิมะเริ่มพร้อมกันแข็งๆ ตอนโผล่มา
function renderWeatherFx(category) {
  weatherFx.innerHTML = '';
  weatherFx.className = 'weather-fx' + (category ? ` fx-${category}` : '');

  const rand = (min, max) => min + Math.random() * (max - min);

  if (category === 'cloudy') {
    for (let i = 0; i < 3; i++) {
      const cloud = document.createElement('div');
      cloud.className = 'fx-cloud-shape';
      cloud.style.top = `${rand(20, 90)}px`;
      cloud.style.animationDuration = `${rand(12, 20)}s`;
      cloud.style.animationDelay = `${rand(-10, 0)}s`;
      weatherFx.appendChild(cloud);
    }
  } else if (category === 'fog') {
    for (let i = 0; i < 3; i++) {
      const band = document.createElement('div');
      band.className = 'fx-fog-band';
      band.style.top = `${rand(20, 100)}px`;
      band.style.animationDuration = `${rand(8, 14)}s`;
      band.style.animationDelay = `${rand(-6, 0)}s`;
      weatherFx.appendChild(band);
    }
  } else if (category === 'rain' || category === 'storm') {
    for (let i = 0; i < 16; i++) {
      const drop = document.createElement('div');
      drop.className = 'fx-raindrop';
      drop.style.left = `${rand(0, 100)}%`;
      drop.style.animationDuration = `${rand(0.5, 0.9)}s`;
      drop.style.animationDelay = `${rand(-1, 0)}s`;
      weatherFx.appendChild(drop);
    }
    if (category === 'storm') {
      const flash = document.createElement('div');
      flash.className = 'fx-flash';
      weatherFx.appendChild(flash);
    }
  } else if (category === 'snow') {
    for (let i = 0; i < 14; i++) {
      const flake = document.createElement('span');
      flake.className = 'fx-snowflake';
      flake.textContent = '❄';
      flake.style.left = `${rand(0, 100)}%`;
      flake.style.animationDuration = `${rand(4, 7)}s`;
      flake.style.animationDelay = `${rand(-5, 0)}s`;
      flake.style.setProperty('--fx-drift', `${rand(-20, 20)}px`);
      weatherFx.appendChild(flake);
    }
  }
  // sunny: ไม่ต้องสร้าง element เพิ่ม แสงเปล่งมาจาก CSS ::before ของ .fx-sunny เอง (ดู style.css)
}

function showWeather(data) {
  clearTimeout(weatherHideTimer); // ถามอากาศที่ใหม่ระหว่างนับถอยหลังเดิมอยู่ -> เคลียร์ตัวเก่าทิ้งก่อน
  renderWeatherFx(data.fx);
  weatherLocation.textContent = data.location || '-';
  weatherEmoji.textContent = data.emoji || '❓';
  weatherTemp.textContent = data.temperature != null ? `${data.temperature}°` : '--°';
  weatherCondition.textContent = data.condition || '-';
  weatherFeelsLike.textContent = data.feels_like != null ? `รู้สึกเหมือน ${data.feels_like}°` : '';
  weatherHumidity.textContent = data.humidity != null ? `ความชื้น ${data.humidity}%` : '';
  weatherWind.textContent = data.wind_speed != null ? `ลม ${data.wind_speed} กม./ชม.` : '';

  weatherForecast.innerHTML = '';
  (data.forecast || []).forEach((day) => {
    const div = document.createElement('div');
    div.className = 'weather-forecast-day';

    const label = document.createElement('span');
    const d = new Date(`${day.date}T00:00:00`);
    label.textContent = Number.isNaN(d.getTime()) ? '-' : WEATHER_DAY_NAMES[d.getDay()];

    const emoji = document.createElement('span');
    emoji.className = 'fc-emoji';
    emoji.textContent = day.emoji || '❓';

    const maxEl = document.createElement('span');
    maxEl.className = 'fc-max';
    maxEl.textContent = day.max != null ? `${day.max}°` : '--°';

    const minEl = document.createElement('span');
    minEl.textContent = day.min != null ? `${day.min}°` : '--°';

    div.append(label, emoji, maxEl, minEl);
    weatherForecast.appendChild(div);
  });

  weatherPanel.classList.add('visible');
}

function addLine(cls, text) {
  const div = document.createElement('div');
  div.className = cls;
  if (cls === 'friday') {
    typeText(div, text);
  } else {
    div.textContent = text;
  }
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
  return div;
}

// ใช้กับข้อความสำคัญที่ยิงมาจาก error handler (เช่น ไม่ได้สิทธิ์ไมค์, service ล่ม) ซึ่งไม่ได้เกิดจาก
// การคุยปกติที่ engagedActive จะถูกตั้งไว้ก่อนหน้าอยู่แล้ว — ถ้าใช้ addLine() ตรงๆ ข้อความจะถูกเพิ่มเข้า
// DOM จริงแต่ "มองไม่เห็น" เพราะแชทซ่อนอยู่เป็นค่าเริ่มต้น (ดู .log ใน style.css) ผู้ใช้เลยรู้สึกเหมือน
// "ไม่มีอะไรเกิดขึ้นเลย" ทั้งที่ FRIDAY พยายามแจ้งเตือนแล้วจริงๆ (นี่คือบั๊กจริงที่เจอ)
function announceSystemNotice(text) {
  engagedActive = true;
  addLine('friday', text);
  startFollowUpWindow();
}

function typeText(el, text) {
  let i = 0;
  const cursor = document.createElement('span');
  cursor.className = 'typing-cursor';
  el.appendChild(document.createTextNode(''));
  el.appendChild(cursor);

  function step() {
    if (i < text.length) {
      cursor.before(text[i]);
      i++;
      log.scrollTop = log.scrollHeight;
      setTimeout(step, 14);
    } else {
      cursor.remove();
    }
  }
  step();
}

function setThinking(on) {
  core.classList.toggle('thinking', on);
  coreWrap.classList.toggle('thinking', on);
  status.textContent = on ? 'PROCESSING' : 'STANDBY';
}

function formatHMS(totalSeconds) {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  return [h, m, s].map((n) => String(n).padStart(2, '0')).join(':');
}

// เดิม poll server ทุก 1 วิเพื่อให้ตัวนับถอยหลัง cooldown ลื่น แต่นั่นคือ 86,400 request/วันแม้ไม่ได้ใช้งานเลย
// เปลี่ยนมา sync กับ server ห่างขึ้น (ยังพอให้ LINK OK/LOST ไวพอสำหรับแอปบนเครื่องเดียวกัน) แล้วนับถอยหลัง
// cooldown เองฝั่ง client จากค่าล่าสุดที่รู้ + เวลาที่ผ่านไป ไม่ต้องยิง request ทุกวินาที
const QUOTA_SYNC_MS = 5000;
let lastQuota = { used: 0, limit: null, remaining: null, cooldown_seconds: 0 };
let lastQuotaFetchedAt = 0;

function renderQuotaDisplay() {
  const elapsed = Math.floor((Date.now() - lastQuotaFetchedAt) / 1000);
  const liveCooldown = Math.max(0, lastQuota.cooldown_seconds - elapsed);

  const usedPart = lastQuota.limit != null
    ? `QUOTA ${lastQuota.used}/${lastQuota.limit} · เหลือ ${lastQuota.remaining}`
    : `ใช้วันนี้ ${lastQuota.used} ครั้ง (ยังไม่ทราบโควตาสูงสุด)`;

  quota.innerHTML = usedPart;
  if (liveCooldown > 0) {
    quota.innerHTML += ` <span class="cooldown">คูลดาวน์ ${formatHMS(liveCooldown)}</span>`;
  }

  renderQuotaGauge({ ...lastQuota, cooldown_seconds: liveCooldown });
}

async function refreshQuota() {
  try {
    const res = await fetch('/api/quota', { cache: 'no-store' });
    if (!res.ok) throw new Error('bad status');
    lastQuota = await res.json();
    lastQuotaFetchedAt = Date.now();
    renderQuotaDisplay();
    setLinkHealthy(true);
  } catch (err) {
    setLinkHealthy(false);
  }
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const message = input.value.trim();
  if (!message) return;

  engagedActive = true; // กำลังใช้งาน friday อยู่จริง (พิมพ์/กดพูด/สั่งผ่าน wake mode) โชว์แชท+เขียวไว้ก่อน
  addLine('you', message);
  input.value = '';
  setThinking(true);
  sendBeep();

  const t0 = performance.now();
  try {
    // ยังไม่มีพิกัด (ขอตอนโหลดหน้าไม่สำเร็จ / เพิ่งกดอนุญาต) หรือพิกัดเก่าเกิน 10 นาที -> ขอใหม่แบบ
    // ไม่รอ (request นี้ใช้ค่าที่มีอยู่ รอบหน้าค่อยได้ค่าสด) — rate-limit ไว้กันยิงทุก submit ตอนโดนปฏิเสธ
    const geoStale = clientGeo && Date.now() - clientGeoFetchedAt > GEO_MAX_AGE_MS;
    if ((!clientGeo || geoStale) && Date.now() - geoLastAttemptAt > GEO_RETRY_MS) refreshClientGeo();
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(clientGeo ? { message, geo: clientGeo } : { message }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    recordLatency(performance.now() - t0);
    addLine('friday', data.reply);
    receiveBeep();
    // เปิดก่อน speak() เสมอ (ไม่รอ TTS โหลด/เล่นจบ) เพราะ browser อนุญาต window.open() แบบไม่โดน
    // popup blocker ได้แค่ช่วงสั้นๆ หลัง user gesture (transient activation) รอ TTS ก่อนมักเลยเวลานั้นไปแล้ว
    if (data.action?.type === 'open_url' && data.action.url) {
      openUrlWithFallback(data.action.url);
    } else if (data.action?.type === 'play_youtube' && data.action.video_id) {
      playYoutubeVideo(data.action.video_id, data.action.title);
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
    addLine('friday', `เชื่อมต่อไม่ได้: ${err.message}`);
    startFollowUpWindow(); // ให้เวลาอ่าน error สักพักก่อนแชทจะหายไปเอง แทนที่จะค้าง engagedActive ตลอดไป
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
