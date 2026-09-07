# Plan 03 — ต่อ จาร์วิส เข้ากับเครื่องพิมพ์ 3 มิติ Bambu Lab

> **สถานะ: ยังไม่เริ่ม — รอเครื่อง** · **รุ่นที่ผู้ใช้เลือกแล้ว = Bambu Lab P2S Combo (P2S + AMS 2 Pro)**
> เป้าหมายผู้ใช้: *"ผมมีหน้าที่แค่ออกแบบโมเดล แล้ววางไฟล์ — ที่เหลือ จาร์วิส จัดการ"*
> ข้อมูลในไฟล์นี้ **ค้นจากเอกสารจริง ไม่ใช่ความจำ** (ก.ย. 2026) — ดู Sources ท้ายไฟล์
> §1.7 = ข้อเท็จจริงเฉพาะ P2S ที่ **ต่างจากรุ่นอื่นและมีผลกับโค้ด** อ่านก่อนเริ่ม step 1

## ⚠️ อ่านก่อนลงมือ — ข้อมูลนี้อาจล้าสมัย
Bambu Lab **เคยล็อกการเข้าถึงจากภายนอกมาแล้ว** (Authorization Control System, ม.ค. 2025 — ทำ OrcaSlicer
และ Panda Touch ใช้ไม่ได้ชั่วคราว) มีความเป็นไปได้ที่จะเปลี่ยนอีก
**ก่อน implement ต้องเช็คใหม่ทุกครั้ง:**
1. Developer Mode ยังมีอยู่ไหม / เปิดยังไง
2. MQTT/FTPS ยังเปิดตามนี้ไหม
3. flag ของ Bambu Studio CLI เปลี่ยนไหม (ต่างกันตามเวอร์ชัน)
4. `bambulabs-api` เวอร์ชันล่าสุดรองรับรุ่นที่ซื้ออะไรบ้าง

---

## 1. ข้อเท็จจริงที่ยืนยันแล้ว (ฐานของแผนนี้)

### 1.1 เงื่อนไขบังคับ — Developer Mode
- ตั้งแต่ firmware ม.ค. 2025 มี **Authorization Control System** ล็อกการสั่งงานจากภายนอก
  (เริ่มพิมพ์ผ่าน LAN/cloud, คุมมอเตอร์/อุณหภูมิ/พัดลม/AMS/calibration, ดูวิดีโอ)
- **ทางออกเดียว = Developer Mode** (มีทุกรุ่นตั้งแต่ 21 มิ.ย. 2025) → กลับมาเหมือน LAN mode เดิม ไม่ต้อง authorization
- เปิดที่: **Settings → WLAN/Network → LAN Mode Only → Developer Mode**
  (toggle Developer Mode **โผล่หลังเปิด LAN-only แล้วเท่านั้น**)
- firmware ขั้นต่ำที่มี Developer Mode: X1 `01.08.03.00` · P1 `01.08.02.00` · A1 `01.05.00.00` · H2D `01.01.00.01`
  · **P2 series = ติดมาตั้งแต่โรงงาน (shipped with Developer Mode from the start)** → **P2S ไม่ต้องอัปเฟิร์มแวร์ก่อน**
- **H2D / H2S / H2C ต้องเปิดทั้ง LAN-only + Developer Mode** ไม่งั้นต่อติดแต่ไม่ตอบ status
- Bambu ระบุชัด: ผู้ใช้รับผิดชอบความปลอดภัยเครือข่ายเอง **ไม่มี customer support สำหรับโหมดนี้**

**ราคาที่ต้องจ่าย (ผู้ใช้ต้องยอมรับก่อนเริ่ม):**
- ❌ Bambu Handy ใช้จากนอกบ้านไม่ได้ (ใช้ได้เฉพาะใน wifi เดียวกัน)
- ❌ สั่ง/ดูเครื่องจากนอกบ้านผ่าน cloud
- ❌ Print History + สถิติบน cloud
- ✅ workaround: VPN ที่บ้าน (Tailscale / WireGuard)

