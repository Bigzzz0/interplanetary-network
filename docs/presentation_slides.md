# Presentation Slides Outline

**Slide 1: Title Slide**
- Project Title: Interplanetary Latency-Masking Network
- Team Members & Roles
- Course Name

**Slide 2: The Problem**
- The speed of light limits Earth-Mars communication (3 to 22 minutes).
- Traditional protocols freeze or buffer, destroying real-time UX.
- Goal: Create a perception of real-time interaction using "Latency Masking."

**Slide 3: High-Level Architecture**
- Diagram: Sender -> Delay Simulator -> Edge Predictor -> Client
- Explanation of the 4 components.

**Slide 4: The Edge Predictor (ML in the Middle)**
- What it does: Guesses missing frames in real-time.
- Tech Stack: PyTorch, RAFT Optical Flow, DAIN frame interpolation.
- Result: 1 FPS delayed stream becomes a smooth 30 FPS stream.

**Slide 5: Audio & Adaptive Bitrate (ABR)**
- Audio is synced via `sounddevice` and Web Audio API.
- ABR: Network simulator feeds back congestion/delay metrics to the sender.
- Sender automatically degrades MJPEG quality/resolution to ensure packets arrive.

**Slide 6: Security - "Can we trust the video?"**
- Issue: If AI is making up frames, how do we prevent deepfakes?
- Solution: Cryptographic provenance.
- Origin (Sender) signs keyframes with Ed25519.
- Edge signs synthetic frames and includes a "Confidence Score."

**Slide 7: Live Demo (or Pre-recorded Video)**
- Split screen comparison:
  - Left: The raw, jittery, delayed stream.
  - Right: The smooth, ML-predicted stream with trust badges.
- *Show the ABR adjusting resolution when delay is spiked!*

**Slide 8: Objective Results**
- Show Graphs:
  - Latency reduction percentages (e.g., 3000ms perceived latency down to 33ms).
  - SSIM / PSNR quality metrics of the synthesized frames.

**Slide 9: User Study Highlights**
- Quote from user testing.
- Graph of UX scores (Baseline vs Predicted).

**Slide 10: Limitations & Future Work**
- Current predictor struggles with entirely unpredictable, fast camera jerks.
- Future work: Hardware accelerators, full depth-map integration.

**Slide 11: Q&A**
- Link to GitHub Repo
- Contact info
