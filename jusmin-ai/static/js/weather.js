import {
  weatherPanel, weatherLocation, weatherEmoji, weatherTemp, weatherCondition,
  weatherFeelsLike, weatherHumidity, weatherWind, weatherForecast, weatherFx,
  weatherChips, weatherWindRow, weatherHourly, weatherFocus,
} from './dom.js';

/* ---------- สภาพอากาศ: ข้อมูลจริงจาก Open-Meteo ทั้งหมด (คำนวณ/แปล emoji มาจาก server แล้ว
   ดู tools.py) ฝั่งนี้แค่เอาไปแปะแสดงผลตรงๆ ไม่มีการเดา/เติมค่าเองเลย ---------- */

const WEATHER_DAY_NAMES = ['อา', 'จ', 'อ', 'พ', 'พฤ', 'ศ', 'ส'];

// ปิด panel เองอัตโนมัติ 30 วิ "หลัง จัสมิน พูดตอบจบจริง" (ไม่ใช่หลังได้ข้อมูลมา) ผู้ใช้ขอไว้ — เรียก
// scheduleWeatherHide() จาก onDone callback ของ speak() เดียวกับที่คุมช่วงคุยต่อเนื่อง 15 วิ ตรงกับ
// pattern เดิมของโปรเจกต์ (นับเวลาจากเสียงพูดหยุดจริง ไม่ใช่จากตอนได้คำตอบมา)
const WEATHER_AUTO_HIDE_MS = 30000;
let weatherHideTimer = null;