### 1.2 MQTT (คุมเครื่อง + อ่านสถานะ)
- `{PRINTER_IP}:8883` **TLS** · username `bblp` · password = **Access Code** (จากจอเครื่อง)
- topic: `device/{SERIAL}/report` (สถานะ) · `device/{SERIAL}/request` (คำสั่ง)
- X1 ส่งสถานะเต็มทุกรอบ · **P1 ส่งเฉพาะค่าที่เปลี่ยน** (ต้อง cache ฝั่งเราเอง)
- `pushing.pushall` = ขอสถานะเต็ม

**คำสั่งที่ใช้ได้ (verbatim):**
| กลุ่ม | คำสั่ง |
|---|---|
| งานพิมพ์ | `print.pause` · `print.resume` · `print.stop` (QoS 1) · `print.project_file` (พิมพ์ 3mf) · `print.gcode_file` · `print.gcode_line` (raw G-code) · `print.skip_objects` |
| ความเร็ว/ออปชัน | `print.print_speed` (1=silent 2=standard 3=sport 4=ludicrous) · `print.print_option` (auto_recovery, sound_enable) |
| AMS | `print.ams_change_filament` · `print.ams_get_rfid` · `print.ams_user_setting` · `print.ams_filament_setting` · `print.ams_control` · `print.unload_filament` |
| ระบบ | `system.ledctrl` (chamber_light/work_light: on/off/flashing) · `system.get_access_code` · `system.set_accessories.nozzle` · `info.get_version` |
| กล้อง/AI | `camera.ipcam_record_set` · `camera.ipcam_timelapse` · `xcam.xcam_control_set` (first_layer_inspector, spaghetti_detector) |
| คาลิเบรต | `print.calibration` (bitmask) |
| เฟิร์มแวร์ | `upgrade.start` · `upgrade.get_history` · `upgrade.upgrade_confirm` |

**ฟิลด์สถานะที่อ่านได้ (verbatim):**
| กลุ่ม | ฟิลด์ |
|---|---|
| งานพิมพ์ | `gcode_state` (IDLE/PRINTING/PAUSED/FINISH/FAILED) · `gcode_file` · `mc_percent` · `mc_remaining_time` (วินาที) · `gcode_start_time` · `mc_print_stage` / `mc_print_sub_stage` · `print_type` · `task_id` |
| ชั้น | `layer_num` · `total_layer_num` |
| อุณหภูมิ | `nozzle_temper` / `nozzle_target_temper` · `bed_temper` / `bed_target_temper` · `chamber_temper` |
| พัดลม (0–255) | `cooling_fan_speed` · `big_fan1_speed` · `big_fan2_speed` · `heatbreak_fan_speed` |
| AMS | `ams.ams[].id` / `.temp` / `.humidity` · `ams.ams[].tray[].id` / `tray_type` / `tray_color` / `tray_weight` / `nozzle_temp_min` / `nozzle_temp_max` · `tray_now` / `tray_tar` / `tray_pre` · `vt_tray` (ม้วนนอก) · `ams_status` · `ams_rfid_status` |
| ข้อผิดพลาด | `hms[]` · `print_error` · `mc_print_error_code` · `fail_reason` |
| ระบบ | `sdcard` · `wifi_signal` (dBm) · `nozzle_diameter` · `home_flag` · `maintain` · `online.*` |
| ความเร็ว | `spd_lvl` · `spd_mag` (%) |
| ไฟ | `lights_report[].node` / `.mode` |
| AI ในตัว | `xcam.first_layer_inspector` · `xcam.spaghetti_detector` · `xcam.printing_monitor` · `xcam.halt_print_sensitivity` |
| อัปโหลด | `upload.status` / `progress` / `speed` |
| เฟิร์มแวร์ | `upgrade_state.status` / `new_version_state` / `ota_new_version_number` |
| ข้ามชิ้น | `s_obj[]` |

**HMS error code**: รูปแบบ 4 กลุ่ม 4 ตัว (เช่น `0700-xxxx-xxxx-xxxx` = AMS ป้อนไส้, `0300-...` = ฐาน/อุณหภูมิ)
Bambu มีหน้า wiki ต่อรหัส → **ใช้ `read_url()` ที่มีอยู่แล้วดึงคำอธิบายมาแปลไทยได้**

