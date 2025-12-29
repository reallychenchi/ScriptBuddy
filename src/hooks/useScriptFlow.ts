// src/hooks/useScriptFlow.ts
import { useEffect, useRef } from 'react';
import { useAppStore } from '../store/useAppStore';
import { VolcEnginePerformer } from '../services/volcengine/performer';
import { DeepSeekReviewer } from '../services/deepseek';

export const useScriptFlow = () => {
    const {
        phase, script, currentLineIndex, userRole,
        serverConfig, nextLine, setPhase, setMasteryLevel, setPracticeState
    } = useAppStore();

    const performer = useRef<any>(null);
    const reviewer = useRef<DeepSeekReviewer | null>(null);

    // init services
    useEffect(() => {
        if (!performer.current) {
            performer.current = new VolcEnginePerformer((state) => {
                // Map performer state to app state
                if (state === 'SPEAKING') setPracticeState('COMPANION_SPEAKING');
                else if (state === 'LISTENING') setPracticeState('USER_SPEAKING');
                else setPracticeState('IDLE');
            });
        }
        if (serverConfig && serverConfig.llm && serverConfig.llm.apiKey) {
            reviewer.current = new DeepSeekReviewer(serverConfig.llm.apiKey);
        }
    }, [serverConfig]);

    // Main Loop
    useEffect(() => {
        if (phase !== 'PRACTICE' || !script || !userRole) return;

        const currentLine = script.lines[currentLineIndex];
        if (!currentLine) {
            console.log("End of Script");
            performer.current.speak("练习结束");
            setPhase('INIT'); // simplified end
            return;
        }

        const processLine = async () => {
            const roleKey = currentLine.role;

            if (roleKey === userRole) {
                // User's Turn
                console.log("Flow: User Turn");
                await performer.current.stop(); // ensure clean state

                performer.current.listen(async (text: string) => {
                    console.log("User said:", text);
                    // Intent Check (Async)
                    if (reviewer.current) {
                        const intent = await reviewer.current.judgeIntent(text);
                        console.log("Intent:", intent);
                        if (intent === 'STOP') {
                            setPhase('INIT');
                            performer.current.stop();
                            return;
                        }
                        if (intent === 'CHANGE_LEVEL') {
                            setMasteryLevel(2); // Mock logic just up level
                            return;
                        }
                    }

                    // Naive Finish Check: user said something -> Next
                    nextLine();
                });
            } else if (roleKey === '合') {
                // Together Mode
                console.log("Flow: Together Mode");
                performer.current.speak(currentLine.content, { volume: 0.3 }); // Background
                performer.current.listen((text: string) => {
                    console.log("User (Together) said:", text);
                    // Also check intent?
                    nextLine();
                });
            } else {
                // Companion Turn
                console.log("Flow: Companion Turn");
                await performer.current.stop();
                await performer.current.speak(currentLine.content);
                nextLine();
            }
        };

        processLine();

        // Cleanup on unmount or line change (stop previous audio if moving fast)
        // Actually we shouldn't stop indiscriminately or TTS cuts off.
        // Ideally processLine handles the sequence.
        return () => {
            // cleanup?
        };

    }, [currentLineIndex, phase, userRole, script /*, nextLine, setPhase*/]); // Careful with dependencies

    // expose nothing, just run effects
};
