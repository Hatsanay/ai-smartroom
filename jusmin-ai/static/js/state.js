/* state ที่ใช้ "ข้ามโมดูล" — ES module import เป็น read-only binding เขียนไม่ได้ แต่ mutate property
   ของ object ที่ import มาได้ เลยรวม flag ที่หลายโมดูลต้องอ่าน+เขียนไว้ใน object เดียว (S)
   ทุกที่ที่เดิมเขียน `engagedActive = true` -> `S.engagedActive = true`; อ่าน `if (ttsSpeaking)` -> `if (S.ttsSpeaking)`
   flag ที่ใช้ในไฟล์เดียว (selectedEngine, recognition, ytVolume, followUpActive, ...) ยังเป็น let ในไฟล์นั้นตามเดิม */
export const S = {
  engagedActive: false, // ได้ยิน "จัสมิน" แล้ว -> สีเขียว + โชว์แชท (voice/chat เขียน, wave อ่าน)
  ttsSpeaking: false, // จัสมิน กำลังพูด (sound เขียน, wave/voice/youtube อ่าน)
  wakeMode: false, // โหมดฟังตลอดเปิดอยู่ (voice เขียน, wave อ่าน)
  listening: false, // ปุ่มกดพูด (push-to-talk) เปิดอยู่ (voice เขียน, wave อ่าน)

  ytPlayer: null, // YT.Player instance (youtube เขียน, voice อ่านเช็คว่ามีเพลงอยู่ไหม)
  ytIsPlaying: false, // state จริงจาก onStateChange (youtube เขียน, voice อ่านกันข้ามช่วงคุยต่อเนื่องตอนเพลงเล่น)
  ytMaximized: false, // เต็มจอ CSS อยู่ไหม (youtube เขียน, wave อ่านจับ edge ย่อจอตอนถูกเรียก)
  ytWasMaximizedBeforeEngage: false, // ย่อจอชั่วคราวเพราะถูกเรียก -> กลับไปเต็มจอตอนคุยจบ (youtube/wave/voice ใช้ร่วม)

  clientGeo: null, // { lat, lon, label } พิกัดเบราว์เซอร์ (geo เขียน, chat submit อ่านแนบไป /api/chat)
  clientGeoFetchedAt: 0,
  geoLastAttemptAt: 0, // rate-limit การ retry ตอน submit
};