### 1.3 FTPS (อัปโหลดไฟล์เข้าเครื่อง)
- `{PRINTER_IP}:990` **implicit TLS** · user `bblp` · password = Access Code
- ต้องเปิด passive port range **50000–50100** ด้วย
- ปลายทางที่เขียนลง **ต่างกันตามรุ่น**: X1 / P1 / A1 = **microSD ต้องเสียบอยู่ + FAT32** ·
  **P2S = ไม่มีช่อง SD เลย → เขียนลง eMMC 8 GB ในตัว หรือ USB ที่เสียบ** (ดู §1.7)
- รับ `.gcode` · `.3mf` · `.stl`
- หมายเหตุ: สั่งพิมพ์ `.3mf` ต้องมี Developer Mode · `.gcode` ไม่ต้อง

### 1.4 สไลซ์อัตโนมัติ — Bambu Studio CLI
```bash
bambu-studio --slice 1 \
  --load-settings "machine.json;process.json" \
  --load-filaments "filament.json" \
  --allow-newer-file --skip-useless-pick \
  --outputdir <TEMPDIR> \
  --arrange 1 --orient \
  --export-3mf out.gcode.3mf   model.stl
```
- ผลลัพธ์ = **`.gcode.3mf`** (3MF archive ที่มี G-code ข้างใน — เครื่อง Bambu กินตรงๆ) · G-code ดิบอยู่ที่ `Metadata/plate_N.gcode`
- **ไม่ต้องมีจอ/GUI — รัน headless ได้**
- flag อื่น: `--scale` · `--curr-bed-type` · `--export-slicedata` · `--export-png` (≥2.1.0) · `--estimate-mode` (≥2.7.1)
- ลำดับความสำคัญของค่า: command-line (`--key=value`) > `--load-settings`/`--load-filaments` > ค่าใน 3mf
- ⚠️ **ต้องมี JSON 3 ไฟล์** (machine / process / filament) — **export จาก Bambu Studio GUI ครั้งเดียว**
  (ค่า default ของรุ่นนั้นใช้ได้เลย ไม่ต้องจูน) · profile ของ Bambu Studio กับ Orca **ใช้แทนกันไม่ได้**
- ⚠️ **แต่ละ slice สร้าง temp file หลายร้อย MB** ในโฟลเดอร์ทำงาน → **ต้องรันใน temp dir แยก แล้วลบทิ้งทุกครั้ง**

### 1.5 ไลบรารี Python
- **`bambulabs-api`** (PyPI, ≥2.6.6, Python ≥3.10) — MQTT + camera + FTP
- เมธอดที่มี (verbatim): `connect` · `disconnect` · `mqtt_client_connected` · `get_current_state` · `get_state` · `get_percentage` · `get_time` · `get_file_name` · `print_error_code` · `get_bed_temperature` · `get_nozzle_temperature` · `get_chamber_temperature` · `current_layer_num` · `total_layer_num` · `start_print` · `pause_print` · `resume_print` · `stop_print` · `set_bed_temperature` · `set_nozzle_temperature` · `set_print_speed` · `get_print_speed` · `set_part_fan_speed` · `set_aux_fan_speed` · `set_chamber_fan_speed` · `turn_light_on` · `turn_light_off` · `get_light_state` · `ams_hub` · `vt_tray` · `load_filament_spool` · `unload_filament_spool` · `set_filament_printer` · `home_printer` · `move_z_axis` · `calibrate_printer` · `skip_objects` · `camera_start` / `camera_stop` / `get_camera_frame` (base64) / `get_camera_image` (PIL Image) · `upload_file` · `delete_file` · `nozzle_diameter` · `nozzle_type` · `wifi_signal` · `reboot` · `gcode`
- ⚠️ เอกสารระบุ: **X1 ยังไม่รองรับเต็ม — กล้องยังไม่ implement ในเวอร์ชันก่อน 2.7.0** → ต้องเช็คตอนติดตั้งจริง
- ทางเลือกอ้างอิง: HA integration `greghesp/ha-bambulab` (โตกว่า ใช้เป็น reference ได้)

### 1.6 กล้อง — คุณภาพต่างกันตามรุ่น
| รุ่น | กล้อง |
|---|---|
| **P2S** | **1920×1080 @ 30 fps** + AI spaghetti detection (ดีที่สุดในตระกูล P) |
| X1 series | 1080p เฟรมเรตดีสุด |
| P1 series | เฟรมเรตพอใช้ (ESP32 แรงไม่พอ) |
| A1 / A1 mini | **~1–2 fps** (มี Live View Camera ขายแยก) |

