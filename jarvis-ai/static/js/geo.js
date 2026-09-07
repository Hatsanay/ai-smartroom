import { S } from './state.js';

/* ---------- ตำแหน่งปัจจุบันของเบราว์เซอร์: แนบไปกับ /api/chat ให้ get_weather() ใช้พิกัดจริงตอน
   ผู้ใช้ถามอากาศ "ที่นี่" โดยไม่ต้องพิมพ์ชื่อเมือง — มีแต่เบราว์เซอร์ที่รู้พิกัด (tool รันฝั่ง server)
   ถ้าผู้ใช้ไม่อนุญาต ก็ปล่อยเป็น null แล้ว get_weather() จะถามชื่อเมืองกลับตามเดิม (ไม่พังอะไร) */

let geoInFlight = false; // กัน getCurrentPosition ซ้อนกันหลายเส้นทางที่เรียก refreshClientGeo()
export const GEO_MAX_AGE_MS = 10 * 60 * 1000; // เกินนี้ถือว่าเก่า ค่อยขอพิกัดใหม่
export const GEO_RETRY_MS = 20000; // เว้นอย่างน้อยเท่านี้ระหว่าง retry ตอน submit

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

export function refreshClientGeo() {
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
  S.geoLastAttemptAt = Date.now();
  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      geoInFlight = false;
      const lat = +pos.coords.latitude.toFixed(4); // ~11m พอสำหรับอากาศ + หยาบลงนิดเรื่อง privacy
      const lon = +pos.coords.longitude.toFixed(4);
      // เซ็ตพิกัดไว้ก่อนเลย เผื่อ reverse geocode ค้าง/ล่ม จะได้มีพิกัดส่งให้ server ทันที
      S.clientGeo = { lat, lon, label: null };
      S.clientGeoFetchedAt = Date.now();
      const label = await reverseGeocodeLabel(lat, lon);
      if (label && S.clientGeo && S.clientGeo.lat === lat && S.clientGeo.lon === lon) S.clientGeo.label = label;
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
  if (document.visibilityState === 'visible' && !S.clientGeo) refreshClientGeo();
});
