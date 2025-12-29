// src/services/performer.ts
import { IPerformer } from './interfaces';

// Polyfill for Web Speech API types
declare global {
    interface Window {
        webkitSpeechRecognition: any;
        SpeechRecognition: any;
    }
}

export class BrowserPerformer implements IPerformer {
    private recognition: any;
    private isListening: boolean = false;
    private isSpeaking: boolean = false;

    constructor() {
        // Init Speech Recognition
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRecognition) {
            this.recognition = new SpeechRecognition();
            this.recognition.continuous = false;
            this.recognition.lang = 'zh-CN';
            this.recognition.interimResults = false;
            this.recognition.maxAlternatives = 1;
        }
    }

    async checkSystem() {
        const hasMic = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
        const hasSpeech = !!this.recognition;
        const hasTTS = !!window.speechSynthesis;
        return {
            micGranted: hasMic, // We assume true if check passed previously
            volumeReady: hasTTS
        };
    }

    listen(onResult: (text: string) => void): void {
        if (this.isSpeaking) {
            console.warn("Warning: Listening while speaking (Together Mode?)");
            // Relaxation: Do NOT return here, allow overlap for Together Mode
        }
        if (!this.recognition) {
            console.error("Speech Recognition not supported");
            return;
        }

        // Stop previous if any (Safety)
        try { this.recognition.stop(); } catch (e) { }

        this.isListening = true;
        this.recognition.onresult = (event: any) => {
            const text = event.results[0][0].transcript;
            console.log('ASR Result:', text);
            onResult(text);
            this.isListening = false;
        };

        this.recognition.onerror = (e: any) => {
            // Common error: 'no-speech' or 'aborted'
            console.log("ASR Status:", e.error);
            this.isListening = false;
        };

        this.recognition.onend = () => {
            this.isListening = false;
        };

        try {
            this.recognition.start();
            console.log("ASR Started");
        } catch (e) {
            console.error("Failed to start ASR", e);
        }
    }

    async speak(text: string, options?: { volume?: number }): Promise<void> {
        if (this.isListening) {
            console.warn("Warning: Speaking while listening");
            // Relaxation: Do NOT stop recognition here, allow overlap
        }

        return new Promise((resolve, reject) => {
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'zh-CN';
            utterance.volume = options?.volume ?? 1;
            utterance.rate = 1.0;

            utterance.onend = () => {
                this.isSpeaking = false;
                resolve();
            };

            utterance.onerror = (e) => {
                this.isSpeaking = false;
                console.error("TTS Error", e);
                resolve(); // Resolve anyway to not block flow
            };

            this.isSpeaking = true;
            console.log("TTS Speaking:", text);
            window.speechSynthesis.speak(utterance);
        });
    }

    stop(): void {
        if (this.recognition) try { this.recognition.stop(); } catch (e) { }
        if (window.speechSynthesis) window.speechSynthesis.cancel();
        this.isListening = false;
        this.isSpeaking = false;
    }
}
