# architecture\_spec.md

**Project Title:** Interplanetary-Style Low-Latency Multi-Sensory Network (Undergrad Demo)

**Course:** Computer Networks (Undergraduate, Computer Science)

**Team:** 5 members

**Duration:** 4 weeks

---

## 1. Project Overview

Build a working undergraduate-level prototype that demonstrates a simplified *latency-masking* inter-node communication system using high-throughput links, edge prediction, and provenance metadata. The goal is an end-to-end proof-of-concept that shows how predictive processing at an edge node can improve perceived latency for multi-sensory streams (video + audio), with clear instrumentation of link performance and provenance verification.

**Scope (constrained for 4 weeks):**

- Simulated network topology (local or cloud hosts emulating Earth, Relay/Edge, Mars).
- One or two real endpoints for capture & playback (webcam & microphone) or prerecorded datasets.
- An edge server that runs a simple predictive model (frame interpolation/prediction using classical/ML methods) and attaches confidence metadata.
- A lightweight provenance signing mechanism (digital signatures using standard libs) and client-side verification.
- Instrumentation: latency, throughput, prediction accuracy, and UI indicators for provenance/confidence.

**Out of scope:** real optical links, neural implants, planetary-scale deployment.

---

## 2. Objectives & Success Criteria

**Functional Objectives:**

- End-to-end pipeline: Sender -> (simulated) network -> Edge predictor -> Client.
- The predictor improves *perceived latency* vs. raw delayed playback in at least one realistic scenario (validated by logged metrics + short user test).
- Provenance metadata is attached to keyframes and to synthesized frames by the edge, and the client verifies signatures.

**Non-functional Objectives:**

- Clean codebase & documentation suitable for grading.
- Modular design to allow later extension (neural models, real links).

**Success Criteria (measurable):**

- Prototype runs on commodity hardware (one laptop + cloud VM recommended).
- Demonstrated latency masking metric: subjective user test (N≥3 team members) reports higher perceived responsiveness with predictor enabled; and objective metrics show predictor reduced perceived update interval by ≥30% for chosen scenario.
- Provenance signatures validate on client and are displayed correctly.

---

## 3. High-Level Architecture

**Components:**

1. **Sender (Node A — "Mars emulator"):** Captures video/audio (or plays recorded dataset), encodes into keyframes and low-rate updates, signs keyframes with origin key.
2. **Network Simulator / Transport Layer:** Emulates latency & packet loss (e.g., netem on Linux or a simple delay/proxy server). This simulates Earth–Mars characteristics (configurable delay: e.g., 1–20 seconds for demo, can be scaled to minutes in simulation).
3. **Edge Relay / Predictor (Node B — "Lagrange edge"):** Receives keyframes & streams, runs a predictive algorithm (frame interpolation / optical flow / simple ML predictor) to synthesize intermediate frames, annotates synthesized frames with confidence & provenance (edge attestation signature).
4. **Client (Node C — "Earth receiver"):** Verifies provenance, displays reconstructed stream, and visualizes confidence & provenance UI badges.
5. **Control / Orchestration:** Simple REST endpoints or messaging bus (WebSocket / gRPC) for orchestration, health checks, and configuration.
6. **Logging & Instrumentation:** Centralized logging of latency, throughput, prediction error (PSNR/SSIM or perceptual surrogate), and user interactions.

**Data flows:**

- Sender emits signed keyframes + low-bitrate deltas to network simulator.
- Edge receives frames, runs predictor to generate midframes, attaches confidence/provenance, forwards to client.
- Client verifies signatures for origin and edge attestation, displays stream.

**Protocol choices:**

- Transport: **WebRTC** (if real-time browser demo desired) or **gRPC/HTTP2** for simpler control with chunked media blobs. For a controlled demo, a custom WebSocket-based transport with explicit delay injection is acceptable.
- Encoding: H.264/VP8 for baseline keyframes; optionally use MJPEG for simplicity during development. For ML predictor integration, frames can be raw images (PNG/JPEG) exchanged via the transport.
- Signatures: Ed25519 via libs (libsodium / PyNaCl / TweetNaCl) for small key sizes and ease of use.

---

## 4. Component Specs & Interfaces

### Sender (Mars emulator)

- Responsibilities: capture video/audio or read dataset; create signed keyframes; send streaming updates.
- Inputs: camera/mic or recorded dataset.
- Outputs: signed keyframes, metadata (timestamp, frame\_id, signature).
- Technologies: Python (OpenCV, PyNaCl), or Node.js (node-webcam, tweetnacl), or browser-based capture (getUserMedia + WebSocket).

