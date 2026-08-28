import { S } from './state.js';
import { ytPanel, ytPanelTitle, ytPlayerMount, ytExitFs } from './dom.js';

/* ---------- เครื่องเล่น YouTube: ฝัง IFrame Player จริงในหน้า (ไม่ใช่เปิดแท็บแยก) เพื่อให้
   สั่งหยุด/เล่นต่อ/เปลี่ยนเพลงจากโค้ดเราได้จริง — แท็บที่เปิดแยกจาก window.open() สั่งควบคุมจาก
   ภายนอกไม่ได้เลย (คนละ browsing context) วิดีโอที่เล่นมาจาก yt_dlp ค้นหาจริงฝั่ง server (tools.py)
   ไม่ใช่ของสุ่ม/ปลอม ---------- */

let ytApiReady = false;
let ytPlayerReady = false; // true หลัง onReady event จริงเท่านั้น — เมธอดของ YT.Player (setVolume ฯลฯ)
// ใช้งานไม่ได้แน่นอนก่อนหน้านี้ แม้ตัว object จะคืนกลับมาจาก `new YT.Player()` ทันทีแบบ synchronous แล้ว
// ก็ตาม (ตัว iframe ข้างในยังไม่ได้เชื่อมต่อ postMessage เสร็จ) เป็นเรื่องจริงที่เอกสาร YouTube ระบุไว้
let ytPendingVideo = null; // {id, title} รอเล่นถ้ายังโหลด IFrame API/player ไม่เสร็จตอนสั่งมา
let ytPendingCommand = null; // action ล่าสุดที่รอทำ ถ้า controlYoutube() ถูกเรียกก่อน player ready จริง
// ผู้ใช้ขอ: ทุกครั้งที่เปิด YouTube ใหม่ ให้เริ่มที่ 25% เสมอ (ไม่ค้างค่าที่เคยปรับไว้ข้ามเพลง)
const YT_DEFAULT_VOLUME = 25;
let ytVolume = YT_DEFAULT_VOLUME; // baseline volume ที่ผู้ใช้ตั้งไว้ล่าสุดผ่าน volume_up/volume_down (คนละตัวกับตอน duck ชั่วคราว)
// หูมนุษย์รับรู้ความดังแบบ logarithmic ไม่ใช่ linear — ทดสอบยืนยันแล้วว่า setVolume() บน player จริง
// เปลี่ยนค่าไปตรงตามที่สั่งเป๊ะ (100->80 จริง) แต่ผู้ใช้รายงานว่า "สั่งลดแล้วไม่รู้สึกว่าลดเลย" เพราะ
// step เดิม (20) เล็กเกินไปจนหูแทบไม่รู้สึกถึงความต่าง — ปรับเป็น 25 ให้รู้สึกถึงการเปลี่ยนแปลงชัดเจนขึ้น
const YT_VOLUME_STEP = 25;

// เรียกทุกครั้งที่เริ่มวิดีโอใหม่ (player เพิ่ง ready หรือ loadVideoById เพลงใหม่) — รีเซ็ต baseline กลับ
// ค่าเริ่มต้น แล้วสั่ง setVolume จริงถ้าทำได้ตอนนี้ (ถ้า จัสมิน กำลังพูด = duck ค้างอยู่ ปล่อยให้
// restoreYoutubeVolume() หยิบค่าใหม่ไปใช้เองตอน TTS จบ)
function applyDefaultVolume() {
  ytVolume = YT_DEFAULT_VOLUME;
  if (S.ytPlayer && ytPlayerReady && !S.ttsSpeaking && typeof S.ytPlayer.setVolume === 'function') {
    S.ytPlayer.setVolume(YT_DEFAULT_VOLUME);
  }
}

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
    const { id, title, resetVolume } = ytPendingVideo;
    ytPendingVideo = null;
    playYoutubeVideo(id, title, resetVolume);
  }
};

