/* ค้น/ดู รูป-วิดีโอ — HUD ฝั่ง client
   - showMediaResults : ตาราง thumbnail จากผล search_media (คลิก = สั่ง "เปิดอันที่ N")
   - showMedia        : ตัวดูเต็มจอ (รับ gallery ทั้งชุด + index -> เลื่อน prev/next ในเครื่องได้ทันที)
   - hideMedia        : ปิด + คืน stream ของ <video> */
import {
  form, input,
  mediaGridPanel, mediaGrid, mediaGridTitle, mediaGridClose,
  mediaViewer, mediaStage, mediaTitle, mediaPos, mediaSource,
  mediaPrev, mediaNext, mediaClose, mediaDownload,
} from './dom.js';

let gallery = [];
let idx = 0;

// สั่ง จัสมิน ผ่านช่องพิมพ์ (เหมือนผู้ใช้พิมพ์เอง) — ใช้ตอนคลิก tile / กดปุ่ม ⬇
function ask(text) {
  input.value = text;
  form.requestSubmit();
}

export function showMediaResults(data) {
  const items = data.items || [];
  mediaGridTitle.textContent = `ผลการค้นหา${data.query ? ': ' + data.query : ''} (${items.length})`;
  mediaGrid.innerHTML = '';
  for (const it of items) {
    const tile = document.createElement('div');
    tile.className = 'media-tile';
    tile.title = it.title || '';

    const img = document.createElement('img');
    img.loading = 'lazy';
    img.alt = it.title || '';
    img.src = it.thumb || it.url || '';
    img.onerror = () => { tile.classList.add('broken'); img.remove(); };
    tile.appendChild(img);

    const num = document.createElement('span');
    num.className = 'mt-num';
    num.textContent = it.n;
    tile.appendChild(num);

    if (it.kind === 'video') {
      const play = document.createElement('span');
      play.className = 'mt-play';
      play.textContent = '▶';
      tile.appendChild(play);
      if (it.duration) {
        const d = document.createElement('span');
        d.className = 'mt-dur';
        d.textContent = it.duration;
        tile.appendChild(d);
      }
    }

    tile.addEventListener('click', () => ask(`เปิดอันที่ ${it.n}`));
    mediaGrid.appendChild(tile);
  }
  mediaGridPanel.classList.add('visible');
}

function closeGrid() {
  mediaGridPanel.classList.remove('visible');
}

let slideMs = 0;
let slideTimer = null;

function stopSlide() {
  if (slideTimer) { clearInterval(slideTimer); slideTimer = null; }
}
function startSlide(ms) {
  stopSlide();
  slideMs = ms;
  if (ms > 0 && gallery.length > 1) slideTimer = setInterval(() => render(idx + 1), ms);
}

export function showMedia(data) {
  gallery = data.list || [];
  render(data.index || 0);
  startSlide((data.slideshow || 0) * 1000); // slideshow=0 -> stopSlide()
}

function render(i) {
  if (!gallery.length) return;
  idx = ((i % gallery.length) + gallery.length) % gallery.length;
  const it = gallery[idx];

  const oldV = mediaStage.querySelector('video');
  if (oldV) { oldV.pause(); oldV.removeAttribute('src'); oldV.load(); }
  mediaStage.innerHTML = '';
  let el;
  if (it.kind === 'video') {
    el = document.createElement('video');
    el.src = it.src;
    el.controls = true;
    el.autoplay = true;
    el.playsInline = true;
  } else {
    el = document.createElement('img');
    el.src = it.src;
    el.alt = it.name || '';
    el.addEventListener('click', () => el.classList.toggle('zoomed'));
  }
  mediaStage.appendChild(el);

  mediaTitle.textContent = it.name || '';
  mediaSource.textContent = it.source || '';
  const multi = gallery.length > 1;
  mediaPos.textContent = multi ? `${idx + 1}/${gallery.length}` : '';
  mediaPrev.hidden = !multi;
  mediaNext.hidden = !multi;
  mediaDownload.hidden = !it.ref;
  mediaDownload.onclick = it.ref ? () => ask(`โหลดอันที่ ${it.ref}`) : null;

  mediaViewer.hidden = false;
}

export function hideMedia() {
  stopSlide();
  const v = mediaStage.querySelector('video');
  if (v) {
    v.pause();
    v.removeAttribute('src');
    v.load();
  }
  mediaStage.innerHTML = '';
  mediaViewer.hidden = true;
  closeGrid(); // "ปิด" = เก็บทั้งตัวดูเต็มจอ + ตารางผลค้น
}

function nav(step) {
  if (gallery.length < 2) return;
  render(idx + step);
  if (slideTimer) startSlide(slideMs); // เลื่อนเองระหว่างสไลด์ -> รีเซ็ตนาฬิกา เล่นต่อ
}

mediaGridClose.addEventListener('click', closeGrid);
mediaClose.addEventListener('click', hideMedia);
mediaPrev.addEventListener('click', () => nav(-1));
mediaNext.addEventListener('click', () => nav(1));
mediaViewer.addEventListener('click', (e) => {
  if (e.target === mediaViewer) hideMedia();
});
window.addEventListener('keydown', (e) => {
  if (!mediaViewer.hidden) {
    if (e.key === 'Escape') hideMedia();
    else if (e.key === 'ArrowRight') nav(1);
    else if (e.key === 'ArrowLeft') nav(-1);
  } else if (e.key === 'Escape' && mediaGridPanel.classList.contains('visible')) {
    closeGrid(); // Esc ปิดตารางผลค้นได้เลย (ตอนยังไม่เปิดตัวดูเต็มจอ)
  }
});
