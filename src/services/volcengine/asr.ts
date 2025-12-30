// src/services/volcengine/asr.ts
import { v4 as uuidv4 } from 'uuid';
import {
    buildFullClientRequest,
    buildAudioOnlyRequest,
    parseResponse
} from './protocol';

// Helper to convert Float32 (Web Audio) to Int16 (PCM)
function convertFloat32ToInt16(buffer: Float32Array): Int16Array {
    let l = buffer.length;
    const buf = new Int16Array(l);
    while (l--) {
        buf[l] = Math.min(1, Math.max(-1, buffer[l])) * 0x7FFF;
    }
    return buf;
}

// Downsample if needed (Browser is usually 44.1/48k, Volc needs 16k)
function downsampleBuffer(buffer: Float32Array, inputRate: number, outputRate: number = 16000): Float32Array {
    if (outputRate === inputRate) {
        return buffer;
    }
    const sampleRateRatio = inputRate / outputRate;
    const newLength = Math.round(buffer.length / sampleRateRatio);
    const result = new Float32Array(newLength);
    let offsetResult = 0;
    let offsetBuffer = 0;
    while (offsetResult < result.length) {
        const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio);
        let accum = 0, count = 0;
        for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
            accum += buffer[i];
            count++;
        }
        result[offsetResult] = count > 0 ? accum / count : 0;
        offsetResult++;
        offsetBuffer = nextOffsetBuffer;
    }
    return result;
}

export class VolcEngineAsrClient {
    private ws: WebSocket | null = null;
    private audioContext: AudioContext | null = null;
    private mediaStream: MediaStream | null = null;
    private processor: ScriptProcessorNode | null = null;

    private onResult: (text: string) => void;
    private seq: number = 1;
    private frameCount: number = 0;
    private totalBytesSent: number = 0;

    constructor(onResult: (text: string) => void) {
        this.onResult = onResult;
    }

    async start() {
        console.log("🎤 [ASR] start() called");

        // 1. Get Mic
        try {
            console.log("🎤 [ASR] Requesting microphone access...");
            this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const audioTracks = this.mediaStream.getAudioTracks();
            console.log("🎤 [ASR] ✓ Microphone access granted. Tracks:", audioTracks.length);
            audioTracks.forEach((track, i) => {
                console.log(`🎤 [ASR] Track ${i}: ${track.label}, enabled: ${track.enabled}, muted: ${track.muted}`);
            });
        } catch (e) {
            console.error("🎤 [ASR] ❌ Failed to get microphone:", e);
            return;
        }

        // 2. Connect WS (Proxy)
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const url = `${protocol}//${host}/api/ws/asr`;

        console.log("🎤 [ASR] Connecting to:", url);
        this.ws = new WebSocket(url);
        this.ws.binaryType = 'arraybuffer';

        this.ws.onopen = () => {
            console.log("🎤 [ASR] WebSocket OPEN");
            this.sendFullRequest();
            this.startAudioProcessing();
        };

        this.ws.onmessage = (event) => {
            console.log("🎤 [ASR] Message received, size:", event.data.byteLength, "bytes");
            const parsed = parseResponse(event.data);
            if (parsed && parsed.payload) {
                console.log("🎤 [ASR] Parsed response:", JSON.stringify(parsed.payload, null, 2));

                // Check for error
                if (parsed.payload.code && parsed.payload.code !== 0) {
                    console.error("🎤 [ASR] ❌ Server error:", parsed.payload);
                    return;
                }

                if (parsed.payload.result && parsed.payload.result[0]) {
                    const text = parsed.payload.result[0].text;
                    console.log("🎤 [ASR] ✓ Recognized text:", text);
                    this.onResult(text);
                } else {
                    console.log("🎤 [ASR] Response has no text result");
                }
            } else {
                console.log("🎤 [ASR] Could not parse response");
            }
        };

        this.ws.onerror = (e) => {
            console.error("🎤 [ASR] ❌ WebSocket ERROR:", e);
        };

        this.ws.onclose = (e) => {
            console.log("🎤 [ASR] WebSocket CLOSED. Code:", e.code, "Reason:", e.reason);
            console.log("🎤 [ASR] Session stats: Frames sent:", this.frameCount, "Total bytes:", this.totalBytesSent);
        };
    }

