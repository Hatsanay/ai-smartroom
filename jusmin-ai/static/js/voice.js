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
  /just[iy]n/i,                // justin (STT มักได้ยินเป็นชื่อนี้)
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
  // ---- ไทย: สั้นๆ แค่ "จัส / จั๊ส / แจ๊ส / จัสมิ" เผื่อ STT ตัดหางคำ (ไม่เอา "จัด" เดี่ยวๆ = คำไทยปกติ)
  //          ใช้ lookbehind กันไม่ให้กิน space นำหน้า (จะได้ไม่ตัดคำสั่งเพี้ยนตอนมีคำนำหน้าคำปลุก) ----
  /(?<=^|\s)(?:จั[่้๊๋]?ส|แจ[่้๊๋]?ส|จัสมิ|จั[่้๊๋]?ด[สซ])(?=\s|$|ม)/,
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
const TTS_RESUME_DELAY_MS = 500; // กันเสียงสะท้อน/หางเสียงจากลำโพงหลุดเข้าไมค์หลัง TTS จบ

export function pauseWakeListening() {
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

export function resumeWakeListeningAfterDelay(delayMs = TTS_RESUME_DELAY_MS) {
  if (!S.wakeMode) return;
  clearTimeout(wakeRestartTimer);
  wakeRestartTimer = setTimeout(runWakeRecognition, delayMs);
}

function runWakeRecognition() {
  if (!S.wakeMode || !SpeechRecognitionCtor) return;

  wakeRecognition = new SpeechRecognitionCtor();
  wakeRecognition.lang = 'th-TH';
  wakeRecognition.interimResults = false;
  wakeRecognition.continuous = true;

  wakeRecognition.onresult = (e) => {
    if (S.ttsSpeaking) return; // เผื่อผลลัพธ์หลุดมาในช่วงเสี้ยววินาทีก่อน stop() มีผลจริง กันไว้อีกชั้น
    const result = e.results[e.results.length - 1];
    if (!result.isFinal) return;
    const transcript = result[0].transcript.trim();
    if (!transcript) return;

    // ระหว่างเพลง YouTube กำลังเล่นอยู่จริง (state จริงจาก YT.Player ไม่ใช่เดาเอง) ห้ามข้ามการพูด
    // "จัสมิน" นำแม้จะอยู่ในช่วงคุยต่อเนื่อง/กำลังรอฟังต่อก็ตาม กันเนื้อเพลง/เสียงร้องถูกตีความเป็น
    // คำสั่งมั่วๆ — ปล่อยให้ตกไปเช็ค extractWakeCommand() ข้างล่างแทน ต้องมีคำว่า "จัสมิน" อยู่จริง
    if ((followUpActive || isAccumulatingCommand) && !S.ytIsPlaying) {
      // อยู่ในช่วงคุยต่อเนื่อง หรือกำลังรอ debounce 5 วิเผื่อพูดต่ออยู่ พูดอะไรมาก็ถือเป็นส่วนหนึ่งของ
      // คำสั่งเดิมเลย ไม่ต้องพูด "จัสมิน" ซ้ำ — queueWakeCommand() เอง (ไม่ส่งทันที รอ 5 วิเผื่อพูดต่อ)
      queueWakeCommand(transcript);
      return;
    }

    const command = extractWakeCommand(transcript);
    if (command === null) {
      // เก็บ log ไว้เผื่อ debug กรณี "พูด จัสมิน แล้วไม่ติด" — บางทีสาเหตุคือ Google STT ถอดเสียง
      // "จัสมิน" เป็นคำไทยที่สะกดต่างจาก WAKE_WORD_PATTERNS ที่มี ไม่ใช่ปัญหาจังหวะ/ไมค์เลย
      // เปิด DevTools console (F12) ดู "[wake] missed:" เทียบว่า STT ได้ยินเป็นคำว่าอะไรจริงๆ
      // (ใช้ console.log ไม่ใช่ debug จะได้เห็นเลยไม่ต้องเปิด Verbose — เอาคำที่ขึ้นมาบอกได้ จะเพิ่ม pattern ให้)
      console.log('[wake] missed:', transcript);
      return; // ไม่มีคำว่า จัสมิน ในประโยคนี้ ข้ามไป
    }
    if (!command) {
      // เรียกชื่อเฉยๆ ไม่มีคำสั่งตาม -> ตอบรับด้วยเสียงจริง พอตอบเสร็จ (ไมค์เปิดกลับมาเอง) ค่อยรอฟังคำถามต่อ
      // โดยไม่ต้องพูด "จัสมิน" ซ้ำ (ใช้กลไกช่วงคุยต่อเนื่องเดิม)
      // นับ 15 วิ "หลังเสียงพูดหยุดจริง" (ผ่าน callback ตอน speak() จบ) ไม่ใช่นับตั้งแต่เริ่มพูด
      // ไม่งั้นถ้าประโยคยาวจะโดนกินเวลาไปตั้งแต่ตอนยังพูดไม่จบ
      S.engagedActive = true; // ได้ยินคำว่า "จัสมิน" แล้ว เขียวทันที ไม่ต้องรอพูดจบ
      const ack = WAKE_ACK_PHRASES[Math.floor(Math.random() * WAKE_ACK_PHRASES.length)];
      addLine('jusmin', ack);
      speak(ack, () => {
        if (S.wakeMode) startFollowUpWindow();
      });
      return;
    }
    // ได้ยินคำว่า "จัสมิน" + คำสั่งแล้ว — ยังไม่ส่งทันที รอ 5 วิเผื่อพูดต่อ (queueWakeCommand ตั้ง
    // S.engagedActive/isAccumulatingCommand ให้เองแล้ว พูดต่อโดยไม่ต้องพูด "จัสมิน" ซ้ำได้เลยในช่วงนี้)
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
    if (S.wakeMode) {
      // เดิมหน่วง 250ms ก่อน restart — Chrome ตัดจบ session ของ continuous:true เองเป็นระยะแม้ไม่มี
      // error เลย (พฤติกรรมปกติของ Web Speech API ไม่ใช่แค่ตอน error) รอบ restart แบบนี้เลยเกิดขึ้น
      // บ่อยมากตอนใช้งานจริง ไม่ใช่กรณีพิเศษ — ช่วง 250ms ที่ไมค์ "หูหนวก" สนิทนี้แหละคือสาเหตุที่
      // พูด "จัสมิน" คำเดียว (สั้นแค่ ~300-500ms) แล้วบางทีไม่ติดเลย เพราะจังหวะพูดดันตรงกับช่วงรีสตาร์ท
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
    if (S.wakeMode) wakeRestartTimer = setTimeout(runWakeRecognition, WAKE_RESTART_DELAY_MS);
  }
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
    if (S.wakeMode) stopWakeMode();
    else startWakeMode();
  });
}
