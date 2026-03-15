# User Study Framework: Interplanetary Network Evaluation

## Objective
The goal of this user study is to subjectively evaluate the perceived latency and user experience of the interplanetary network simulator, comparing the baseline "Delayed Path" against the "ML-Predicted Path."

## Participant Criteria
- Must be unfamiliar with the predictive algorithm's specific technical workings (to avoid bias).
- Target N = 5 to 10 participants.

## Study Setup
1. **Environment:** A quiet room with a standard laptop/monitor setup.
2. **Network Config:** Set the network simulator to a fixed challenge scenario (e.g., 2000ms delay, 2% packet loss).
3. **Application State:** Launch all four components (`sender`, `network_simulator`, `edge_server`, `client`). The sender should use a live webcam feed of the researcher interacting with the participant (e.g., holding up fingers, moving objects).

## Testing Protocol (15 Minutes)

### Part 1: Introduction (2 mins)
Explain the premise: "You are an operator on Earth communicating with a rover on Mars. The distance causes a significant communication delay. We have two viewing modes for you to evaluate."

### Part 2: Baseline Observation (3 mins)
1. Turn OFF the ML predictor (hide the right canvas or switch to `raft` without interpolation).
2. Ask the participant to interact with the researcher (e.g., "tell me when I raise my right hand").
3. Ask the participant to rate the perceived frustration and lag on a scale of 1-5.

### Part 3: Predicted Observation (3 mins)
1. Turn ON the ML predictor (show the ML-Predicted stream).
2. Repeat the physical interaction tests.
3. Ask the participant to rate the perceived frustration and lag on a scale of 1-5.

### Part 4: Trust and Provenance (2 mins)
1. Point out the "Edge Attested" and "Confidence" badges.
2. Ask if these indicators change how much they trust the smoothed video feed.

## Data Collection Survey
Record the following for each participant:
1. **Baseline UX Score (1=Terrible, 5=Excellent):** ___
2. **Predicted UX Score (1=Terrible, 5=Excellent):** ___
3. **Did the prediction make the interaction easier? (Yes/No/Unsure):** ___
4. **Qualitative feedback on visual artifacts (e.g., "blurriness during fast motion"):** _____________________
5. **Qualitative feedback on UI trust indicators:** _____________________

## Analysis Plan
- Calculate the average increase in UX score.
- Summarize qualitative feedback to identify limitations of the edge predictor algorithm (e.g., does it fail gracefully?).
