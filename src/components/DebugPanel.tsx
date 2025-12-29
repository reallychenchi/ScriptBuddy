
import React, { useState } from 'react';
import clsx from 'clsx';
import { useAppStore } from '../store/useAppStore';

export function DebugPanel() {
    const { phase, masteryLevel, setMasteryLevel, nextLine } = useAppStore();
    const [isExpanded, setIsExpanded] = useState(false);

    // If we're in the INIT phase, maybe we don't need debug tools, or maybe we do.
    // The original App.tsx only showed it when phase !== 'INIT'.
    if (phase === 'INIT') return null;

    if (!isExpanded) {
        return (
            <button
                onClick={() => setIsExpanded(true)}
                className="fixed bottom-4 right-4 z-50 bg-gray-900 text-white p-3 rounded-full shadow-lg hover:bg-gray-700 transition-all opacity-50 hover:opacity-100"
                title="Open Debug Panel"
            >
                🐞
            </button>
        );
    }

    return (
        <div className="fixed bottom-4 right-4 z-50 bg-gray-900/90 text-white p-4 rounded-xl shadow-xl backdrop-blur-sm text-xs space-y-3 w-48 border border-gray-700">
            <div className="flex justify-between items-center border-b border-gray-700 pb-2">
                <h3 className="font-bold text-gray-300">Debug Panel</h3>
                <button
                    onClick={() => setIsExpanded(false)}
                    className="text-gray-400 hover:text-white"
                >
                    ✕
                </button>
            </div>

            <div className="space-y-2">
                <div className="flex justify-between items-center text-gray-400">
                    <span>Phase:</span>
                    <span className="font-mono text-purple-400">{phase}</span>
                </div>

                <div className="pt-2">
                    <button
                        onClick={nextLine}
                        className="w-full bg-blue-600 hover:bg-blue-500 py-2 rounded font-medium transition-colors"
                    >
                        Next Line
                    </button>
                </div>

                <div className="pt-2">
                    <p className="mb-1 text-gray-500">Mastery Level</p>
                    <div className="flex gap-1 justify-between">
                        {[1, 2, 3].map(lv => (
                            <button
                                key={lv}
                                onClick={() => setMasteryLevel(lv as 1 | 2 | 3)}
                                className={clsx(
                                    "flex-1 py-1 rounded transition-colors",
                                    masteryLevel === lv ? "bg-green-600 text-white" : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                                )}
                            >
                                L{lv}
                            </button>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
