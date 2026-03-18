/**
 * Interplanetary Network - Video Comparison Demo
 * Client-side Application Logic (Video/MJPEG Version)
 */

// Configuration
const CONFIG = {
    clientWsUrl: 'ws://localhost:8004/stream',
    networkConfigUrl: 'http://localhost:8002/network/config',
    modelConfigUrl: 'http://localhost:8003/config',
    reconnectInterval: 2000,
    maxLogEntries: 50,
    targetFPS: 30
};

// State
let state = {
    connected: false,
    socket: null,
    baselineFrameCount: 0,
    predictionFrameCount: 0,
    synthFrameCount: 0,
    startTime: null,
    baselineLastFrameTime: 0,
    predictionLastFrameTime: 0,
    baselineImages: [],
    predictionImages: [],
    maxBufferedImages: 60
};

// Audio State
let audioCtx = null;
let audioStartTime = 0;

// DOM Elements
const elements = {
    status: {
        dot: document.querySelector('.status-dot'),
        text: document.querySelector('.status-text'),
        container: document.getElementById('connectionStatus')
    },
    nodes: {
        mars: document.getElementById('marsNode'),
        marsStatus: document.getElementById('marsStatus'),
        network: document.getElementById('networkNode'),
        networkStatus: document.getElementById('networkStatus'),
        edge: document.getElementById('edgeNode'),
        edgeStatus: document.getElementById('edgeStatus'),
        earthStatus: document.getElementById('earthStatus')
    },
    baseline: {
        canvas: document.getElementById('baselineCanvas'),
        ctx: document.getElementById('baselineCanvas').getContext('2d'),
        delayOverlay: document.getElementById('baselineDelay'),
        delayValue: document.getElementById('baselineDelayValue'),
        frameCounter: document.getElementById('baselineFrameId'),
        totalFrames: document.getElementById('baselineFrames'),
        fps: document.getElementById('baselineFps'),
        interval: document.getElementById('baselineInterval')
    },
    prediction: {
        canvas: document.getElementById('predictionCanvas'),
        ctx: document.getElementById('predictionCanvas').getContext('2d'),
        frameTypeBadge: document.getElementById('frameTypeBadge'),
        frameCounter: document.getElementById('predictionFrameId'),
        totalFrames: document.getElementById('predictionFrames'),
        synthFrames: document.getElementById('synthFrames'),
        fps: document.getElementById('predictionFps'),
        confidenceFill: document.getElementById('confidenceFill'),
        confidenceValue: document.getElementById('confidenceValue')
    },
    packets: {
        srcFrameId: document.getElementById('srcFrameId'),
        srcTimestamp: document.getElementById('srcTimestamp'),
        srcPayloadSize: document.getElementById('srcPayloadSize'),
        srcSignature: document.getElementById('srcSignature'),
        srcStatus: document.getElementById('srcStatus'),
        synthFrameId: document.getElementById('synthFrameId'),
        synthBaseFrame: document.getElementById('synthBaseFrame'),
        synthConfidence: document.getElementById('synthConfidence'),
        synthAttestation: document.getElementById('synthAttestation')
    },
    performance: {
        baselineFps: document.getElementById('perfBaselineFps'),
        predictionFps: document.getElementById('perfPredictionFps'),
        fpsImprovement: document.getElementById('fpsImprovement'),
        baselineLatency: document.getElementById('perfBaselineLatency'),
        predictionLatency: document.getElementById('perfPredictionLatency'),
        latencyImprovement: document.getElementById('latencyImprovement'),
        baselineFrames: document.getElementById('perfBaselineFrames'),
        predictionFrames: document.getElementById('perfPredictionFrames'),
        framesImprovement: document.getElementById('framesImprovement'),
        originVerified: document.getElementById('originVerified'),
        edgeAttested: document.getElementById('edgeAttested')
    },
    quality: {
        psnrValue: document.getElementById('psnrValue'),
        psnrBar: document.getElementById('psnrBar'),
        ssimValue: document.getElementById('ssimValue'),
        ssimBar: document.getElementById('ssimBar'),
        matchValue: document.getElementById('matchValue'),
        matchBar: document.getElementById('matchBar')
    },
    graph: {
        canvas: document.getElementById('streamGraph'),
        ctx: document.getElementById('streamGraph')?.getContext('2d'),
        totalOriginal: document.getElementById('totalOriginalFrames'),
        totalPredicted: document.getElementById('totalPredictedFrames'),
        ratio: document.getElementById('predOrigRatio')
    },
    controls: {
        startBtn: document.getElementById('startBtn'),
        stopBtn: document.getElementById('stopBtn'),
        delaySelect: document.getElementById('delaySelect'),
        modelTypeRadios: document.getElementsByName('modelType')
    },
    log: document.getElementById('logContainer')
};