export function scheduleWeatherHide() {
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

// stat chip เล็กๆ: พระอาทิตย์ขึ้น/ตก + UV + โอกาสฝนวันนี้ — ทุกค่ามาจาก Open-Meteo (daily) จริง
// อันไหนไม่มีข้อมูลก็ไม่ต้องสร้าง chip (ไม่โชว์ค่าเดา/ค่าว่าง)
function renderWeatherChips(data) {
  weatherChips.innerHTML = '';
  const addChip = (icon, text) => {
    const c = document.createElement('div');
    c.className = 'weather-chip';
    const ic = document.createElement('span');
    ic.className = 'wc-icon';
    ic.textContent = icon;
    const tx = document.createElement('span');
    tx.textContent = text;
    c.append(ic, tx);
    weatherChips.appendChild(c);
  };
  if (data.sunrise) addChip('🌅', data.sunrise);
  if (data.sunset) addChip('🌇', data.sunset);
  if (data.uv_index != null) addChip('🔆', `UV ${data.uv_index}${data.uv_label ? ' ' + data.uv_label : ''}`);
  if (data.precip_today != null) addChip('💧', `ฝน ${data.precip_today}%`);
  weatherChips.style.display = weatherChips.children.length ? '' : 'none';
}

// ทิศทางลม: ลูกศรหมุนตามองศาจริง (wind_direction = ทิศที่ลมพัดมาจาก -> ลูกศรชี้ +180 = ทิศที่ลมพัดไป) + ลมกระโชก
function renderWeatherWind(data) {
  weatherWindRow.innerHTML = '';
  if (data.wind_direction == null && data.wind_gusts == null) {
    weatherWindRow.style.display = 'none';
    return;
  }
  weatherWindRow.style.display = '';
  const arrow = document.createElement('span');
  arrow.className = 'wind-arrow';
  arrow.textContent = '↑';
  if (data.wind_direction != null) arrow.style.transform = `rotate(${(data.wind_direction + 180) % 360}deg)`;
  const label = document.createElement('span');
  let t = data.wind_direction_label ? `ลมจากทิศ${data.wind_direction_label}` : 'ทิศทางลม';
  if (data.wind_gusts != null) t += ` · กระโชก ${data.wind_gusts} กม./ชม.`;
  label.textContent = t;
  weatherWindRow.append(arrow, label);
}

// กราฟ SVG อเนกประสงค์: เส้นค่า (cyan) + แท่งพื้นหลังจางๆ (ถ้ามี) — ใช้ทั้งกราฟ 12 ชม.หน้าหลัก
// และกราฟโฟกัส (ฝน/อุณหภูมิ/ลม/UV รายชั่วโมง) series = [{label:"14:00", value:<num>, bar:<num|null>}]
const SVG_NS = 'http://www.w3.org/2000/svg';
function renderSeriesChart(el, series, opts) {
  el.innerHTML = '';
  const pts = (series || []).filter((s) => s && s.value != null);
  if (pts.length < 2) {
    el.style.display = 'none';
    return;
  }
  el.style.display = '';
  const o = opts || {};
  const unit = o.unit || '';
  const showEvery = o.showEvery || Math.max(1, Math.round(series.length / 6));
  const n = series.length;
  const W = 276;
  const H = 92;
  const padX = 8;
  const padTop = 16;
  const padBot = 24;
  const plotH = H - padTop - padBot;
  const vals = pts.map((s) => s.value);
  const vMin = o.valMin != null ? o.valMin : Math.min(...vals);
  const vMax = o.valMax != null ? o.valMax : Math.max(...vals);
  const vSpan = vMax - vMin || 1;
  const barVals = series.filter((s) => s && s.bar != null && s.bar > 0).map((s) => s.bar);
  const barMax = o.barMax != null ? o.barMax : (barVals.length ? Math.max(...barVals) : 1);
  const x = (i) => padX + (i / (n - 1)) * (W - padX * 2);
  const y = (v) => padTop + (1 - (v - vMin) / vSpan) * plotH;

  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.setAttribute('class', 'hourly-svg');

  const barW = Math.max(3, (W - padX * 2) / n - 3);
  series.forEach((s, i) => {
    if (!s || s.bar == null || s.bar <= 0) return;
    const bh = Math.min(1, s.bar / barMax) * plotH;
    const r = document.createElementNS(SVG_NS, 'rect');
    r.setAttribute('x', (x(i) - barW / 2).toFixed(1));
    r.setAttribute('y', (H - padBot - bh).toFixed(1));
    r.setAttribute('width', barW.toFixed(1));
    r.setAttribute('height', bh.toFixed(1));
    r.setAttribute('class', 'hourly-precip');
    svg.appendChild(r);
  });

  const line = document.createElementNS(SVG_NS, 'polyline');
  line.setAttribute(
    'points',
    series.map((s, i) => (s && s.value != null ? `${x(i).toFixed(1)},${y(s.value).toFixed(1)}` : null)).filter(Boolean).join(' ')
  );
  line.setAttribute('class', 'hourly-line');
  svg.appendChild(line);

  series.forEach((s, i) => {
    if (!s || s.value == null) return;
    if (i % showEvery !== 0 && i !== n - 1) return;
    const dot = document.createElementNS(SVG_NS, 'circle');
    dot.setAttribute('cx', x(i).toFixed(1));
    dot.setAttribute('cy', y(s.value).toFixed(1));
    dot.setAttribute('r', '2');
    dot.setAttribute('class', 'hourly-dot');
    svg.appendChild(dot);

    const tl = document.createElementNS(SVG_NS, 'text');
    tl.setAttribute('x', x(i).toFixed(1));
    tl.setAttribute('y', (y(s.value) - 6).toFixed(1));
    tl.setAttribute('class', 'hourly-temp-label');
    tl.textContent = `${Math.round(s.value)}${unit}`;
    svg.appendChild(tl);

    const xl = document.createElementNS(SVG_NS, 'text');
    xl.setAttribute('x', x(i).toFixed(1));
    xl.setAttribute('y', (H - 7).toFixed(1));
    xl.setAttribute('class', 'hourly-x-label');
    xl.textContent = (s.label || '').slice(0, 2);
    svg.appendChild(xl);
  });

  el.appendChild(svg);
}

// กราฟ 12 ชม.หน้าหลัก (view "now"): เส้นอุณหภูมิ + แท่งโอกาสฝน
function renderHourly(hourly) {
  renderSeriesChart(
    weatherHourly,
    (hourly || []).map((h) => ({ label: h.time, value: h.temp, bar: h.precip })),
    { unit: '°', barMax: 100 }
  );
}

function renderForecastInto(el, forecast) {
  el.innerHTML = '';
  (forecast || []).forEach((day) => {
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

    if (day.precip != null && day.precip > 0) {
      const p = document.createElement('span');
      p.className = 'fc-precip';
      p.textContent = `${day.precip}%`;
      div.appendChild(p);
    }

    el.appendChild(div);
  });
}

// บล็อกโฟกัส: การ์ดปรับ layout ตาม data.view (rain/temperature/wind/uv/sun) ให้ตรงกับสิ่งที่ผู้ใช้ถาม
function renderWeatherFocus(data) {
  weatherFocus.innerHTML = '';

  const head = document.createElement('div');
  head.className = 'wf-head';
  head.textContent = [data.day_label, data.headline].filter(Boolean).join(' · ');
  weatherFocus.appendChild(head);

  const chart = document.createElement('div');
  chart.className = 'wf-chart';

  if (data.view === 'rain') {
    weatherFocus.appendChild(chart);
    renderSeriesChart(
      chart,
      (data.rain_series || []).map((s) => ({ label: s.time, value: s.prob, bar: s.prob })),
      { unit: '%', valMin: 0, valMax: 100, barMax: 100 }
    );
    if (data.rain_windows && data.rain_windows.length) {
      const wrap = document.createElement('div');
      wrap.className = 'wf-windows';
      data.rain_windows.forEach((w) => {
        const c = document.createElement('span');
        c.className = 'wf-win';
        c.textContent = `🌧️ ${w.start}–${w.end} · สูงสุด ${w.peak}%`;
        wrap.appendChild(c);
      });
      weatherFocus.appendChild(wrap);
    }
  } else if (data.view === 'temperature') {
    weatherFocus.appendChild(chart);
    renderSeriesChart(chart, (data.temp_series || []).map((s) => ({ label: s.time, value: s.temp })), { unit: '°' });
  } else if (data.view === 'wind') {
    weatherFocus.appendChild(chart);
    renderSeriesChart(
      chart,
      (data.wind_series || []).map((s) => ({ label: s.time, value: s.speed, bar: s.gust })),
      { unit: '' }
    );
    if (data.wind_direction != null || data.wind_direction_label) {
      const sub = document.createElement('div');
      sub.className = 'wf-subhead';
      const ar = document.createElement('span');
      ar.className = 'wind-arrow';
      ar.textContent = '↑';
      if (data.wind_direction != null) ar.style.transform = `rotate(${(data.wind_direction + 180) % 360}deg)`;
      const tx = document.createElement('span');
      tx.textContent = data.wind_direction_label ? `ลมจากทิศ${data.wind_direction_label} · แท่ง = ลมกระโชก` : '';
      sub.append(ar, tx);
      weatherFocus.appendChild(sub);
    }
  } else if (data.view === 'uv') {
    weatherFocus.appendChild(chart);
    const mx = Math.max(11, ...(data.uv_series || []).map((s) => s.uv || 0));
    renderSeriesChart(chart, (data.uv_series || []).map((s) => ({ label: s.time, value: s.uv })), { unit: '', valMin: 0, valMax: mx });
  } else if (data.view === 'sun') {
    const box = document.createElement('div');
    box.className = 'wf-sun';
    const big = document.createElement('div');
    big.className = 'wf-sun-times';
    big.textContent = `🌅 ${data.sun_sunrise || '--:--'}     🌇 ${data.sun_sunset || '--:--'}`;
    box.appendChild(big);
    if (data.day_length_h != null) {
      const dl = document.createElement('div');
      dl.className = 'wf-sun-len';
      dl.textContent = `กลางวันยาว ${data.day_length_h} ชม. ${data.day_length_m} นาที`;
      box.appendChild(dl);
    }
    (data.sun_next || []).forEach((s) => {
      const row = document.createElement('div');
      row.className = 'wf-sun-row';
      row.textContent = `${s.label}   🌅 ${s.sunrise || '--'}   🌇 ${s.sunset || '--'}`;
      box.appendChild(row);
    });
    weatherFocus.appendChild(box);
  }
}

export function showWeather(data) {
  clearTimeout(weatherHideTimer); // ถามอากาศที่ใหม่ระหว่างนับถอยหลังเดิมอยู่ -> เคลียร์ตัวเก่าทิ้งก่อน
  const view = data.view || 'now';
  weatherPanel.dataset.view = view;
  renderWeatherFx(data.fx);

  weatherLocation.textContent = data.location || '-';
  weatherEmoji.textContent = data.emoji || '❓';
  weatherTemp.textContent = data.temperature != null ? `${data.temperature}°` : '--°';
  weatherCondition.textContent = data.condition || '-';
  weatherFeelsLike.textContent = data.feels_like != null ? `รู้สึกเหมือน ${data.feels_like}°` : '';
  weatherHumidity.textContent = data.humidity != null ? `ความชื้น ${data.humidity}%` : '';
  weatherWind.textContent = data.wind_speed != null ? `ลม ${data.wind_speed} กม./ชม.` : '';

  // เคลียร์ทุกบล็อกก่อน แล้วเติมเฉพาะที่ view นี้ใช้ (CSS `[data-view]` ซ่อน section ที่ไม่ใช้)
  weatherFocus.innerHTML = '';
  weatherChips.innerHTML = '';
  weatherWindRow.innerHTML = '';
  weatherHourly.innerHTML = '';
  weatherForecast.innerHTML = '';

  if (view === 'now') {
    renderWeatherChips(data);
    renderWeatherWind(data);
    renderHourly(data.hourly);
    renderForecastInto(weatherForecast, data.forecast);
  } else if (view === 'forecast') {
    const head = document.createElement('div');
    head.className = 'wf-head';
    head.textContent = [data.day_label, data.headline].filter(Boolean).join(' · ');
    weatherFocus.appendChild(head);
    renderForecastInto(weatherForecast, data.forecast);
  } else {
    renderWeatherFocus(data);
  }

  weatherPanel.classList.add('visible');
}

