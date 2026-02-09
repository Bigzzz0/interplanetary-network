# implementation_plan.md

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

*End of implementation_plan.md*