// Graph data
const graphData = {
    originalFrames: [],
    predictedFrames: [],
    maxPoints: 100,
    lastUpdate: Date.now()
};

// Setup Event Listeners
function setupEventListeners() {
    elements.controls.startBtn.addEventListener('click', startDemo);
    elements.controls.stopBtn.addEventListener('click', stopDemo);
    elements.controls.delaySelect.addEventListener('change', updateNetworkDelay);
    
    // Model selection radio buttons
    elements.controls.modelTypeRadios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            if (e.target.checked) {
                updateModelSelection(e.target.value);
            }
        });
    });
}

// Logging
function log(message, type = 'info') {
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    const time = new Date().toLocaleTimeString();
    entry.textContent = `[${time}] ${message}`;

    elements.log.prepend(entry);

    if (elements.log.children.length > CONFIG.maxLogEntries) {
        elements.log.lastElementChild.remove();
    }
}

// WebSocket Connection
function connect() {
    if (state.connected) return;

    log('Connecting to Earth Receiver...', 'info');
    elements.status.dot.className = 'status-dot connecting';
    elements.status.text.textContent = 'Connecting...';

    try {
        state.socket = new WebSocket(CONFIG.clientWsUrl);

        state.socket.onopen = () => {
            state.connected = true;
            state.startTime = Date.now();

            elements.status.dot.className = 'status-dot connected';
            elements.status.text.textContent = 'Connected';
            elements.controls.startBtn.disabled = true;
            elements.controls.stopBtn.disabled = false;
            elements.baseline.delayOverlay.classList.remove('hidden');

            updateNodeStatus('online');
            log('Connected to video stream.', 'success');
        };

        state.socket.onmessage = handleMessage;

        state.socket.onclose = () => {
            state.connected = false;
            elements.status.dot.className = 'status-dot disconnected';
            elements.status.text.textContent = 'Disconnected';
            elements.controls.startBtn.disabled = false;
            elements.controls.stopBtn.disabled = true;

            updateNodeStatus('offline');
            log('Disconnected from server.', 'warning');
        };

        state.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            log('Connection error occurred.', 'error');
        };

    } catch (e) {
        log(`Connection failed: ${e.message}`, 'error');
        elements.status.dot.className = 'status-dot disconnected';
    }
}

function disconnect() {
    if (state.socket) {
        state.socket.close();
        state.socket = null;
    }
}

// Message Handling
function handleMessage(event) {
    try {
        const data = JSON.parse(event.data);

        if (data.type === 'error') {
            log(`Server Error: ${data.message}`, 'error');
            return;
        }

        if (data.type === 'frame') {
            processFrame(data);
        } else if (data.type === 'audio') {
            processAudio(data);
        }

    } catch (e) {
        console.error('Error parsing message:', e);
        log('JSON parse error: ' + e.message, 'error');
    }
}