    private sendFullRequest() {
        if (!this.ws) return;

        const reqid = uuidv4();
        const payload = {
            user: { uid: "browser_user" },
            audio: {
                format: "pcm",  // Use "pcm" for raw PCM data (no WAV headers)
                codec: "raw",
                rate: 16000,
                bits: 16,
                channel: 1
            },
            request: {
                reqid: reqid,
                workflow: "audio_in",
                sequence: 1,
                model_name: "bigmodel",
                enable_itn: true,
                result_type: "full"
            }
        };

        console.log("🎤 [ASR] Sending initial request:", JSON.stringify(payload, null, 2));
        const frame = buildFullClientRequest(payload, this.seq++);
        this.ws.send(frame);
        console.log("🎤 [ASR] Initial request sent, waiting for audio input...");
    }

    private startAudioProcessing() {
        if (!this.mediaStream) return;

        this.audioContext = new AudioContext();
        console.log("🎤 [ASR] AudioContext created. Sample rate:", this.audioContext.sampleRate);

        const source = this.audioContext.createMediaStreamSource(this.mediaStream);
        this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);

        // Track audio levels for debugging
        let maxLevel = 0;
        let sampleCount = 0;

        this.processor.onaudioprocess = (e) => {
            if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

            const inputData = e.inputBuffer.getChannelData(0);

            // Calculate audio level (for debugging)
            let sum = 0;
            for (let i = 0; i < inputData.length; i++) {
                sum += Math.abs(inputData[i]);
            }
            const avgLevel = sum / inputData.length;
            if (avgLevel > maxLevel) maxLevel = avgLevel;
            sampleCount++;

            // Log every 50 frames (~3 seconds at 4096 samples)
            if (sampleCount % 50 === 0) {
                console.log(`🎤 [ASR] Audio level check - Avg: ${avgLevel.toFixed(4)}, Max seen: ${maxLevel.toFixed(4)}`);
                if (maxLevel < 0.01) {
                    console.warn("🎤 [ASR] ⚠️ Audio level very low! Check if microphone is working.");
                }
            }

            // Downsample and convert
            const downsampled = downsampleBuffer(inputData, this.audioContext!.sampleRate, 16000);
            const pcmData = convertFloat32ToInt16(downsampled);
            const pcmBytes = new Uint8Array(pcmData.buffer);

            // Build and send frame
            const frame = buildAudioOnlyRequest(pcmBytes, this.seq++, false);
            this.ws.send(frame);

            this.frameCount++;
            this.totalBytesSent += frame.length;

            // Log every 100 frames
            if (this.frameCount % 100 === 0) {
                console.log(`🎤 [ASR] Sent ${this.frameCount} frames, ${this.totalBytesSent} bytes total`);
            }
        };

        source.connect(this.processor);
        this.processor.connect(this.audioContext.destination);
        console.log("🎤 [ASR] Audio processing started. Waiting for speech...");
    }

    stop() {
        console.log("🎤 [ASR] stop() called. Frames sent:", this.frameCount, "Bytes:", this.totalBytesSent);

        if (this.processor) this.processor.disconnect();
        if (this.audioContext) this.audioContext.close();
        if (this.mediaStream) this.mediaStream.getTracks().forEach(t => t.stop());

        if (this.ws) {
            if (this.ws.readyState === WebSocket.OPEN) {
                try {
                    console.log("🎤 [ASR] Sending final frame with isLast=true");
                    const frame = buildAudioOnlyRequest(new Uint8Array(0), this.seq++, true);
                    this.ws.send(frame);
                } catch (e) {
                    console.error("🎤 [ASR] Error sending final frame:", e);
                }
                this.ws.close();
            } else if (this.ws.readyState === WebSocket.CONNECTING) {
                console.log("🎤 [ASR] WebSocket still connecting, will close on open");
                this.ws.onopen = () => this.ws?.close();
            } else {
                console.log("🎤 [ASR] WebSocket already closed/closing. State:", this.ws.readyState);
            }
        }

        this.ws = null;
        this.processor = null;
        this.audioContext = null;
        this.mediaStream = null;
        this.frameCount = 0;
        this.totalBytesSent = 0;
    }
}