---

### 1.7 ⚠️ เฉพาะ P2S — จุดที่ **ต่างจากรุ่นอื่นและมีผลกับโค้ด**

**สเปกที่เกี่ยวข้อง**
- พื้นที่พิมพ์ **256×256×256 mm** · CoreXY · สูงสุด 600 mm/s · จอสัมผัส 5"
- extruder **DynaSense servo** (แรงบีบ +~70% จาก P1S) · flow calibration ด้วย eddy-current pressure sensor
- **มี chamber temperature sensor จากโรงงาน** (NTC ติดที่เสาหน้า มี part + คู่มือเปลี่ยนบน wiki)
  → ฟิลด์ `chamber_temper` ใช้ได้ · แต่ **ห้องไม่มีฮีตเตอร์** (ไม่เหมาะ PPS-CF / PEEK)
- **AMS 2 Pro** 4 ช่อง · active venting + electromagnetic air valve (อบไส้เร็วขึ้น ~30%) · RFID อ่านชนิด/สีอัตโนมัติ
  · ต่อพ่วงได้สูงสุด **8 ยูนิต / 20 ช่อง** (AMS 2 Pro ×4 + AMS HT ×4)
- **AMS รับ TPU/ไส้ยืดหยุ่นไม่ได้** → ต้องใช้ที่แขวนม้วนด้านข้าง → **`printer_filaments()` ต้องรายงาน `vt_tray` แยก
  และ `slice_model()` ห้ามเลือก TPU จากช่อง AMS**

**⚠️ 1) ไม่มีช่อง microSD — มี eMMC 8 GB ในตัว + USB port**
→ **ตัดข้อ "เสียบ microSD" ออกจาก setup** · `print_model()` อัปโหลดผ่าน FTPS ได้ตามปกติ
แต่ต้องยืนยันตอนเทสจริงว่า path ราก FTPS ชี้ไป eMMC หรือ USB
→ ⚠️ มี issue รู้แล้วบน BambuStudio: **อัปไฟล์เกิน 6 ไฟล์ผ่าน FTP ทำให้ logic จำกัดจำนวนไฟล์ของเครื่องถูกข้าม**
→ **`print_model()` ต้องลบไฟล์เก่าหลังพิมพ์เสร็จ** (`delete_file`) ไม่ให้สะสม

**⚠️ 2) FTPS ของ P2S มี 3 กับดักที่ ftplib มาตรฐานพังทันที**
(รายงานจาก `sowmiksudo/BambuLab-P2S-Automation` ที่ต้องเขียน workaround เอง)
| อาการ | สาเหตุ |
|---|---|
| TLS handshake ถูกปฏิเสธ | **FTPS SNI rejection บน local IP** — ต้องไม่ส่ง SNI / ปิด hostname check |
| ตัดการเชื่อมต่อกลางคัน (WinError 10054) | **บังคับ SSL Session-ID reuse บน data channel** — ต้องผูก session ของ data ให้ตรงกับ control |
| เครื่องค้าง/รีเซ็ตตอนส่งคำสั่ง | **JSON parser ใน firmware แครชกับ whitespace** — payload MQTT ต้อง `separators=(',',':')` ไม่มีเว้นวรรค/newline |
→ **step 7 (`print_model`) ต้องเผื่อเวลาแก้ 3 เรื่องนี้** อย่าคิดว่า `ftplib.FTP_TLS` ธรรมดาจะผ่าน

**⚠️ 3) กล้องเป็น RTSPS พอร์ต 322 — ไม่ใช่วิธีเดียวกับ X1/P1**
- `rtsps://` + TLS ที่พอร์ต **322** (auth ด้วย `bblp` + Access Code)
- `ha-bambulab` มี issue P2S camera ไม่เสถียร → ปิดเป็น **"external / wontfix"** · workaround ที่ชุมชนใช้ = **go2rtc**
- **ข้อดีสำหรับเรา:** `printer_camera()` ต้องการแค่ **ภาพนิ่ง 1 เฟรม** ไม่ใช่สตรีมต่อเนื่อง →
  **ใช้ ffmpeg ที่โปรเจกต์มีอยู่แล้ว** (`media._ffmpeg_path()` / `imageio-ffmpeg`) ดึงเฟรมเดียวออกมาได้ตรงๆ:
  `ffmpeg -rtsp_transport tcp -i rtsps://bblp:<code>@<ip>:322/streaming/live/1 -frames:v 1 out.jpg`
  → **ไม่ต้องลง go2rtc เพิ่ม** · ⚠️ URL path ยังไม่ยืนยัน ต้องเทสกับเครื่องจริงใน step 5

