# Final Report: Interplanetary-Style Low-Latency Multi-Sensory Network

## 1. Abstract
*Provide a 250-word summary of the project, the problem it solves (latency masking over interplanetary distances), the approach (RAFT / DAIN ML interpolation, Ed25519 signing, ABR), and the core findings.*

## 2. Introduction
*Describe the motivations for the project. Explain the fundamental physical limits of interplanetary communication (speed of light) and why edge prediction is a viable workaround for UX.*

## 3. System Architecture
### 3.1 Overview
*Include a high-level block diagram showing the 4 nodes: Sender (Mars), Network Simulator, Edge Server (Lagrange point), and Client (Earth).*

### 3.2 Network Layer
*Discuss how delays and packet drops are simulated and how the Adaptive Bitrate (ABR) feedback loop stabilizes the stream.*

### 3.3 Security and Provenance
*Explain the mathematical basis of Ed25519 signatures. Detail how original frames are signed by the sender, and how synthetic frames are attested to by the edge server.*

## 4. Advanced ML Algorithms
### 4.1 RAFT Optical Flow
*Describe the math and implementation of RAFT for dense optical flow tracking.*

### 4.2 DAIN Frame Interpolation
*Explain how optical flow and depth awareness are combined to warp and blend frames securely.*

## 5. Evaluation & Results
### 5.1 Objective Metrics
*Discuss the quantitative metrics collected during tests:*
- FPS Improvements (Baseline vs Predicted)
- Latency Reduction (ms)
- Interpolation Quality (Average PSNR and SSIM)

### 5.2 Subjective User Study
*Summarize the results of the user tests based on the `user_study_framework.md` data. Include charts showing average UX ratings.*

## 6. Challenges and Limitations
*Discuss integration challenges (e.g., PyTorch initialization latency, asynchronous audio/video synchronization) and edge cases where the predictor fails (e.g., very fast, unpredictable movements).*

## 7. Conclusion & Future Work
*Summarize project success criteria. Suggest future improvements like deep adaptive video compression or full depth-camera hardware integration.*

## 8. References
*List academic papers (e.g., RAFT, DAIN) and software libraries used.*