// resetVolume = true เฉพาะตอน "เปิด YouTube ใหม่" (open_youtube) — ตอน "เปลี่ยนเพลง/เพลงถัดไป" (next)
// ส่ง false มา ให้คงระดับเสียงที่ผู้ใช้ปรับไว้ (loadVideoById ไม่แตะ volume ของ player อยู่แล้ว)
export function playYoutubeVideo(videoId, title, resetVolume = false) {
  ytPanelTitle.textContent = title || videoId;
  ytPanel.classList.add('visible');

  if (!ytApiReady || (S.ytPlayer && !ytPlayerReady)) {
    // ยังโหลด script ไม่เสร็จ หรือ player ตัวเดิมยังไม่ ready จริง (รอ onReady) — เก็บคิวไว้ก่อน
    loadYtApiScript();
    ytPendingVideo = { id: videoId, title, resetVolume };
    return;
  }

  if (S.ytPlayer && typeof S.ytPlayer.loadVideoById === 'function') {
    S.ytPlayer.loadVideoById(videoId);
    if (resetVolume) applyDefaultVolume(); // เปิดใหม่เท่านั้น = กลับไป 25% — เปลี่ยนเพลงคงเสียงเดิม
    return;
  }

  S.ytPlayer = new YT.Player(ytPlayerMount, {
    videoId,
    playerVars: { autoplay: 1, playsinline: 1 },
    events: { onReady: onYtPlayerReady, onStateChange: onYtStateChange },
  });
}

