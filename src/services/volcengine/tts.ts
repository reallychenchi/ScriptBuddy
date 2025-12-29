// src/services/volcengine/tts.ts
import { v4 as uuidv4 } from 'uuid';
import {
    buildFullClientRequest,
    parseResponse
} from './protocol';

export class VolcEngineTTSClient {
    private ws: WebSocket | null = null;
    private audioContext: AudioContext | null = null;

    constructor() {
        // No config needed - authentication handled by backend proxy
    }

    async speak(text: string, options: { volume?: number } = {}): Promise<void> {
        console.log("🔊 [TTS] speak() called with text:", text.substring(0, 50) + (text.length > 50 ? "..." : ""));

        return new Promise((resolve, reject) => {
            // Proxy URL
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = window.location.host;
            const url = `${protocol}//${host}/api/ws/tts`;

            console.log("🔊 [TTS] Connecting to:", url);
            this.ws = new WebSocket(url);
            this.ws.binaryType = 'arraybuffer';

            let audioParts: ArrayBuffer[] = [];
            let messageCount = 0;

            this.ws.onopen = () => {
                console.log("🔊 [TTS] WebSocket OPEN");
                const reqid = uuidv4();

                const payload = {
                    user: { uid: "browser_user" },
                    audio: {
                        voice_type: "BV001_streaming",
                        encoding: "mp3",
                        rate: 24000
                    },
                    request: {
                        reqid: reqid,
                        text: text,
                        operation: "submit",
                        with_timestamp: 1
                    }
                };

                console.log("🔊 [TTS] Sending request payload:", JSON.stringify(payload, null, 2));
                const frame = buildFullClientRequest(payload);
                console.log("🔊 [TTS] Frame size:", frame.length, "bytes");
                this.ws?.send(frame);
                console.log("🔊 [TTS] Request sent, waiting for audio...");
            };

            this.ws.onmessage = async (event) => {
                messageCount++;
                console.log(`🔊 [TTS] Message #${messageCount} received, size:`, event.data.byteLength, "bytes");

                const parsed = parseResponse(event.data);
                if (!parsed) {
                    console.log("🔊 [TTS] Could not parse response, treating as raw audio");
                    if (event.data instanceof ArrayBuffer && event.data.byteLength > 0) {
                        audioParts.push(event.data);
                        console.log("🔊 [TTS] Added raw audio part, total parts:", audioParts.length);
                    }
                    return;
                }

                console.log("🔊 [TTS] Parsed response:", {
                    messageType: parsed.messageType,
                    isLast: parsed.isLast,
                    seq: parsed.seq,
                    payloadType: parsed.payload instanceof Uint8Array ? 'Uint8Array' : typeof parsed.payload,
                    payloadSize: parsed.payload instanceof Uint8Array ? parsed.payload.length : JSON.stringify(parsed.payload).length
                });

                // Check for error in JSON payload
                if (parsed.payload && !(parsed.payload instanceof Uint8Array)) {
                    if (parsed.payload.code && parsed.payload.code !== 0) {
                        console.error("🔊 [TTS] ❌ Server returned error:", parsed.payload);
                    }
                }

                // Check for audio payload
                if (parsed.payload instanceof Uint8Array && parsed.payload.length > 0) {
                    audioParts.push(parsed.payload.slice().buffer as ArrayBuffer);
                    console.log("🔊 [TTS] Added audio part, total parts:", audioParts.length);
                }

                // Check if last message
                if (parsed.isLast) {
                    console.log("🔊 [TTS] ✓ Last message received. Total audio parts:", audioParts.length);
                    const totalBytes = audioParts.reduce((acc, p) => acc + p.byteLength, 0);
                    console.log("🔊 [TTS] Total audio bytes:", totalBytes);

                    if (totalBytes > 0) {
                        await this.playAudio(audioParts, options.volume);
                    } else {
                        console.warn("🔊 [TTS] ⚠️ No audio data received!");
                    }
                    resolve();
                }
            };

            this.ws.onerror = (e) => {
                console.error("🔊 [TTS] ❌ WebSocket ERROR:", e);
                reject(new Error("TTS WebSocket error"));
            };

            this.ws.onclose = (e) => {
                console.log("🔊 [TTS] WebSocket CLOSED. Code:", e.code, "Reason:", e.reason);
                // If we have audio parts but didn't resolve yet, try to play
                if (audioParts.length > 0) {
                    const totalBytes = audioParts.reduce((acc, p) => acc + p.byteLength, 0);
                    console.log("🔊 [TTS] Playing audio on close. Total bytes:", totalBytes);
                    this.playAudio(audioParts, options.volume).then(resolve).catch(reject);
                } else {
                    console.warn("🔊 [TTS] ⚠️ Connection closed with no audio data");
                    resolve(); // Resolve anyway to not block the flow
                }
            };
        });
    }

    private async playAudio(parts: ArrayBuffer[], volume: number = 1.0): Promise<void> {
        console.log("🔊 [TTS] playAudio() called. Parts:", parts.length, "Volume:", volume);

        if (parts.length === 0) {
            console.warn("🔊 [TTS] ⚠️ No audio parts to play");
            return;
        }

        // Concatenate all audio parts
        const totalLength = parts.reduce((acc, p) => acc + p.byteLength, 0);
        console.log("🔊 [TTS] Concatenating audio. Total length:", totalLength, "bytes");

        const combined = new Uint8Array(totalLength);
        let offset = 0;
        for (const part of parts) {
            combined.set(new Uint8Array(part), offset);
            offset += part.byteLength;
        }

        try {
            if (!this.audioContext) {
                this.audioContext = new AudioContext();
                console.log("🔊 [TTS] Created AudioContext. State:", this.audioContext.state);
            }

            // Resume if suspended (browser autoplay policy)
            if (this.audioContext.state === 'suspended') {
                console.log("🔊 [TTS] AudioContext suspended, resuming...");
                await this.audioContext.resume();
                console.log("🔊 [TTS] AudioContext resumed. State:", this.audioContext.state);
            }

            console.log("🔊 [TTS] Decoding audio data...");
            const audioBuffer = await this.audioContext.decodeAudioData(combined.buffer.slice(0));
            console.log("🔊 [TTS] ✓ Audio decoded. Duration:", audioBuffer.duration, "sec, Channels:", audioBuffer.numberOfChannels);

            const source = this.audioContext.createBufferSource();
            source.buffer = audioBuffer;

            // Volume control
            const gainNode = this.audioContext.createGain();
            gainNode.gain.value = volume;
            source.connect(gainNode);
            gainNode.connect(this.audioContext.destination);

            console.log("🔊 [TTS] ▶️ Starting playback...");
            source.start();

            return new Promise((resolve) => {
                source.onended = () => {
                    console.log("🔊 [TTS] ✓ Playback finished");
                    resolve();
                };
            });
        } catch (e) {
            console.error("🔊 [TTS] ❌ Failed to decode/play audio:", e);
            // Log first 50 bytes to help debug format issues
            console.log("🔊 [TTS] First 50 bytes:", Array.from(combined.slice(0, 50)));
        }
    }

    stop(): void {
        console.log("🔊 [TTS] stop() called");
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}