**⚠️ 4) `bambulabs-api` รองรับ P2S หรือยัง — ยังไม่ยืนยัน**
P2S เป็นรุ่นใหม่ ไลบรารีอาจยังไม่มี model profile
- ✅ ที่ยืนยันแล้ว: **`greghesp/ha-bambulab` รองรับ P2S** (มี issue tracker ของ P2S จริง)
- → **step 1 ต้องเช็คก่อน** ถ้า `bambulabs-api` ยังไม่รองรับ ให้ fallback เป็น **`paho-mqtt` เขียนเอง**
  โดยใช้ `ha-bambulab` (pybambu) เป็น reference ของ schema

---

## 2. Setup ครั้งเดียวที่ผู้ใช้ต้องทำ (ปรับตาม P2S แล้ว)
1. เปิด **LAN Only Mode → Developer Mode** ที่จอเครื่อง (ยอมรับว่าเสีย Handy นอกบ้าน)
   — P2S ติดมาจากโรงงาน **ไม่ต้องอัปเฟิร์มแวร์ก่อน**
2. จด **IP · Serial · Access Code** จากจอเครื่อง → ใส่ `.env`
3. ลง **Bambu Studio** บนเครื่องที่รัน server → **export preset JSON 3 ไฟล์** (machine / process / filament)
   เก็บไว้ที่ `printer_profiles/` (gitignore — เป็นค่าเฉพาะเครื่อง)
   ⚠️ ต้องเป็น preset ของ **P2S + AMS 2 Pro** และ Bambu Studio ต้องเวอร์ชันที่รู้จัก P2S แล้ว
4. ~~เสียบ microSD~~ **P2S ไม่ต้อง** — มี eMMC 8 GB ในตัว (เสียบ USB ได้ถ้าอยากมีที่พักไฟล์แยก)
5. เปิด firewall/router ให้ port **8883** (MQTT) · **990 + 50000–50100** (FTPS) · **322** (กล้อง RTSPS) ในวง LAN

**`.env` keys ใหม่:**
```
BAMBU_HOST=192.168.1.xx
BAMBU_SERIAL=01Sxxxxxxxxxxxx
BAMBU_ACCESS_CODE=12345678
BAMBU_STUDIO_PATH=C:\Program Files\Bambu Studio\bambu-studio.exe
BAMBU_PROFILE_DIR=printer_profiles
```

---

## 3. Tools ที่จะเพิ่ม — `tools/printer.py` (ไฟล์ใหม่)

| tool | ทำอะไร | หมายเหตุ |
|---|---|---|
| `printer_status()` | สถานะเต็ม: state, %, ชั้น, ETA, อุณหภูมิ, AMS, HMS, wifi | + `pending_action` → HUD panel |
| `printer_control(action)` | `pause` / `resume` / `stop` / `light_on` / `light_off` / `speed` | **`stop` = confirm 2 ขั้นบังคับ** (pattern `send_email`/`_pending_send`) |
| `printer_camera(question="")` | ดึงเฟรม → เซฟลงโฟลเดอร์ที่อนุญาต → ป้อน **`analyze_image()` ที่มีอยู่แล้ว** | "จาร์วิส ดูเครื่องพิมพ์ให้หน่อย" |
| `slice_model(path, material="", quality="")` | เรียก Bambu Studio CLI ใน temp dir → คืน เวลาพิมพ์/น้ำหนักไส้/path ไฟล์ `.gcode.3mf` | **ไม่พิมพ์** แค่สไลซ์+รายงาน |
| `print_model(path_or_ref, confirm=False)` | อัปโหลด FTPS → `print.project_file` | **confirm 2 ขั้นบังคับ** (เปลืองไส้+เวลา) |
| `printer_filaments()` | อ่าน AMS: ช่องไหนมีอะไร สีอะไร เหลือเท่าไร ความชื้น | ให้ จาร์วิส เลือกไส้ให้เองได้ |

