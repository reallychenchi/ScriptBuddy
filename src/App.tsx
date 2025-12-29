
import { useState, useEffect } from 'react';
import { StartupCheck } from './components/StartupCheck';
import { ScriptStage } from './components/ScriptStage';
import { VoiceLottieState } from './components/VoiceLottieState';
import { DebugPanel } from './components/DebugPanel';
import { useAppStore, RoleKey } from './store/useAppStore';
import { useScriptFlow } from './hooks/useScriptFlow';
import clsx from 'clsx';

function App() {
    useScriptFlow(); // Activate Script Logic Loop

    const { phase, setUserRole, setPhase } = useAppStore();
    const [isLandscape, setIsLandscape] = useState(true);

    // Initial check and subsequent listener for orientation
    useEffect(() => {
        const checkOrientation = () => {
            setIsLandscape(window.innerWidth >= window.innerHeight);
        };

        // Check initially
        checkOrientation();

        window.addEventListener('resize', checkOrientation);
        return () => window.removeEventListener('resize', checkOrientation);
    }, []);

    const handleRoleSelect = (role: RoleKey) => {
        setUserRole(role);
        setPhase('PRACTICE');
    };

    if (phase === 'INIT') {
        return <StartupCheck />;
    }

    // Role Selection Phase (Simplified for this full-screen layout)
    if (phase === 'ROLE_SELECT') {
        return (
            <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-4">
                <div className="max-w-md w-full text-center space-y-8">
                    <h2 className="text-3xl font-bold text-gray-800">Choose Your Role</h2>
                    <div className="grid grid-cols-2 gap-4">
                        <button
                            onClick={() => handleRoleSelect('甲')}
                            className="aspect-square bg-purple-100 hover:bg-purple-200 text-purple-700 rounded-2xl flex flex-col items-center justify-center gap-2 transition-all"
                        >
                            <span className="text-4xl">👔</span>
                            <span className="font-bold">Interviewer</span>
                        </button>
                        <button
                            onClick={() => handleRoleSelect('乙')}
                            className="aspect-square bg-blue-100 hover:bg-blue-200 text-blue-700 rounded-2xl flex flex-col items-center justify-center gap-2 transition-all"
                        >
                            <span className="text-4xl">👨‍💻</span>
                            <span className="font-bold">Candidate</span>
                        </button>
                    </div>
                </div>
                <DebugPanel />
            </div>
        );
    }

    // Main Practice Phase
    return (
        <div className={clsx(
            "min-h-screen bg-white flex overflow-hidden",
            isLandscape ? "flex-row" : "flex-col"
        )}>
            {/* Information / Script Area */}
            {/* Landscape: Left (50%), Portrait: Top (50%) */}
            <div className={clsx(
                "flex-1 overflow-auto border-gray-200 relative",
                isLandscape ? "border-r h-screen" : "border-b h-[50vh]",
            )}>
                <div className="h-full p-6">
                    <ScriptStage />
                </div>
            </div>

            {/* Voice / Animation Area */}
            {/* Landscape: Right (50%), Portrait: Bottom (50%) */}
            <div className={clsx(
                "flex-1 bg-gray-50 flex items-center justify-center relative",
                isLandscape ? "h-screen" : "h-[50vh]",
            )}>
                <VoiceLottieState />
            </div>

            <DebugPanel />
        </div>
    );
}

export default App;