// Frame Processing
function processFrame(data) {
    try {
        const metadata = data.metadata || {};
        const base64Data = data.data;

        if (!base64Data) {
            console.error('No frame data received');
            return;
        }

        const isSynthesized = metadata.is_synthesized === true;

        try {
            if (isSynthesized) {
                // Render to prediction canvas
                renderVideoFrame(elements.prediction.ctx, base64Data, true);
                updatePredictionStats(metadata, isSynthesized);
                updatePacketCards(metadata, isSynthesized);
            } else {
                // Render to baseline canvas
                if (!elements.baseline.delayOverlay.classList.contains('hidden')) {
                    elements.baseline.delayOverlay.classList.add('hidden');
                }
                renderVideoFrame(elements.baseline.ctx, base64Data, false);
                updateBaselineStats(metadata, data.network_metadata || {});
                updatePacketCards(metadata, isSynthesized);
            }

            updatePerformanceSection();
            if (isSynthesized) {
                updateQualityMetrics(metadata);
            }

            // Update verification status
            if (elements.performance.originVerified) {
                elements.performance.originVerified.textContent = metadata.origin_verified ? 'VALID' : 'PENDING';
                elements.performance.originVerified.className = metadata.origin_verified ? 'verify-value valid' : 'verify-value';
            }
            if (elements.performance.edgeAttested && isSynthesized) {
                elements.performance.edgeAttested.textContent = metadata.edge_signature ? 'SIGNED' : 'PENDING';
                elements.performance.edgeAttested.className = metadata.edge_signature ? 'verify-value signed' : 'verify-value';
            }

            updateComparison();
        } catch (renderError) {
            console.error('Render error:', renderError);
            log('Render error: ' + renderError.message, 'error');
        }

    } catch (e) {
        console.error('processFrame error:', e);
        log('Frame processing error: ' + e.message, 'error');
    }
}

// Audio Processing
function processAudio(data) {
    if (!audioCtx) return;
    try {
        const base64Data = data.data;
        if (!base64Data) return;

        // Decode base64 to Float32Array
        const binaryString = window.atob(base64Data);
        const len = binaryString.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        const floatArray = new Float32Array(bytes.buffer);

        // Create AudioBuffer
        const buffer = audioCtx.createBuffer(1, floatArray.length, 16000);
        buffer.copyToChannel(floatArray, 0);

        // Play
        const source = audioCtx.createBufferSource();
        source.buffer = buffer;
        source.connect(audioCtx.destination);
        
        // Schedule playback smoothly
        if (audioStartTime < audioCtx.currentTime) {
            audioStartTime = audioCtx.currentTime;
        }
        source.start(audioStartTime);
        audioStartTime += buffer.duration;
    } catch (e) {
        console.error('Audio processing error', e);
    }
}

/**
 * Render MJPEG frame from base64 to canvas
 */
function renderVideoFrame(ctx, base64Data, isPredictionCanvas) {
    const canvas = ctx.canvas;
    const img = new Image();
    
    img.onload = () => {
        // Clear canvas
        ctx.fillStyle = '#1a1a2e';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        // Calculate aspect ratio and center the image
        const scale = Math.min(
            canvas.width / img.width,
            canvas.height / img.height
        );
        const x = (canvas.width - img.width * scale) / 2;
        const y = (canvas.height - img.height * scale) / 2;
        
        // Draw the frame
        ctx.drawImage(img, x, y, img.width * scale, img.height * scale);
        
        // Draw overlay info
        drawOverlayInfo(ctx, canvas.width, canvas.height, isPredictionCanvas);
    };
    
    img.onerror = (e) => {
        console.error('Failed to decode frame image', e);
        log('Error rendering image frame (corrupt base64/JPEG)', 'error');
    };
    
    // Load image from base64
    img.src = 'data:image/jpeg;base64,' + base64Data;
}

/**
 * Draw overlay information on canvas
 */
function drawOverlayInfo(ctx, width, height, isPredictionCanvas) {
    // Draw semi-transparent info bar at top
    ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
    ctx.fillRect(0, 0, width, 30);
    
    // Draw FPS and frame info
    ctx.fillStyle = '#00ff88';
    ctx.font = '12px "Courier New", monospace';
    ctx.textAlign = 'left';
    ctx.fillText(`LIVE`, 10, 20);
    
    // Draw mode indicator
    ctx.font = 'bold 16px Arial';
    ctx.textAlign = 'center';
    if (isPredictionCanvas) {
        ctx.fillStyle = '#00ff88';
        ctx.fillText("SMOOTHED BY PREDICTION", width / 2, 22);
    } else {
        ctx.fillStyle = '#ff3333';
        ctx.fillText("⚠️ LAG SIMULATION", width / 2, 22);
    }
    
    // Draw timestamp
    const now = new Date().toLocaleTimeString();
    ctx.fillStyle = '#ffffff';
    ctx.textAlign = 'right';
    ctx.fillText(now, width - 10, 20);
}

