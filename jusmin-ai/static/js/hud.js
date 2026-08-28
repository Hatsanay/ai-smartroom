import {
  bootOverlay, bootText, coreWrap, clockTime, clockDate,
  latencyPoly, latencyLast, latencyEmpty,
  quota, quotaBars, quotaGaugeLabel, radarSweep, linkStatus,
} from './dom.js';

/* ---------- boot sequence ---------- */

const BOOT_LINES = [
  '> INITIALIZING J.U.S.M.I.N CORE...',
  '> LOADING NEURAL MODULES........ OK',
  '> CONNECTING GEMINI LINK......... OK',
  '> SEARCH MODULE.................. OK',
  '> VOICE INTERFACE................ OK',
  '> SYSTEM ONLINE',
];

export function runBoot() {
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

export function recordLatency(ms) {
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

function formatHMS(totalSeconds) {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  return [h, m, s].map((n) => String(n).padStart(2, '0')).join(':');
}

// เดิม poll server ทุก 1 วิเพื่อให้ตัวนับถอยหลัง cooldown ลื่น แต่นั่นคือ 86,400 request/วันแม้ไม่ได้ใช้งานเลย
// เปลี่ยนมา sync กับ server ห่างขึ้น (ยังพอให้ LINK OK/LOST ไวพอสำหรับแอปบนเครื่องเดียวกัน) แล้วนับถอยหลัง
// cooldown เองฝั่ง client จากค่าล่าสุดที่รู้ + เวลาที่ผ่านไป ไม่ต้องยิง request ทุกวินาที
export const QUOTA_SYNC_MS = 5000;
let lastQuota = { used: 0, limit: null, remaining: null, cooldown_seconds: 0 };
let lastQuotaFetchedAt = 0;

export function renderQuotaDisplay() {
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

export async function refreshQuota() {
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