→ chat tools: 29 → ~35 · **ระวัง quota Gemini** (tool list ยาวขึ้น) — พิจารณารวมบางตัวเข้าด้วยกัน

**dep ใหม่:** `bambulabs-api` (หรือ `paho-mqtt` + เขียนเอง ถ้า lib ไม่รองรับรุ่นที่ซื้อ)

---

## 4. Watcher เชิงรุก — ต่อกับ `tools/watchers.py` + `notify` (Tier 1 #3)
subscribe MQTT ค้างไว้ใน scheduler thread → event → `notify.push()` → **จาร์วิส พูดเอง**

| เหตุการณ์ | ตรวจจาก |
|---|---|
| พิมพ์เสร็จ | `gcode_state` → `FINISH` |
| ล้มเหลว | `gcode_state` → `FAILED` + `fail_reason` |
| error ใหม่ | `hms[]` มีรหัสเพิ่ม → ดึงคำอธิบายจาก wiki ด้วย `read_url()` |
| ไส้จะหมด | `tray_weight` ต่ำกว่าเกณฑ์ |
| AMS ชื้น | `ams.ams[].humidity` สูง |
| ใกล้เสร็จ | `mc_remaining_time` < 5 นาที |
| หยุดค้างผิดปกติ | `gcode_state` = PAUSED นานเกิน N นาที |
| ถึงรอบบำรุงรักษา | `maintain` |

---

## 5. HUD panel (`static/js/printer.js` + `css/printer.css`)
progress bar + % + ชั้นที่/ทั้งหมด + ETA นับถอยหลัง + กราฟอุณหภูมิ (หัวฉีด/ฐาน/ห้อง) +
ช่อง AMS พร้อม **สีไส้จริงจาก `tray_color`** + ภาพจากกล้อง + สถานะ/HMS
→ ทุกค่าจาก MQTT จริง ตรงกฎ **"ห้าม UI ข้อมูลปลอม"**

---

## 6. Steps (ทีละ step)
1. **เช็คข้อมูลใหม่ทั้งหมด** (ดูหัวข้อ ⚠️ ด้านบน) + ติดตั้ง `bambulabs-api` + ต่อ MQTT ได้จริง → พิมพ์ status ดิบออกมาดู
2. `printer_status()` + `printer_filaments()` (read-only ล้วน ปลอดภัยสุด) + wire + เทส
3. HUD panel — progress/อุณหภูมิ/AMS
4. `printer_control()` + confirm-gate สำหรับ `stop`
5. `printer_camera()` → ต่อกับ `analyze_image()`
6. `slice_model()` — Bambu Studio CLI ใน temp dir + cleanup + parse เวลา/น้ำหนัก
7. `print_model()` — FTPS upload + `print.project_file` + confirm 2 ขั้น
8. watcher เชิงรุก + notify
9. docs (`CLAUDE.md` section + tree) + เทสจริงกับเครื่อง → deploy

---

## 7. ข้อจำกัดที่ต้องบอกผู้ใช้ตั้งแต่ต้น
- **สไลซ์ต้องมี Bambu Studio ติดตั้ง** → บน Pi (Phase 2) ทำไม่ได้ ต้องให้เครื่องคอมสไลซ์
- **แก้งานพิมพ์ที่พังไม่ได้** — บอกได้ว่าเห็นอะไรผิดปกติ แต่ปัญหาการยึดเกาะ/support ผู้ใช้ต้องจัดการ
- **ออกแบบโมเดลให้ไม่ได้** — ต้องมี STL/STEP/3MF มาให้
- **Bambu อาจล็อกเพิ่มในอนาคต** (เคยทำมาแล้ว)
- **TPU/ไส้ยืดหยุ่นใส่ AMS ไม่ได้** → ต้องแขวนม้วนข้างเครื่องเอง จาร์วิส เลือกให้อัตโนมัติไม่ได้
- **ห้องพิมพ์ไม่มีฮีตเตอร์** (P2S) → PPS-CF / PEEK ทำไม่ได้ ไม่ว่าจะสั่งยังไง
- ~~A1 กล้องช้า~~ **ไม่เกี่ยวแล้ว** — P2S กล้อง 1080p@30fps ฟีเจอร์ "ให้ จาร์วิส ดูงานพิมพ์" ได้ผลเต็มที่