// Stats Updates
function updateBaselineStats(metadata, networkMetadata) {
    state.baselineFrameCount++;
    const now = Date.now();
    const timeDiff = now - state.baselineLastFrameTime;

    if (state.baselineLastFrameTime > 0 && timeDiff > 0) {
        const fps = 1000 / timeDiff;
        elements.baseline.fps.textContent = fps.toFixed(1) + " FPS";
        elements.baseline.interval.textContent = timeDiff.toFixed(0) + "ms";
    }

    state.baselineLastFrameTime = now;

    elements.baseline.totalFrames.textContent = state.baselineFrameCount;
    elements.baseline.frameCounter.textContent = metadata.frame_id || '-';

    if (networkMetadata && networkMetadata.simulated_delay_ms) {
        const simulatedDelay = networkMetadata.simulated_delay_ms;
        elements.baseline.delayValue.textContent = `Simulated: ${simulatedDelay.toFixed(0)}ms delay`;
    }
}

function updatePredictionStats(metadata, isSynthesized) {
    state.predictionFrameCount++;
    if (isSynthesized) state.synthFrameCount++;

    const now = Date.now();
    const timeDiff = now - state.predictionLastFrameTime;

    if (state.predictionLastFrameTime > 0) {
        const fps = 1000 / timeDiff;
        elements.prediction.fps.textContent = fps.toFixed(1) + " FPS";
    }

    state.predictionLastFrameTime = now;

    elements.prediction.totalFrames.textContent = state.predictionFrameCount;
    elements.prediction.synthFrames.textContent = state.synthFrameCount;
    elements.prediction.frameCounter.textContent = metadata.frame_id || '-';

    // Badge Update
    // Check if the edge server provided a specific flag for actual synthesis status (due to buffer routing)
    const trulySynthesized = metadata.is_actually_synth !== undefined ? metadata.is_actually_synth : isSynthesized;
    
    if (trulySynthesized) {
        elements.prediction.frameTypeBadge.className = 'frame-type-badge synthesized';
        elements.prediction.frameTypeBadge.innerHTML = '<span class="badge-icon">⚡</span> ML SYNTH';
    } else {
        elements.prediction.frameTypeBadge.className = 'frame-type-badge';
        elements.prediction.frameTypeBadge.innerHTML = '<span class="badge-icon">📷</span> ORIGINAL';
    }

    // Confidence Bar
    const confidence = metadata.confidence || 1.0;
    const confPercent = Math.round(confidence * 100);
    elements.prediction.confidenceValue.textContent = `${confPercent}%`;
    elements.prediction.confidenceFill.style.width = `${confPercent}%`;

    if (confidence < 0.5) {
        elements.prediction.confidenceFill.className = 'confidence-fill very-low';
    } else if (confidence < 0.8) {
        elements.prediction.confidenceFill.className = 'confidence-fill low';
    } else {
        elements.prediction.confidenceFill.className = 'confidence-fill';
    }
}

function updateComparison() {
    // Handled by updatePerformanceSection()
}

// Network Configuration
async function updateNetworkDelay() {
    const delay = parseInt(elements.controls.delaySelect.value);
    log(`Setting network delay to ${delay}ms...`, 'info');

    try {
        const response = await fetch(`${CONFIG.networkConfigUrl}?base_delay_ms=${delay}`, {
            method: 'POST'
        });

        if (response.ok) {
            log(`Network delay updated to ${delay}ms`, 'success');
        } else {
            log('Failed to update network delay', 'error');
        }
    } catch (e) {
        log(`Network config error: ${e.message}`, 'error');
    }
}