### Network Simulator

- Responsibilities: inject configurable delay, jitter, and packet loss; log transport metrics.
- Technologies: Linux netem for system-level emulation OR a simple proxy server in Node/Python that delays and forwards packets.

### Edge Relay / Predictor

- Responsibilities: receive frames, run predictor, output synthesized frames and confidence, sign attestation.
- Predictor options (ordered by complexity):
  - Optical flow + frame interpolation (classical) — fastest to implement.
  - Simple neural interpolation (e.g., pre-trained DAIN/IFR networks) — higher quality but heavier.
  - Learned residual predictor trained on provided dataset (if time permits).
- Technologies: Python, OpenCV, PyTorch/TensorFlow (if using ML), Flask/FastAPI or gRPC server.
- Security: runs with a local private key in a file (simulate TPM for demo) and signs synthesized frames.

### Client

- Responsibilities: verify signatures (origin & edge), reconstruct playback, show provenance/confidence UI, log subjective feedback.
- UI: Display video player with overlay badges: origin verified, edge attested, confidence bar.
- Technologies: Browser-based UI (HTML/JS) or desktop app (Python + Tkinter / PyQt) depending on team skillset.

### Logging & Metrics

- Collect: send\_time, receive\_time (per hop), predictor\_latency, PSNR/SSIM vs. ground truth (if available), bandwidth usage, user subjective ratings.
- Visualization: simple dashboard using Grafana/Plotly or static CSVs & plots.

---

## 5. Security & Ethics

- Use cryptographic signatures for provenance. Keep private keys safe; for demo, store in encrypted file or environment variable.
- Provide explicit UI indication when content is synthesized and show confidence values.
- Keep user tests limited, informed consent for subjective testing, and record only with permission.

---

## 6. Division of Work (5 members)

- **Member 1 (Project Lead / Sender & Dataset):** Camera capture or dataset preparation; implement sender signing and streaming.
- **Member 2 (Edge & Predictor):** Implement predictor algorithms (start with optical flow), run edge signing.
- **Member 3 (Client & UI):** Build player UI, signature verification, and provenance indicators.
- **Member 4 (Network & Orchestration):** Build network delay simulator, orchestration endpoints, logging pipeline.
- **Member 5 (Testing & Reports):** Design experiments, run metrics collection, user tests, and produce final report & slides.

Work together on devops: the team lead coordinates merges, CI, and final integration.

---

## 7. Deliverables

- Source code (GitHub): sender, edge, client, network simulator.
- README & setup scripts (Docker recommended for reproducibility).
- Short demo video (3–5 min) showing baseline vs. predictor-enabled playback.
- Final report (max 10 pages) with architecture diagrams, evaluation metrics, and reflection.
- Presentation slides (10–12 slides) and demo script.

---

## 8. Evaluation Metrics (for grading)

- Correctness: signature verification works; playback pipeline functional.
- Functionality: predictor runs and improves perceived responsiveness in chosen scenario.
- Code quality & documentation: README, modular code, clear instructions.
- Team coordination & report: clear distribution of work, meeting notes, and final presentation.

---

# implementation\_plan.md

**Project:** Interplanetary-Style Latency-Masking Network — 4-Week Implementation Plan

**Team:** 5 members

**Weekly cadence:** 4 weeks, ending with demo & report. Weekly deliverables and sprint goals below. Use 2–3 short team meetings per week (one planning, one integration), daily async updates in GitHub issues/Slack.

---

## Week 0 (Preparation — before Week 1)

- Team roles confirmed and dev environment standardized (Docker images, repo created with branches).
- Quick spike demos: choose baseline transport (WebSocket vs WebRTC) and predictor approach (optical flow vs pretrained model).
- Create project repo with issue tracker and initial README.

**Deliverable:** Project repo scaffold + development checklist.

---

## Week 1 — Core pipeline & baseline

**Goals:** Implement baseline end-to-end pipeline without prediction.

**Tasks & Assignment:**

- **Member 1 (Sender):** Implement capture script or dataset loader; sign keyframes using Ed25519; push frames to network simulator. (2–3 days)
- **Member 4 (Network):** Implement network simulator (delay/jitter packet proxy) and integrate with sender/client. Document configuration. (2–3 days)
- **Member 3 (Client):** Implement a simple player that receives frames and displays them; implement signature verification for origin key. (3 days)
- **Member 5 (Testing):** Create test plan and initial metrics logger (timestamps, RTT). Start small user tests for baseline. (ongoing)
- **Member 2 (Edge):** Setup edge server skeleton; stub predictor (pass-through) and signing. (2 days)