## 8. คำแนะนำเชิงเลือกซื้อ — **ตัดสินใจแล้ว: P2S Combo**
- ✅ **P2S Combo (เลือกแล้ว)** — กล้อง 1080p@30fps + AI spaghetti detection + AMS 2 Pro (อบไส้ + RFID + วัดความชื้น)
  + **Developer Mode ติดมาจากโรงงาน** + ไม่ต้องหา microSD → ได้ทุกฟีเจอร์ในแผนนี้เต็มรูปแบบ
  ⚠️ แลกมาด้วยงานเขียนโค้ดเพิ่มใน §1.7 (FTPS 3 กับดัก + กล้อง RTSPS + อาจต้องเขียน MQTT เอง)
- X1-Carbon — เทียบเท่า + LIDAR + ส่ง status เต็มทุกรอบ (P-series ส่งเฉพาะค่าที่เปลี่ยน ต้อง cache เอง)
- P1S / A1 — ครบเหมือนกัน แต่กล้องด้อยกว่าชัดเจน

---

## Sources (ตรวจ ก.ย. 2026)
- OpenBambuAPI — MQTT commands & status fields: https://github.com/Doridian/OpenBambuAPI/blob/main/mqtt.md
- bambulabs_api — Printer class API docs: https://bambutools.github.io/bambulabs_api/api/printer.html
- Bambu Studio — Command Line Usage: https://github.com/bambulab/BambuStudio/wiki/Command-Line-Usage
- Printago — Bambu Studio CLI Reference: https://printago.io/blog/bambu-studio-cli-reference
- bambu-mcp (FTPS 990 / Developer Mode): https://github.com/schwarztim/bambu-mcp
- SimplyPrint — LAN-only & Developer Mode: https://help.simplyprint.io/en/article/bambu-lab-lan-only-mode-and-developer-mode-how-to-enable-xa0hch/
- SimplyPrint — LAN-only vs Bambu Cloud: https://help.simplyprint.io/en/article/bambu-lab-integration-lan-only-vs-bambu-cloud-2eof1u/
- Hackaday — Authorization Control System: https://hackaday.com/2025/01/17/new-bambu-lab-firmware-update-adds-mandatory-authorization-control-system/
- Tom's Hardware — Security update removes OrcaSlicer access: https://www.tomshardware.com/3d-printing/bambu-lab-security-update-will-remove-orcaslicers-access
- OctoEverywhere — Bambu P1/A1 webcam frame rate: https://blog.octoeverywhere.com/full-frame-rate-webcam-streaming-for-bambu-lab-3d-printers/
- Bambu Lab HMS code wiki: https://wiki.bambulab.com/en/hms/home

**เพิ่มเติมเฉพาะ P2S (ตรวจ ก.ย. 2026)**
- Bambu Lab — P2S technical specifications: https://bambulab.com/en/p2s/specs
- Additive-X — P2S Combo review (สเปก/AMS 2 Pro/ห้องไม่มีฮีตเตอร์/TPU): https://www.additive-x.com/blog/bambu-lab-p2s-combo-review
- Tom's Hardware — P2S review: https://www.tomshardware.com/3d-printing/bambu-lab-p2s-review
- SimplyPrint — P2S setup guide: https://simplyprint.io/setup-guide/bambu-lab/p2s
- BambuLab-P2S-Automation (FTPS SNI / session reuse / JSON whitespace + RTSPS→go2rtc): https://github.com/sowmiksudo/BambuLab-P2S-Automation
- ha-bambulab issue #1627 — P2S camera unreliable (wontfix, workaround go2rtc): https://github.com/greghesp/ha-bambulab/issues/1627
- BambuStudio issue #9198 — P2S file-limit bypass เมื่ออัปผ่าน FTP: https://github.com/bambulab/BambuStudio/issues/9198
- synman/bambu-go2rtc — mjpeg/frame endpoint สำหรับกล้อง Bambu: https://github.com/synman/bambu-go2rtc
