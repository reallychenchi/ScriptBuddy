// src/services/interfaces.ts

export interface IPerformer {
    /**
     * Start listening for user input (ASR).
     * MUST ensure TTS is stopped before calling this.
     * @param onResult Callback for final recognized text.
     */
    listen(onResult: (text: string) => void): void;

    /**
     * Speak text (TTS).
     * MUST ensure ASR is stopped before calling this.
     * @param text Text to speak.
     * @param options volume: 0-1 (default 1).
     */
    speak(text: string, options?: { volume?: number }): Promise<void>;

    /**
     * Stop both ASR and TTS immediately.
     */
    stop(): void;

    /**
     * Check system permissions (Mic, AudioContext).
     */
    checkSystem(): Promise<{ micGranted: boolean; volumeReady: boolean }>;
}

export interface IReviewer {
    /**
     * Analytic intent from user text.
     */
    judgeIntent(userText: string, context?: any): Promise<string>;
}
