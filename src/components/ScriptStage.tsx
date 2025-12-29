// src/components/ScriptStage.tsx
import { useEffect } from 'react';
import { useAppStore } from '../store/useAppStore';
import { ScriptLineItem } from './ScriptLineItem';
export const ScriptStage = () => {
    const { currentLineIndex, script: activeScript } = useAppStore();

    if (!activeScript) return <div>Loading script...</div>;

    const roleMap = activeScript.meta.roleMap;

    return (
        <div className="w-full max-w-2xl mx-auto pb-40">
            <div className="text-center py-6">
                <h2 className="text-xl font-bold text-gray-800">{activeScript.meta.title}</h2>
                <p className="text-sm text-gray-500">{activeScript.meta.description}</p>
            </div>

            <div className="space-y-4">
                {activeScript.lines.map((line, index) => (
                    <ScriptLineItem
                        key={line.id}
                        line={line}
                        isActive={index === currentLineIndex}
                        roleName={roleMap[line.role] || line.role}
                    />
                ))}
            </div>
        </div>
    );
};
