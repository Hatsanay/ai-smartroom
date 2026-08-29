import { S } from './state.js';
import { micBtn, wakeBtn, status, input, form, ytPanel } from './dom.js';
import { speak } from './sound.js';
import { addLine, announceSystemNotice } from './chatui.js';
import { requestYoutubeFullscreen } from './youtube.js';

/* ---------- Speech-to-Text: พูดใส่ไมค์แทนพิมพ์ ---------- */

const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;


function setListening(on) {
  S.listening = on;
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
    if (S.wakeMode) return; // โหมดฟังตลอดเปิดอยู่ ไม่ให้ใช้ปุ่มกดพูดซ้อนกัน
    if (S.listening) {
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

/* ---------- โหมดฟังตลอด: พูด "จัสมิน" แล้วตามด้วยคำสั่งได้เลย ---------- */

// Google STT ถอดเสียง "จัสมิน" ออกมาได้สารพัดแบบ (อังกฤษบ้าง ไทยหลายสะกดบ้าง สลับ จ/ย/ญ, ส/ด/ซ/ช,
// เติม/ตัดสระ, ใส่วรรณยุกต์, เว้นวรรคกลางคำ) — รวม pattern ให้กว้างที่สุดเท่าที่ยังไม่ชนคำไทยปกติ
// T = วรรณยุกต์/ไม้ไต่คู้/การันต์ ที่ STT ชอบแถมมา (optional คั่นได้ทุกพยางค์)
const T = '[็-๎]?';
const WAKE_WORD_PATTERNS = [
  // ---- โรมัน / อังกฤษ ----
  /j[ua]s?\s?m[iy]ne?/i,       // jusmin jusmine jasmin jasmine jusmn jas min
  /j[ae]z\s?m[iy]ne?/i,        // jazmin jazmine jezmin
  /y[ae]s\s?m[iy]ne?/i,        // yasmin yasmine yesmin
  /[cg][ha][ts]?\s?m[iy]ne?/i, // chasmin gasmin chatmin (จ ~ ch/j)
  /jes\s?m[iy]ne?/i,           // jesmin
  /jus\s?m[ae]n/i,             // jusman
  /\bjust[iy]n\b/i,            // justin (STT มักได้ยินเป็นชื่อนี้) — ต้องเป็นคำเดี่ยว กัน "adjusting" ฯลฯ
  // ---- ไทย: แกน "จัส/จัด/จาด/ยัส/ญัส..." + "มิน/มีน/มิล/มน" (+ หาง "ทร์/์" ที่ STT ชอบเติม) ----
  new RegExp('[จยญชฌ]' + T + '[ัาะ]?' + T + '[รฤ]?[สซดชฉศษทถ]' + T + '\\s?ม' + T + '[ิีึ]?' + T + '[นลณมฬ](?:ทร?์?|์)?'),
  // ---- ไทย: ขึ้นต้น "แจส / แจ๊ส / แยส / แจ็ส" ----
  new RegExp('แ[จยญ]' + T + '[สซดช]' + T + '\\s?ม' + T + '[ิี]?' + T + '[นลม](?:ทร?์?|์)?'),
  // ---- ไทย: หล่นตัว จ นำ ("รัสมิน / อัสมิน / ทัสมิน / นัสมิน / ลัสมิน") ----
  /[รลอทนห]ั?[สซด]\s?ม[ิี]?น/,
  // ---- ไทย: "จรัสมิน / จัดสมิน / จัสมินทร์ / จัสมิน์" ----
  /จ[ัา]?[รด]?[สซด]\s?ม[ิี]?น(?:ทร?์?)?/,
  // ---- ไทย: "จัสติน / แจสติน" (STT ได้ยินเป็นชื่อจัสติน) ----
  /แ?จ[ัา]?[สซด]\s?ต[ิี]?น/,
  // ---- ไทย: สั้นๆ แค่ "จัส / จั๊ส / จัสมิ" เผื่อ STT ตัดหางคำ (ไม่เอา "จัด" เดี่ยวๆ = คำไทยปกติ,
  //          ไม่เอา "แจ๊ส" เดี่ยวๆ = jazz; "แจสมิน" เต็มคำมี pattern อื่นจับอยู่แล้ว)
  //          ใช้ lookbehind กันไม่ให้กิน space นำหน้า (จะได้ไม่ตัดคำสั่งเพี้ยนตอนมีคำนำหน้าคำปลุก) ----
  /(?<=^|\s)(?:จั[่้๊๋]?ส|จัสมิ|จั[่้๊๋]?ด[สซ])(?=\s|$|ม)/,
];

// เรียกชื่อเฉยๆ ไม่มีคำสั่งตาม - ตอบรับสั้นๆ ด้วยเสียงจริง สุ่มสลับไว้กันซ้ำจำเจ
const WAKE_ACK_PHRASES = ['ค่ะ มีอะไรให้ช่วยคะ', 'ว่าไงคะบอส', 'ฟังอยู่ค่ะ', 'คะ พร้อมค่ะ'];

function extractWakeCommand(transcript) {
  // เลือก match ที่อยู่ต้นประโยคที่สุด (เผื่อมีหลาย pattern โดน) แล้วคืนส่วนที่เหลือหลังคำปลุกเป็นคำสั่ง
  let best = null;
  for (const pattern of WAKE_WORD_PATTERNS) {
    const m = transcript.match(pattern);
    if (m && (best === null || m.index < best.index)) best = { index: m.index, end: m.index + m[0].length };
  }
  if (best === null) return null;
  return transcript.slice(best.end).replace(/^[\s,.ๆ]+/, '').trim();
}

let wakeRecognition = null;
let wakeRestartTimer = null;
let wakeStarting = false;     // มี start() ค้างอยู่ยังไม่ยิง onstart -> กันสร้าง instance ซ้อน
let wakeStartedAt = 0;        // เวลาที่เรียก start() ครั้งล่าสุด (watchdog ใช้)
let wakeOnstartAt = 0;        // เวลาที่ onstart ยิงล่าสุด
// per-utterance state — รีเซ็ตทุกครั้งที่ขึ้นประโยคใหม่ / restart session
let curUtterIdx = -1;
let utterWakeSeen = false;    // เจอคำปลุกใน interim ของประโยคนี้แล้ว
let utterHandled = false;     // ประมวลผลประโยคนี้ไปแล้ว (กันยิงซ้ำ interim/final/onend)
let lastInterim = '';         // interim ล่าสุด — เผื่อ session ตายก่อนได้ final ("จัสมิน" คำเดียว)
let heardRevertTimer = null;

// ตัด instance เดิมให้ขาด (abort + ถอด handler) ก่อนสร้างใหม่ — กัน instance เก่ายังฟัง + onend เก่าสั่ง restart ทับ
function killWakeRecognition() {
  const w = wakeRecognition;
  wakeRecognition = null;
  if (!w) return;
  w.onresult = w.onerror = w.onend = w.onstart = null;
  try { w.abort(); } catch (err) { /* state ยังไม่พร้อม ปล่อยได้ */ }
}

// แสดงว่า "ไมค์ยังทำงาน ได้ยินแล้วแต่ไม่ตรงคำปลุก" — ผู้ใช้จะได้รู้ว่าเป็นปัญหาการ match ไม่ใช่ไมค์ตาย
function flashHeard(t) {
  clearTimeout(heardRevertTimer);
  const short = t.length > 22 ? t.slice(0, 22) + '…' : t;
  status.textContent = `STANDBY · ได้ยิน "${short}"`;
  heardRevertTimer = setTimeout(() => {
    if (status.textContent.startsWith('STANDBY · ได้ยิน')) {
      status.textContent = followUpActive ? FOLLOWUP_STATUS_TEXT : 'STANDBY';
    }
  }, 1800);
}

// ประมวลผลประโยคที่ "จบแล้ว" (final จริง หรือ fallback จาก interim ตอน session ตาย)
function handleWakeFinal(transcript, wakeCmd) {
  if (utterHandled) return;
  if (wakeCmd === undefined || wakeCmd === null) wakeCmd = extractWakeCommand(transcript);
  if (wakeCmd === null) {
    // ได้ยินเสียงแต่ไม่มีคำปลุก — ถ้าเมื่อกี้ interim หลอกว่าเจอ (utterWakeSeen) ให้ปลดสีเขียวคืน
    if (utterWakeSeen && !followUpActive && !isAccumulatingCommand) S.engagedActive = false;
    flashHeard(transcript);
    console.log('[wake] missed:', transcript);
    return;
  }
  utterHandled = true;
  if (!wakeCmd) {
    // เรียกชื่อเฉยๆ ไม่มีคำสั่ง -> ตอบรับด้วยเสียง แล้วเข้าช่วงคุยต่อเนื่อง
    S.engagedActive = true;
    const ack = WAKE_ACK_PHRASES[Math.floor(Math.random() * WAKE_ACK_PHRASES.length)];
    addLine('jusmin', ack);
    speak(ack, () => { if (S.wakeMode) startFollowUpWindow(); });
    return;
  }
  queueWakeCommand(wakeCmd);
}

// ช่วงหน่วงก่อน restart session ฟังตลอดใหม่ทุกครั้งที่ session เดิมจบ (ปกติ ไม่ใช่แค่ตอน error —
// ดูหมายเหตุที่ onend ข้างล่าง) เก็บเป็นค่าน้อยที่สุดเท่าที่พอกันชนได้ กันไมค์ "หูหนวก" นานเกินจำเป็น
const WAKE_RESTART_DELAY_MS = 30;

// ช่วงคุยต่อเนื่องหลัง จัสมิน ตอบ: ไม่ต้องพูด "จัสมิน" ซ้ำใน 15 วิถัดไป
const FOLLOWUP_MS = 15000;
const FOLLOWUP_STATUS_TEXT = 'STANDBY · ฟังต่อเนื่อง';
let followUpActive = false;
let followUpTimer = null;

// S.engagedActive คุมสีเขียว (core/wave/glow) กว้างกว่า followUpActive: เริ่มทันทีตั้งแต่ได้ยินคำว่า
// "จัสมิน" (ครอบคลุมช่วงกำลังประมวลผล + กำลังตอบด้วย) แล้วค่อยนับ 15 วิถอยหลังหลังตอบเสร็จจริงๆ
// ถึงจะกลับเป็นสีเดิม ไม่ใช่แค่ตอนเข้าสู่ช่วง follow-up เท่านั้น

// เรียกได้ทั้งตอนคุยผ่านเสียง (wake mode) และพิมพ์/กดพูดแบบธรรมดา — S.engagedActive ใช้คุม
// สีเขียว + การโชว์แชทเหมือนกันหมด ส่วนข้อความ "ฟังต่อเนื่อง"/ไม่ต้องพูด "จัสมิน" ซ้ำ (followUpActive)
// มีความหมายเฉพาะตอน wake mode เปิดอยู่จริงเท่านั้น (ตอนนั้นถึงจะมี STT ฟังอยู่จริง)
export function startFollowUpWindow() {
  clearTimeout(followUpTimer);
  followUpActive = S.wakeMode;
  S.engagedActive = true;
  if (S.wakeMode && status.textContent === 'STANDBY') status.textContent = FOLLOWUP_STATUS_TEXT;
  followUpTimer = setTimeout(expireFollowUpWindow, FOLLOWUP_MS);
}

// เรียกตอนเงียบเกิน 15 วิจริงๆ เท่านั้น -> ถือว่าเลิกคุยแล้ว กลับสีเดิม ต้องเรียก "จัสมิน" ใหม่
export function expireFollowUpWindow() {
  clearTimeout(followUpTimer);
  followUpActive = false;
  S.engagedActive = false;
  if (status.textContent === FOLLOWUP_STATUS_TEXT) status.textContent = 'STANDBY';
  // คุยกับ จัสมิน จบแล้ว (พูดจบ + เงียบครบ 15 วิ ไม่มีถามต่อ) — ถ้าเมื่อกี้ย่อจอ YouTube ไว้เพราะโดนเรียก
  // ให้กลับไปเต็มจอเหมือนเดิม (เว้นแต่เพลงถูกปิดไปแล้ว — เช็คจาก .visible)
  if (S.ytWasMaximizedBeforeEngage) {
    S.ytWasMaximizedBeforeEngage = false;
    if (S.ytPlayer && ytPanel.classList.contains('visible')) requestYoutubeFullscreen();
  }
}

// เรียกตอนมีคนพูดต่อจริงๆ ภายใน 15 วิ (ยังคุยกันต่อ ไม่ใช่หมดเวลา) S.engagedActive เลยยังคงเป็น true ต่อ
export function consumeFollowUpWindow() {
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
let isAccumulatingCommand = false; // true ระหว่างรอ debounce — ให้พูดต่อได้โดยไม่ต้องพูด "จัสมิน" ซ้ำ

function queueWakeCommand(text) {
  pendingCommandText = pendingCommandText ? `${pendingCommandText} ${text}` : text;
  isAccumulatingCommand = true;
  S.engagedActive = true;
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

// ปิดไมค์จริงๆ ตอน จัสมิน พูด (ไม่ใช่แค่เช็ค flag) กัน STT หยิบเสียงตัวเองมาตีความ
// ข้อแลกเปลี่ยน: แทรกกลางประโยคไม่ได้ ต้องรอพูดจบก่อน — เคยลองแบบเทียบข้อความเสียงสะท้อนโดยไม่ปิดไมค์
// (ไม่ต้องรอ TTS จบ แทรกได้ทันที) แต่ไม่น่าเชื่อถือพอในสถานการณ์จริง เพราะ STT แปลงเสียงสะท้อนออกมาเพี้ยนบ่อย
// แผนในอนาคต: ใช้ getUserMedia({echoCancellation:true}) + STT backend จริง (เช่น Whisper) แทน
// ถึงจะแทรกกลางประโยคได้แบบเชื่อถือได้ ตอนนี้พอไม่ไหวก่อน
const TTS_RESUME_DELAY_MS = 200; // กันเสียงสะท้อน/หางเสียงจากลำโพงหลุดเข้าไมค์หลัง TTS จบ (ลดจาก 500 ให้ไมค์กลับมาไวขึ้น)

export function pauseWakeListening() {
  clearTimeout(wakeRestartTimer);
  wakeStarting = false;
  killWakeRecognition(); // abort + ถอด handler -> ไม่มี onend สั่ง restart ซ้อนกับ resumeWakeListeningAfterDelay
}

export function resumeWakeListeningAfterDelay(delayMs = TTS_RESUME_DELAY_MS) {
  if (!S.wakeMode) return;
  clearTimeout(wakeRestartTimer);
  wakeRestartTimer = setTimeout(runWakeRecognition, delayMs);
}

function runWakeRecognition() {
  if (!S.wakeMode || !SpeechRecognitionCtor) return;
  if (wakeStarting) return; // มี start() ค้างอยู่ ยังไม่ยิง onstart — อย่าสร้างซ้อน

  clearTimeout(wakeRestartTimer);
  wakeRestartTimer = null;
  killWakeRecognition();

  wakeStarting = true;
  wakeStartedAt = Date.now();
  curUtterIdx = -1;
  utterWakeSeen = false;
  utterHandled = false;
  lastInterim = '';

  const w = new SpeechRecognitionCtor();
  wakeRecognition = w;
  w.lang = 'th-TH';
  w.interimResults = true;   // จับคำปลุกได้เร็วขึ้นจาก interim + รอด session-end ที่ยังไม่ทันได้ final
  w.continuous = true;
  w.maxAlternatives = 3;     // Google มัก transcribe "จัสมิน" เป็นตัวเลือก #2 ตอน #1 เพี้ยน

  w.onstart = () => {
    wakeStarting = false;
    wakeOnstartAt = Date.now();
  };

  w.onresult = (e) => {
    if (S.ttsSpeaking) return; // ผลหลุดมาช่วงเสี้ยววิก่อน abort() มีผลจริง กันอีกชั้น
    const idx = e.results.length - 1;
    const result = e.results[idx];
    if (idx !== curUtterIdx) { // ขึ้นประโยคใหม่ -> เคลียร์ per-utterance state
      curUtterIdx = idx;
      utterWakeSeen = false;
      utterHandled = false;
      lastInterim = '';
    }

    // เอา transcript จาก alternative ที่เจอคำปลุก (ถ้า #1 ไม่เจอ ลองไล่ #2 #3)
    let transcript = (result[0] && result[0].transcript || '').trim();
    let wakeCmd = extractWakeCommand(transcript);
    if (wakeCmd === null && result.length > 1) {
      for (let a = 1; a < result.length; a++) {
        const alt = (result[a].transcript || '').trim();
        const w2 = extractWakeCommand(alt);
        if (w2 !== null) { transcript = alt; wakeCmd = w2; break; }
      }
    }
    if (!transcript) return;

    // ระหว่างคุยต่อเนื่อง / รอ debounce 5 วิ -> พูดอะไรมาก็เป็นส่วนของคำสั่งเดิม (ไม่ต้องพูด "จัสมิน" ซ้ำ)
    // ยกเว้นตอนเพลง YouTube เล่นอยู่ (state จริงจาก YT.Player) -> บังคับต้องมี "จัสมิน" นำเสมอ
    if ((followUpActive || isAccumulatingCommand) && !S.ytIsPlaying) {
      if (result.isFinal) queueWakeCommand(transcript); // เฉพาะ final — กัน interim ต่อท้ายซ้ำจนเพี้ยน
      else lastInterim = transcript;                    // เผื่อ session ตายก่อน final -> flush ตอน onend
      return;
    }

    if (!result.isFinal) {
      lastInterim = transcript;
      if (wakeCmd !== null && !utterWakeSeen) {
        utterWakeSeen = true;
        S.engagedActive = true; // เขียวทันทีที่ interim เจอคำปลุก = ผู้ใช้รู้ว่าจับได้ (ยังไม่ประมวลผล รอ final)
      }
      return;
    }
    handleWakeFinal(transcript, wakeCmd);
  };

  w.onerror = (e) => {
    wakeStarting = false;
    if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
      stopWakeMode();
      announceSystemNotice('ขออนุญาตใช้ไมโครโฟนก่อนนะคะ ถึงจะเปิดโหมดฟังตลอดได้');
    }
    // no-speech / aborted / network -> ปล่อยให้ onend restart ให้เอง
  };

  w.onend = () => {
    wakeStarting = false;
    // session ตายก่อนได้ final — กู้จาก interim ล่าสุด
    if (lastInterim && !S.ttsSpeaking) {
      if (utterWakeSeen && !utterHandled) {
        handleWakeFinal(lastInterim, null);            // "จัสมิน [คำสั่ง]" คำเดียวสั้นๆ
      } else if ((followUpActive || isAccumulatingCommand) && !S.ytIsPlaying) {
        queueWakeCommand(lastInterim);                 // ระหว่างคุยต่อเนื่อง
      }
    }
    lastInterim = '';
    if (S.wakeMode) {
      // Chrome ตัดจบ continuous:true เองเป็นระยะแม้ไม่มี error — restart ไวสุดเท่าที่ไม่โดน
      // "recognition already started" (ตัว killWakeRecognition + wakeStarting คุมการซ้อนแล้ว)
      wakeRestartTimer = setTimeout(runWakeRecognition, WAKE_RESTART_DELAY_MS);
    }
  };

  try {
    w.start();
  } catch (err) {
    wakeStarting = false;
    // start() ซ้อนได้ (สลับโหมด / browser ยังไม่คืนทรัพยากรไมค์) — ลองใหม่สั้นๆ กันโหมดค้างเงียบ
    if (S.wakeMode) wakeRestartTimer = setTimeout(runWakeRecognition, WAKE_RESTART_DELAY_MS);
  }
}

// watchdog: ถ้าเรียก start() ไปแล้วเกิน 5 วิแต่ onstart ไม่เคยมา และไม่มี restart รออยู่ = session ตายเงียบ
if (SpeechRecognitionCtor) {
  setInterval(() => {
    if (!S.wakeMode || S.ttsSpeaking || wakeStarting) return;
    const now = Date.now();
    if (wakeStartedAt && now - wakeStartedAt > 5000 && wakeOnstartAt < wakeStartedAt && !wakeRestartTimer) {
      status.textContent = 'ไมค์หลุด · กำลังต่อใหม่';
      runWakeRecognition();
    }
  }, 3000);
}

export function startWakeMode() {
  if (!SpeechRecognitionCtor) return;
  if (S.listening) recognition.stop(); // เลิกโหมดกดพูดถ้าค้างอยู่
  S.wakeMode = true;
  wakeBtn.classList.add('active');
  micBtn.disabled = true;
  runWakeRecognition();
}

export function stopWakeMode() {
  S.wakeMode = false;
  wakeBtn.classList.remove('active');
  micBtn.disabled = false;
  clearTimeout(wakeRestartTimer);
  wakeRestartTimer = null;
  wakeStarting = false;
  wakeStartedAt = 0;
  expireFollowUpWindow();
  // กันคำสั่งที่กำลังรอ debounce 5 วิอยู่หลุดออกไปส่งทีหลัง ทั้งที่ปิดโหมดฟังตลอดไปแล้ว
  clearTimeout(commandDebounceTimer);
  pendingCommandText = '';
  isAccumulatingCommand = false;
  killWakeRecognition(); // abort + ถอด handler -> ไม่มี onend สั่ง restart
}

if (SpeechRecognitionCtor) {
  wakeBtn.addEventListener('click', () => {
    if (S.wakeMode) stopWakeMode();
    else startWakeMode();
  });
}
