import { settingsBtn, sidebar, sidebarScrim, sidebarClose, folderBtn } from './dom.js';

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

/* ---------- โฟลเดอร์ที่อนุญาตให้ จัสมิน อ่านไฟล์ได้: state จริงจาก server เท่านั้น (ไม่ใช่แค่จำ
   ไว้ฝั่ง browser) เพราะ server เป็นคนตรวจ path จริงตอน list_files()/read_file() ถูกเรียก ต้อง sync
   กับ server เสมอไม่งั้นปุ่มจะโชว์ค่าที่ไม่ตรงกับที่ backend ใช้งานจริงอยู่ (ผิดหลักการ "ห้ามโชว์ข้อมูลปลอม") */

function updateFolderBtnLabel(path) {
  if (path) {
    const name = path.split(/[\\/]/).filter(Boolean).pop() || path;
    folderBtn.textContent = `📁 ${name}`;
    folderBtn.title = `จัสมิน เข้าถึงไฟล์ได้แค่ในนี้: ${path} (กดเพื่อเปลี่ยน)`;
    folderBtn.classList.add('configured');
  } else {
    folderBtn.textContent = '📁 เลือกโฟลเดอร์';
    folderBtn.title = 'ยังไม่ได้ตั้งค่า — กดเพื่อเลือกโฟลเดอร์ที่ให้ จัสมิน เข้าถึงไฟล์ได้';
    folderBtn.classList.remove('configured');
  }
}

export async function refreshFolderStatus() {
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