async function updateModelSelection(modelType) {
    log(`Switching to ${modelType.toUpperCase()} synthesis model...`, 'info');

    try {
        const response = await fetch(`${CONFIG.modelConfigUrl}?model_type=${modelType}`, {
            method: 'POST'
        });

        if (response.ok) {
            log(`Successfully switched to ${modelType.toUpperCase()}`, 'success');
        } else {
            log(`Failed to switch to ${modelType.toUpperCase()} model`, 'error');
        }
    } catch (e) {
        log(`Model config error: ${e.message}`, 'error');
    }
}

// UI Helpers
function updateNodeStatus(status) {
    if (status === 'online') {
        elements.nodes.marsStatus.className = 'node-status online';
        elements.nodes.marsStatus.textContent = 'Active';
        elements.nodes.networkStatus.className = 'node-status online';
        elements.nodes.networkStatus.textContent = 'Active';
        elements.nodes.edgeStatus.className = 'node-status online';
        elements.nodes.edgeStatus.textContent = 'Active';

        elements.nodes.mars.classList.add('active');
        elements.nodes.network.classList.add('active');
        elements.nodes.edge.classList.add('active');
        elements.nodes.earthStatus.className = 'node-status online';
    } else {
        document.querySelectorAll('.node-status').forEach(el => {
            if (el.id !== 'earthStatus') {
                el.className = 'node-status';
                el.textContent = 'Offline';
            }
        });
        document.querySelectorAll('.node-box').forEach(el => el.classList.remove('active'));
    }
}

// Main Controls
function startDemo() {
    if (!audioCtx) {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        audioCtx = new AudioContext();
    }
    if (audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
    audioStartTime = 0;
    connect();
}

function stopDemo() {
    disconnect();
    state.baselineFrameCount = 0;
    state.predictionFrameCount = 0;
    state.synthFrameCount = 0;
    initializeCanvases();
}

// Initialize canvases with placeholder
function initializeCanvases() {
    const canvases = [elements.baseline.ctx, elements.prediction.ctx];

    canvases.forEach((ctx, index) => {
        const canvas = ctx.canvas;

        // Clear canvas
        ctx.fillStyle = '#1a1a2e';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Draw grid pattern
        ctx.strokeStyle = '#2a2a4e';
        ctx.lineWidth = 1;
        for (let x = 0; x < canvas.width; x += 40) {
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, canvas.height);
            ctx.stroke();
        }
        for (let y = 0; y < canvas.height; y += 40) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(canvas.width, y);
            ctx.stroke();
        }

        // Draw center text
        ctx.fillStyle = '#4a4a6e';
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(index === 0 ? 'Baseline Stream (Delayed)' : 'ML-Predicted Stream', canvas.width / 2, canvas.height / 2 - 10);
        ctx.fillText('Waiting for video...', canvas.width / 2, canvas.height / 2 + 15);
    });

    log('Canvases initialized', 'info');
}

// Update Frame Packet Cards
function updatePacketCards(metadata, isSynthesized) {
    if (!isSynthesized) {
        if (elements.packets.srcFrameId) {
            elements.packets.srcFrameId.textContent = metadata.frame_id || 'frame_0';
        }
        if (elements.packets.srcTimestamp) {
            elements.packets.srcTimestamp.textContent = new Date().toLocaleTimeString();
        }
        if (elements.packets.srcPayloadSize) {
            const size = metadata.frame_size ? metadata.frame_size : '--';
            elements.packets.srcPayloadSize.textContent = size + ' bytes';
        }
        if (elements.packets.srcSignature && metadata.signature) {
            elements.packets.srcSignature.textContent = metadata.signature.substring(0, 16) + '...';
        }
        if (elements.packets.srcStatus) {
            elements.packets.srcStatus.textContent = metadata.origin_verified ? '🔒 Verified' : '⚠️ Unverified';
            elements.packets.srcStatus.className = metadata.origin_verified ? 'packet-value status-verified' : 'packet-value';
        }
    } else {
        if (elements.packets.synthFrameId) {
            elements.packets.synthFrameId.textContent = metadata.frame_id || 'synth_0';
        }
        if (elements.packets.synthBaseFrame && metadata.parent_frame_ids) {
            elements.packets.synthBaseFrame.textContent = metadata.parent_frame_ids.join(', ') || 'frame_0';
        }
        if (elements.packets.synthConfidence) {
            const conf = metadata.confidence ? (metadata.confidence * 100).toFixed(1) : '95.0';
            elements.packets.synthConfidence.textContent = conf + '%';
        }
        if (elements.packets.synthAttestation && metadata.edge_signature) {
            elements.packets.synthAttestation.textContent = metadata.edge_signature.substring(0, 16) + '...';
        }
    }
}

