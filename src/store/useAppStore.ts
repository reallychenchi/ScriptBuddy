// src/store/useAppStore.ts
import { create } from 'zustand';

// Types from Design
export type RoleKey = '甲' | '乙' | '合';

export interface ScriptLine {
    id: string;
    role: RoleKey;
    content: string;
    emotion?: string;
    duration?: number;
}

export interface ScriptDoc {
    meta: {
        title: string;
        roleMap: Record<RoleKey, string>;
        description: string;
    };
    lines: ScriptLine[];
}

export type AppPhase = 'INIT' | 'ROLE_SELECT' | 'PRACTICE' | 'INTENT_CHECK' | 'ERROR';
export type PracticeState =
    | 'IDLE'
    | 'COMPANION_SPEAKING'
    | 'USER_SPEAKING'
    | 'TOGETHER_SPEAKING'
    | 'PROCESSING';

export interface AppConfig {
    asr: {
        appId: string;
        token: string;
        secret: string;
        cluster: string;
    };
    tts: {
        appId: string;
        token: string;
        secret: string;
        cluster: string;
    };
    llm: { apiKey: string; baseUrl?: string };
}

interface AppState {
    // Config
    userRole: RoleKey | null;
    masteryLevel: 1 | 2 | 3;
    serverConfig: AppConfig | null;

    // Script
    currentLineIndex: number;
    script: ScriptDoc | null;

    // Runtime
    phase: AppPhase;
    practiceState: PracticeState;

    // Resources
    volumeLevel: number;
    permissionsGranted: boolean;

    // Actions
    setPhase: (phase: AppPhase) => void;
    setUserRole: (role: RoleKey) => void;
    setMasteryLevel: (level: 1 | 2 | 3) => void;
    setServerConfig: (config: AppConfig) => void;
    setScript: (script: ScriptDoc) => void;
    setPermissionsGranted: (granted: boolean) => void;
    setPracticeState: (state: PracticeState) => void;
    nextLine: () => void;
}

export const useAppStore = create<AppState>((set) => ({
    userRole: null,
    masteryLevel: 1,
    serverConfig: null,
    currentLineIndex: 0,
    script: null,
    phase: 'INIT',
    practiceState: 'IDLE',
    volumeLevel: 0,
    permissionsGranted: false,

    setPhase: (phase) => set({ phase }),
    setUserRole: (userRole) => set({ userRole }),
    setMasteryLevel: (masteryLevel) => set({ masteryLevel }),
    setServerConfig: (serverConfig) => set({ serverConfig }),
    setScript: (script) => set({ script }),
    setPermissionsGranted: (permissionsGranted) => set({ permissionsGranted }),
    setPracticeState: (practiceState) => set({ practiceState }),
    nextLine: () => set((state) => ({ currentLineIndex: state.currentLineIndex + 1 })),
}));
