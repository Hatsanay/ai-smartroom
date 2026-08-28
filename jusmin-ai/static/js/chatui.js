import { S } from './state.js';
import { log, core, coreWrap, status } from './dom.js';
import { startFollowUpWindow } from './voice.js';

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
export function openUrlWithFallback(url) {
  const win = window.open(url, '_blank');
  if (!win || win.closed) {
    addLinkLine(url);
  }
}

export function addLinkLine(url) {
  const div = document.createElement('div');
  div.className = 'jusmin-link';
  const a = document.createElement('a');
  a.href = url;
  a.target = '_blank';
  a.rel = 'noopener noreferrer';
  a.textContent = 'เบราว์เซอร์บล็อกการเปิดแท็บอัตโนมัติ — กดตรงนี้เพื่อเปิดเองค่ะ';
  div.appendChild(a);
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

export function addLine(cls, text) {
  const div = document.createElement('div');
  div.className = cls;
  if (cls === 'jusmin') {
    typeText(div, text);
  } else {
    div.textContent = text;
  }
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
  return div;
}

// ใช้กับข้อความสำคัญที่ยิงมาจาก error handler (เช่น ไม่ได้สิทธิ์ไมค์, service ล่ม) ซึ่งไม่ได้เกิดจาก
// การคุยปกติที่ S.engagedActive จะถูกตั้งไว้ก่อนหน้าอยู่แล้ว — ถ้าใช้ addLine() ตรงๆ ข้อความจะถูกเพิ่มเข้า
// DOM จริงแต่ "มองไม่เห็น" เพราะแชทซ่อนอยู่เป็นค่าเริ่มต้น (ดู .log ใน style.css) ผู้ใช้เลยรู้สึกเหมือน
// "ไม่มีอะไรเกิดขึ้นเลย" ทั้งที่ จัสมิน พยายามแจ้งเตือนแล้วจริงๆ (นี่คือบั๊กจริงที่เจอ)
export function announceSystemNotice(text) {
  S.engagedActive = true;
  addLine('jusmin', text);
  startFollowUpWindow();
}

export function typeText(el, text) {
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

export function setThinking(on) {
  core.classList.toggle('thinking', on);
  coreWrap.classList.toggle('thinking', on);
  status.textContent = on ? 'PROCESSING' : 'STANDBY';
}