// Update Enhanced Performance Section
function updatePerformanceSection() {
    const baselineFps = state.baselineFrameCount > 0 ?
        (1000 / Math.max(1, (Date.now() - state.startTime) / state.baselineFrameCount)).toFixed(1) : '0.0';
    const predictionFps = state.predictionFrameCount > 0 ?
        (1000 / Math.max(1, (Date.now() - state.startTime) / state.predictionFrameCount)).toFixed(1) : '0.0';

    if (elements.performance.baselineFps) {
        elements.performance.baselineFps.textContent = baselineFps;
    }
    if (elements.performance.predictionFps) {
        elements.performance.predictionFps.textContent = predictionFps;
    }

    const bFps = parseFloat(baselineFps) || 0.1;
    const pFps = parseFloat(predictionFps) || 0;
    const fpsRatio = (pFps / bFps).toFixed(0);
    if (elements.performance.fpsImprovement) {
        elements.performance.fpsImprovement.textContent = fpsRatio + 'x';
    }

    const baselineLatency = state.baselineFrameCount > 0 ?
        ((Date.now() - state.startTime) / state.baselineFrameCount).toFixed(0) : '3000';
    const predictionLatency = state.predictionFrameCount > 0 ?
        ((Date.now() - state.startTime) / state.predictionFrameCount).toFixed(0) : '33';

    if (elements.performance.baselineLatency) {
        elements.performance.baselineLatency.textContent = baselineLatency;
    }
    if (elements.performance.predictionLatency) {
        elements.performance.predictionLatency.textContent = predictionLatency;
    }

    const bLat = parseInt(baselineLatency) || 3000;
    const pLat = parseInt(predictionLatency) || 33;
    const latencyReduction = Math.round((1 - pLat / bLat) * 100);
    if (elements.performance.latencyImprovement) {
        elements.performance.latencyImprovement.textContent = latencyReduction + '%';
    }

    if (elements.performance.baselineFrames) {
        elements.performance.baselineFrames.textContent = state.baselineFrameCount;
    }
    if (elements.performance.predictionFrames) {
        elements.performance.predictionFrames.textContent = state.predictionFrameCount;
    }

    const framesRatio = state.baselineFrameCount > 0 ?
        (state.predictionFrameCount / state.baselineFrameCount).toFixed(1) : '0';
    if (elements.performance.framesImprovement) {
        elements.performance.framesImprovement.textContent = framesRatio + 'x';
    }
}

// Update Quality Metrics
function updateQualityMetrics(metadata) {
    const psnr = metadata?.psnr ?? null;
    const ssim = metadata?.ssim ?? null;
    const frameMatch = metadata?.frame_match ?? null;

    if (psnr !== null) {
        if (elements.quality.psnrValue) {
            elements.quality.psnrValue.textContent = psnr.toFixed(1);
        }
        if (elements.quality.psnrBar) {
            elements.quality.psnrBar.style.width = (psnr / 50 * 100) + '%';
        }
    }

    if (ssim !== null) {
        if (elements.quality.ssimValue) {
            elements.quality.ssimValue.textContent = ssim.toFixed(2);
        }
        if (elements.quality.ssimBar) {
            elements.quality.ssimBar.style.width = (ssim * 100) + '%';
        }
    }

    if (frameMatch !== null) {
        if (elements.quality.matchValue) {
            elements.quality.matchValue.textContent = frameMatch.toFixed(1) + '%';
        }
        if (elements.quality.matchBar) {
            elements.quality.matchBar.style.width = frameMatch + '%';
        }
    }
}

