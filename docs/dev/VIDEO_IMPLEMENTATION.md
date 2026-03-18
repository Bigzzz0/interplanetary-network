# 🎥 Video & ML Implementation Guide

## Interplanetary Network - Video/Audio Enhancement

เอกสารนี้อธิบายการอัปเกรดระบบจาก 2D Telemetry เป็น **วิดีโอจริง** พร้อม **ML-based Frame Interpolation**

---

## 📋 สารบัญ

1. [ภาพรวมการเปลี่ยนแปลง](#ภาพรวมการเปลี่ยนแปลง)
2. [การติดตั้ง](#การติดตั้ง)
3. [การใช้งาน](#การใช้งาน)
4. [สถาปัตยกรรม ML](#สถาปัตยกรรม-ml)
5. [การปรับแต่ง](#การปรับแต่ง)
6. [การแก้ปัญหา](#การแก้ปัญหา)

---

## 🚀 ภาพรวมการเปลี่ยนแปลง

### ของเดิม (Telemetry)
- ส่งข้อมูลพิกัด X, Y, Battery, Temperature
- Edge Server ใช้ Linear Extrapolation
- Client แสดงผลเป็นรูปวาด Rover ง่ายๆ

### ของใหม่ (Video + ML)
- ส่งวิดีโอจริงจาก Webcam หรือไฟล์วิดีโอ (MJPEG encoding)
- Edge Server ใช้ **RAFT Optical Flow** + **Frame Warping**
- Client แสดงผลวิดีโอจริง พร้อม Quality Metrics (PSNR, SSIM)

---

## 📦 การติดตั้ง

### 1. ติดตั้ง Dependencies

```bash
# จาก project root directory
pip install -r requirements.txt
```

### 2. Dependencies ใหม่ที่สำคัญ

| Package | วัตถุประสงค์ |
|---------|-------------|
| `opencv-python` | จับภาพวิดีโอและ encode/decode MJPEG |
| `opencv-contrib-python` | Optical flow algorithms |
| `torch`, `torchvision` | ML framework สำหรับ RAFT |
| `av` (PyAV) | Video encoding/decoding |
| `pillow` | Image processing |
| `einops` | Tensor operations สำหรับ RAFT |

### 3. ข้อกำหนดระบบ

| Component | ขั้นต่ำ | แนะนำ |
|-----------|--------|--------|
| **CPU** | 4 cores | 8+ cores |
| **RAM** | 8 GB | 16 GB |
| **GPU** | ไม่จำเป็น | NVIDIA GTX 1060+ (สำหรับ RAFT) |
| **Python** | 3.10+ | 3.11+ |

---

## 🎬 การใช้งาน

### วิธีที่ 1: ใช้วิดีโอจาก Webcam

```bash
# Terminal 1 - Sender (Video from Webcam)
cd sender
python main_video.py
```

### วิธีที่ 2: ใช้ไฟล์วิดีโอที่มีอยู่

```bash
# ใช้ไฟล์วิดีโอจาก dataset folder
cd sender
python main_video.py ../dataset/573527995_24880053378360210_5058579176015171104_n.mp4
```

### วิธีที่ 3: ใช้ Test Pattern (ไม่ต้องมี camera)

```bash
# จะสร้าง test pattern อัตโนมัติถ้าไม่มี camera
cd sender
python main_video.py
```

### เริ่มระบบทั้งหมด (4 Components)

```bash
# Terminal 1 - Sender
cd sender
python main_video.py

# Terminal 2 - Network Simulator
cd network_simulator
python main.py

# Terminal 3 - Edge Server (ML Version)
cd edge_server
python main_ml.py

# Terminal 4 - Client
cd client
python main.py
```

### เปิด Browser

```
http://localhost:8004
```

---

## 🧠 สถาปัตยกรรม ML

### RAFT (Real-time Adaptive Flow Tracker)

**หลักการ:**
1. รับเฟรมถัดไป 2 เฟรม (Frame A, Frame B)
2. คำนวณ Optical Flow เพื่อหา vector การเคลื่อนไหวของแต่ละ pixel
3. ใช้ Flow Warping เพื่อสร้างเฟรมกลาง

**สมการ:**
```
Flow(A→B) = [dx, dy] สำหรับแต่ละ pixel
Intermediate(t) = Warp(A, t * Flow) โดยที่ t ∈ [0, 1]
```

### Frame Interpolation Pipeline

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Frame N    │────▶│ RAFT Optical │────▶│ Flow Field  │
│  (640x480)  │     │    Flow      │     │  (640x480x2)│
└─────────────┘     └──────────────┘     └─────────────┘
                                              │
┌─────────────┐     ┌──────────────┐         │
│  Frame N+1  │◀────│ Frame Warping│◀────────┘
└─────────────┘     └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ Blended Frame│
                    │  (Synthetic) │
                    └──────────────┘
```

### Quality Metrics

| Metric | คำอธิบาย | ช่วงที่ดี |
|--------|---------|----------|
| **PSNR** | Peak Signal-to-Noise Ratio | > 35 dB |
| **SSIM** | Structural Similarity Index | > 0.95 |
| **Frame Match** | Percentage of consistent motion | > 90% |

---

## ⚙️ การปรับแต่ง

### Network Simulator Settings

```bash
# เปลี่ยน delay เป็น 5 วินาที
curl -X POST "http://localhost:8002/config?base_delay_ms=5000"

# เพิ่ม packet loss เป็น 5%
curl -X POST "http://localhost:8002/config?packet_loss_rate=0.05"
```

### Edge Server ML Settings

```python
# ใน edge_server/main_ml.py

config = PredictorConfig(
    interpolation_frames=2,      # จำนวนเฟรมที่สร้างระหว่าง 2 เฟรมจริง
    confidence_threshold=0.7,    # Threshold สำหรับ confidence
    use_ml_model=True,           # เปิด/ปิด ML model
    model_path="models/raft-things.pth"  # Path to pre-trained weights
)
```

### Sender Settings

```python
# ใน sender/main_video.py

FRAME_WIDTH = 640      # ความกว้างวิดีโอ
FRAME_HEIGHT = 480     # ความสูงวิดีโอ
FPS = 30               # เฟรมต่อวินาที
KEYFRAME_INTERVAL = 30 # ลงลายเซ็นทุก 30 เฟรม
```

---

## 🔧 การแก้ปัญหา

### ปัญหา: PyTorch ไม่ติดตั้ง

```
⚠️ PyTorch not available: No module named 'torch'
```

**แก้ไข:**
```bash
pip install torch torchvision
```

### ปัญหา: RAFT Model ไม่พบ

```
⚠️ RAFT module not found. Install from: https://github.com/princeton-vl/RAFT
```

**แก้ไข:**
```bash
# Install RAFT จาก source
git clone https://github.com/princeton-vl/RAFT.git
cd RAFT
pip install -e .
```

หรือใช้ OpenCV fallback (อัตโนมัติ):
```python
# ระบบจะเปลี่ยนไปใช้ OpenCV Optical Flow โดยอัตโนมัติ
```

### ปัญหา: Camera ไม่ทำงาน

```
📷 Camera initialized failed
```

**แก้ไข:**
- ตรวจสอบว่า camera ไม่ถูกใช้โดยโปรแกรมอื่น
- ลองเปลี่ยน camera index: `python main_video.py 1` (ใช้ camera ที่ 2)
- ใช้ test pattern แทน (ระบบจะสร้างอัตโนมัติ)

### ปัญหา: วิดีโอกระตุก

**แก้ไข:**
1. ลด resolution: แก้ `FRAME_WIDTH = 320`, `FRAME_HEIGHT = 240`
2. ลด FPS: แก้ `FPS = 15`
3. ปิด ML model: แก้ `use_ml_model = False` ใน Edge Server

---

## 📊 การประเมินผล

### Metrics ที่ควรเก็บ

1. **FPS Comparison**
   - Baseline (delayed): ~0.3-1 FPS (ที่ delay 3000ms)
   - Predicted (ML): ~30 FPS

2. **Latency Reduction**
   - Baseline: 3000ms (ตาม configured delay)
   - Predicted: ~33ms (1/30 FPS)
   - **Improvement: ~97%**

3. **Quality Metrics**
   - PSNR: 35-45 dB (ดี)
   - SSIM: 0.95-0.99 (ดีมาก)

### การทดสอบ

```bash
# รัน demo เป็นเวลา 1 นาที
# เปิด http://localhost:8004
# คลิก "Start Comparison Demo"
# เลือก delay 3000ms
# รอ 1 นาที และบันทึก metrics จาก UI
```

---

## 📁 โครงสร้างไฟล์ใหม่

```
interplanetary-network/
├── requirements.txt              # อัปเดตแล้ว
├── VIDEO_IMPLEMENTATION.md       # เอกสารนี้
├── sender/
│   ├── main.py                   # ของเดิม (Telemetry)
│   └── main_video.py             # ใหม่ (Video)
├── edge_server/
│   ├── main.py                   # ของเดิม (Linear)
│   └── main_ml.py                # ใหม่ (RAFT/ML)
├── client/
│   ├── app.js                    # ของเดิม (Telemetry UI)
│   └── app_video.js              # ใหม่ (Video UI)
└── network_simulator/
    └── main.py                   # เหมือนเดิม
```

---

## 🎯 แผนการพัฒนาต่อ

### Phase 1: พื้นฐาน (เสร็จแล้ว)
- ✅ Video capture และ MJPEG encoding
- ✅ ML-based optical flow (RAFT/OpenCV)
- ✅ Frame interpolation และ warping
- ✅ Quality metrics (PSNR, SSIM)

### Phase 2: ขั้นสูง (แนะนำ)
- [ ] DAIN (Depth-Aware Video Frame Interpolation)
- [ ] Audio stream พร้อม synchronization
- [ ] Adaptive bitrate ตาม network condition
- [ ] GPU acceleration สำหรับ ML inference

### Phase 3: การประเมินผล
- [ ] User study framework
- [ ] Automated testing script
- [ ] Report template และ slides

---

## 📚 อ้างอิง

1. **RAFT Paper:** Teed & Deng, "RAFT: Recurrent All-Pairs Field Transforms for Optical Flow", ECCV 2020
2. **DAIN Paper:** Bao et al., "Depth-Aware Video Frame Interpolation", CVPR 2019
3. **OpenCV Optical Flow:** https://docs.opencv.org/master/db/d7f/tutorial_js_lucas_kanade.html
4. **PyTorch:** https://pytorch.org/

---

## 👥 การสนับสนุน

หากพบปัญหาหรือมีคำถาม:
1. ตรวจสอบ log ของแต่ละ component
2. ลองใช้ test mode (ไม่มี camera) ก่อน
3. ตรวจสอบว่า dependencies ติดตั้งครบ

**Happy Coding! 🚀**