**Deliverable:** Baseline demo: sender -> delayed network -> client with origin signature verification.

---

## Week 2 — Predictor & Edge integration

**Goals:** Implement predictor on edge and integrate synthesized frames into playback.

**Tasks & Assignment:**

- **Member 2 (Edge):** Implement chosen predictor (optical flow interpolation or simple ML model). Provide API to receive frames and output synthesized frames + confidence. (full week)
- **Member 4 (Network):** Ensure network paths support frame blobs and edge forwarding; add logging hooks. (support)
- **Member 3 (Client):** Update client to accept synthesized frames with edge attestation and display confidence UI. (2–3 days)
- **Member 1 (Sender):** Provide ground-truth recordings for evaluation (if not live capture) and ensure keyframe cadence logic. (support)
- **Member 5 (Testing):** Run initial experiments comparing baseline vs. predictor; compute objective metrics (PSNR/SSIM if ground truth available). Collect subjective feedback. (end of week)

**Deliverable:** Predictor-enabled demo with metrics & logs.

---

## Week 3 — Security, Provenance & UX polish

**Goals:** Implement edge attestation signing, provenance verification, confidence UX, and improve robustness.

**Tasks & Assignment:**

- **Member 4 (Network):** Harden transport & provide configuration toggles for delay scenarios (simulate short/medium/long). (2 days)
- **Member 2 (Edge):** Implement edge signing of synthesized frames and attach metadata (predictor version, confidence, parent keyframe IDs). (2 days)
- **Member 3 (Client):** Show provenance badges, implement fallback UX (display message or freeze when confidence low). Add logging of user interactions. (2–3 days)
- **Member 1 (Sender):** Tune keyframe frequency and signature metadata. (support)
- **Member 5 (Testing):** Plan user study script, IRB checklist (if needed), run 5–10 controlled user tests. (continuous)

**Deliverable:** Security + UX polished demo and user study results draft.

---

## Week 4 — Integration, evaluation & presentation

**Goals:** Final integration, full evaluation, report, and presentation.

**Tasks & Assignment:**

- **Integration & testing (all):** End-to-end smoke tests; fix integration bugs; prepare final demo script (who says what, which toggles to flip). (all)
- **Member 5 (Testing):** Finalize evaluation metrics & generate plots/tables for report. (2 days)
- **Member 1 & 3 (Docs & Slides):** Draft final report (10 pages) and presentation slides (10–12 slides). (3 days)
- **Member 4 (Ops):** Prepare Docker images, deployment scripts, and ensure reproducibility instructions. (2 days)
- **Member 2 (Edge):** Provide model & predictor docs and parameter settings for reproducibility. (support)

**Deliverable:** Final demo, recorded video, final report, slides, and code pushed to main branch.

---

## Communication & DevOps

- **Version control:** GitHub; use feature branches and PRs. One team member reviews/merges PRs (rotate). Protect main branch.
- **CI:** Basic checks (linting, unit tests). Dockerfile(s) to ensure reproducible runs.
- **Documentation:** Use README for quickstart, and docs/ for component guides. Keep a meeting log.

---

## Risk Management & Mitigation

- **Risk:** Predictor is too slow on available hardware. **Mitigation:** Start with classical optical-flow interpolation (fast) and only attempt ML if time permits.
- **Risk:** Integration bugs consume time. **Mitigation:** Keep interfaces simple, define sample messages early, and allocate integration days each sprint.
- **Risk:** User study/IRB delays. **Mitigation:** Keep tests small (team-only or peers) and anonymize results.

---

## Grading & Demo Tips

- Prepare a concise demo script: show baseline (delayed raw playback), then enable predictor and show improved experience; show provenance verification and explain metrics.
- Provide reproducibility notes and a short screencast for graders who cannot run the demo.

---

## Appendix: Quick Technical Choices (recommended stack)

- Languages: Python 3.10+ (OpenCV, PyTorch if needed), JavaScript for client UI.
- Transport: WebSocket (server: FastAPI with WebSocket / Node.js ws) or WebRTC (more complex but real-time). For simplicity, use WebSocket.
- Signing: PyNaCl / libsodium (Ed25519 signatures).
- Containerization: Docker for sender, edge, and client server.
- ML: Pretrained optical flow libraries (e.g., RAFT / OpenCV's calcOpticalFlow) or DAIN-like models if GPU available.

---

*End of combined architecture\_spec.md and implementation\_plan.md*