// Update Stream Stats
function updateStreamStats() {
    if (elements.graph.totalOriginal) {
        elements.graph.totalOriginal.textContent = state.baselineFrameCount;
    }
    if (elements.graph.totalPredicted) {
        elements.graph.totalPredicted.textContent = state.synthFrameCount;
    }
    if (elements.graph.ratio) {
        elements.graph.ratio.textContent = state.synthFrameCount + ':' + state.baselineFrameCount;
    }
}

// Draw Live Stream Graph
function drawStreamGraph() {
    const ctx = elements.graph.ctx;
    const canvas = elements.graph.canvas;

    if (!ctx || !canvas) return;

    const now = Date.now();

    const marginLeft = 50;
    const marginBottom = 25;
    const marginTop = 10;
    const marginRight = 10;
    const graphWidth = canvas.width - marginLeft - marginRight;
    const graphHeight = canvas.height - marginTop - marginBottom;

    if (now - graphData.lastUpdate > 100) {
        graphData.originalFrames.push(state.baselineFrameCount);
        graphData.predictedFrames.push(state.predictionFrameCount);
        graphData.lastUpdate = now;

        if (graphData.originalFrames.length > graphData.maxPoints) {
            graphData.originalFrames.shift();
            graphData.predictedFrames.shift();
        }
    }

    ctx.fillStyle = 'rgba(26, 26, 46, 1)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const maxVal = Math.max(
        Math.max(...graphData.predictedFrames, 0),
        Math.max(...graphData.originalFrames, 0),
        10
    );

    const yMax = Math.ceil(maxVal / 10) * 10 || 10;

    ctx.font = '11px Arial';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';

    for (let i = 0; i <= 5; i++) {
        const yVal = (yMax / 5) * i;
        const y = marginTop + graphHeight - (graphHeight / 5) * i;

        ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(marginLeft, y);
        ctx.lineTo(canvas.width - marginRight, y);
        ctx.stroke();

        ctx.fillStyle = 'rgba(255, 255, 255, 0.6)';
        ctx.fillText(Math.round(yVal).toString(), marginLeft - 8, y);
    }

    ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(marginLeft, marginTop);
    ctx.lineTo(marginLeft, marginTop + graphHeight);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(marginLeft, marginTop + graphHeight);
    ctx.lineTo(canvas.width - marginRight, marginTop + graphHeight);
    ctx.stroke();

    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillStyle = 'rgba(255, 255, 255, 0.6)';
    const xLabels = ['10s ago', '8s', '6s', '4s', '2s', 'Now'];
    xLabels.forEach((label, i) => {
        const x = marginLeft + (graphWidth / 5) * i;
        ctx.fillText(label, x, marginTop + graphHeight + 5);
    });

    ctx.save();
    ctx.translate(12, marginTop + graphHeight / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.textAlign = 'center';
    ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
    ctx.font = '10px Arial';
    ctx.fillText('Frames', 0, 0);
    ctx.restore();

    if (graphData.originalFrames.length < 2) return;

    const xStep = graphWidth / (graphData.maxPoints - 1);
    const yScale = graphHeight / yMax;

    ctx.strokeStyle = '#00ff88';
    ctx.lineWidth = 2;
    ctx.beginPath();
    graphData.predictedFrames.forEach((val, i) => {
        const x = marginLeft + i * xStep;
        const y = marginTop + graphHeight - (val * yScale);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.stroke();

    ctx.strokeStyle = '#0077ff';
    ctx.lineWidth = 2;
    ctx.beginPath();
    graphData.originalFrames.forEach((val, i) => {
        const x = marginLeft + i * xStep;
        const y = marginTop + graphHeight - (val * yScale);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.stroke();
}

// Initialize stream graph animation
let graphAnimationId = null;
function startGraphAnimation() {
    function animate() {
        drawStreamGraph();
        updateStreamStats();
        graphAnimationId = requestAnimationFrame(animate);
    }
    animate();
}

function stopGraphAnimation() {
    if (graphAnimationId) {
        cancelAnimationFrame(graphAnimationId);
        graphAnimationId = null;
    }
}

// Initialize
setupEventListeners();
initializeCanvases();
startGraphAnimation();
log('🎥 Video system initialized. Ready to connect.', 'info');