// onReady ยิงแค่ครั้งเดียวตอนสร้าง player ใหม่เท่านั้น (ไม่ยิงซ้ำตอน loadVideoById เปลี่ยนเพลง) —
// พอ ready แล้วค้างเป็น true ตลอดอายุ player ตัวนี้ ทำคิวที่ค้างไว้ระหว่างรอให้เรียบร้อย (ถ้ามี)
function onYtPlayerReady() {
  ytPlayerReady = true;
  applyDefaultVolume(); // เปิดเพลงครั้งแรก -> ตั้งเสียงเริ่มต้น 25% (autoplay เริ่มที่ default ของ YT ก่อนแป๊บนึง)
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
// (ที่ปกติไม่ต้องพูด "จัสมิน" ซ้ำ) ไปก่อน กันเสียงร้อง/เนื้อเพลงถูกตีความเป็นคำสั่งมั่วๆ ดู
// เงื่อนไข !S.ytIsPlaying ใน wakeRecognition.onresult — ต้องพูด "จัสมิน" นำทุกครั้งระหว่างเพลงเล่นอยู่
function onYtStateChange(event) {
  S.ytIsPlaying = event.data === YT.PlayerState.PLAYING;
}

export function controlYoutube(action) {
  if (!S.ytPlayer) return; // ยังไม่เคยเปิดเพลงอะไรเลย ไม่มีอะไรให้คุม
  if (!ytPlayerReady) {
    // player กำลังโหลดอยู่ ยังสั่งจริงไม่ได้ (เมธอดของ YT.Player ใช้ไม่ได้จริงก่อน onReady แม้ตัว
    // object จะมีอยู่แล้วก็ตาม) รอไว้ก่อน พอ ready แล้ว onYtPlayerReady() จะทำคำสั่งนี้ให้เอง
    // (คำสั่งล่าสุดชนะ ไม่ใช่คิวสะสม — พอเพียงสำหรับ use case นี้)
    ytPendingCommand = action;
    return;
  }
  if (action === 'pause' && typeof S.ytPlayer.pauseVideo === 'function') {
    S.ytPlayer.pauseVideo();
    S.ytIsPlaying = false; // ไม่ต้องรอ onStateChange async กลับมา ตั้งทันทีกันช่วง follow-up ปลดล็อกเร็วเกินจริง
  } else if (action === 'resume' && typeof S.ytPlayer.playVideo === 'function') {
    S.ytPlayer.playVideo();
  } else if (action === 'stop') {
    if (typeof S.ytPlayer.stopVideo === 'function') S.ytPlayer.stopVideo();
    S.ytIsPlaying = false;
    ytVolume = YT_DEFAULT_VOLUME; // เริ่มเซสชันฟังเพลงครั้งถัดไปที่ค่าเริ่มต้น (25%) เสมอ ไม่ค้างค่าที่เคยปรับไว้
    exitYoutubeFullscreen(); // ปิดเพลง -> ออกจากเต็มจอ + ยกเลิกแผนกลับไปเต็มจอ (ไม่ให้ค้างจอดำ/เด้งกลับ)
    ytPanel.classList.remove('visible');
  } else if (action === 'volume_up' || action === 'volume_down') {
    const delta = action === 'volume_up' ? YT_VOLUME_STEP : -YT_VOLUME_STEP;
    ytVolume = Math.max(0, Math.min(100, ytVolume + delta));
    // ถ้า จัสมิน กำลังพูดอยู่ (duck ค้างที่ YT_DUCK_VOLUME) อย่าเพิ่งใช้ค่าใหม่ทับตอนนี้ กันเสียงเพลง
    // ดังแทรกขึ้นมากลางที่ จัสมิน พูดอยู่ — เก็บ ytVolume ไว้ก่อน พอ TTS จบ restoreYoutubeVolume()
    // จะหยิบค่าล่าสุดไปใช้เอง
    if (!S.ttsSpeaking) restoreYoutubeVolume();
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


function ytFullscreenTarget() {
  if (S.ytPlayer && typeof S.ytPlayer.getIframe === 'function') {
    try {
      const f = S.ytPlayer.getIframe();
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

export function requestYoutubeFullscreen() {
  if (!ytPanel) return;
  S.ytMaximized = true;
  ytPanel.classList.add('maximized');
  // bonus: ขอ real fullscreen (ซ่อนแถบเบราว์เซอร์) เฉพาะตอนมี user gesture จริงๆ — พิมพ์คำสั่ง + Enter
  // จะยังมี transient activation อยู่ ส่วนสั่งด้วยเสียง/auto-restore ไม่มี เลยข้ามไปเลย (CSS .maximized
  // ทำให้เต็มจอเบราว์เซอร์ไปแล้ว) กัน Chrome log "requestFullscreen ... requires a user gesture" รก console
  if (navigator.userActivation ? navigator.userActivation.isActive : true) {
    doRequestFullscreen(ytFullscreenTarget()).catch(() => {});
  }
}

export function exitYoutubeFullscreen() {
  S.ytMaximized = false;
  S.ytWasMaximizedBeforeEngage = false; // สั่งออกชัดเจน (ผู้ใช้/ระบบ) -> ยกเลิกแผนกลับไปเต็มจออัตโนมัติด้วย
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
  if (e.key === 'Escape' && (S.ytMaximized || S.ytWasMaximizedBeforeEngage)) exitYoutubeFullscreen();
});
// ผู้ใช้กด Esc ออกจาก real fullscreen (ที่ขอซ้อนไว้) -> เลิก .maximized ด้วย ไม่ให้ค้างเต็มจอครึ่งๆ
document.addEventListener('fullscreenchange', () => {
  if (!document.fullscreenElement && S.ytMaximized) exitYoutubeFullscreen();
});

/* audio ducking: ลดเสียงเพลง YouTube ตอน จัสมิน พูด (TTS) — เรียกจาก sound.js */
const YT_DUCK_VOLUME = 15;
export function duckYoutubeVolume() {
  if (S.ytPlayer && ytPlayerReady && typeof S.ytPlayer.setVolume === 'function') S.ytPlayer.setVolume(YT_DUCK_VOLUME);
}
export function restoreYoutubeVolume() {
  if (S.ytPlayer && ytPlayerReady && typeof S.ytPlayer.setVolume === 'function') S.ytPlayer.setVolume(ytVolume);
}
