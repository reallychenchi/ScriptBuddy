// src/services/volcengine/performer.ts
import { IPerformer } from '../interfaces';
import { VolcEngineAsrClient } from './asr';
import { VolcEngineTTSClient } from './tts';

export class VolcEnginePerformer implements IPerformer {
    private asr: VolcEngineAsrClient | null = null;
    private tts: VolcEngineTTSClient;

    private isListening = false;
    private isSpeaking = false;
    private onResultCallback: ((text: string) => void) | null = null;

    constructor(private onStateChange?: (state: 'IDLE' | 'SPEAKING' | 'LISTENING') => void) {
        // No config needed - authentication handled by backend proxy
        this.tts = new VolcEngineTTSClient();
    }

    private updateState(state: 'IDLE' | 'SPEAKING' | 'LISTENING') {
        if (this.onStateChange) this.onStateChange(state);
    }

    async checkSystem() {
        return { micGranted: true, volumeReady: true };
    }

    listen(onResult: (text: string) => void): void {
        if (this.isSpeaking) {
            console.warn("VolcEngine: Simultaneous Listen/Speak (Together Mode)");
        }

        this.onResultCallback = onResult;
        this.isListening = true;
        this.updateState('LISTENING');

        // Create new ASR client for each listen session
        this.asr = new VolcEngineAsrClient((text) => {
            if (this.onResultCallback) this.onResultCallback(text);
        });
        this.asr.start();
    }

    async speak(text: string, options?: { volume?: number }): Promise<void> {
        this.isSpeaking = true;
        this.updateState('SPEAKING');
        try {
            await this.tts.speak(text, options);
        } finally {
            this.isSpeaking = false;
            // Only go IDLE if not listening (Together Mode)
            if (!this.isListening) this.updateState('IDLE');
        }
    }

    stop(): void {
        if (this.asr) {
            this.asr.stop();
            this.asr = null;
        }
        this.tts.stop();
        this.isListening = false;
        this.isSpeaking = false;
        this.updateState('IDLE');
    }
}
