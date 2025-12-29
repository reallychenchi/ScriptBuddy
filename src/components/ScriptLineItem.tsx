// src/components/ScriptLineItem.tsx
import { useEffect, useRef } from 'react';
import { ScriptLine, useAppStore } from '../store/useAppStore';
import clsx from 'clsx';

interface Props {
    line: ScriptLine;
    isActive: boolean;
    roleName: string;
}

export const ScriptLineItem = ({ line, isActive, roleName }: Props) => {
    const { userRole, masteryLevel } = useAppStore();
    const ref = useRef<HTMLDivElement>(null);

    // Auto-scroll into view if active
    useEffect(() => {
        if (isActive && ref.current) {
            ref.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }, [isActive]);

    const isUser = line.role === userRole;
    const isTogether = line.role === '合';

    // Determine Text Logic
    // Default: Visible (Black/Blue)
    // Mastery Levels applies to User Lines (and Together lines?)
    // Let's assume together lines also follow mastery rules for the user part?
    // Requirements: 
    // User Lines: Level 1 Black, Level 2 Gray, Level 3 White
    // Companion Lines: Normal Dark Blue, Mastery 3 White? (Req says "平时用蓝色，最后默背用背景色")

    let textColorClass = 'text-gray-900'; // Default black

    if (isUser || isTogether) {
        if (masteryLevel === 1) textColorClass = 'text-gray-900';
        else if (masteryLevel === 2) textColorClass = 'text-gray-300';
        else if (masteryLevel === 3) textColorClass = 'text-transparent'; // Invisible but takes space
    } else {
        // Companion
        if (masteryLevel === 3) textColorClass = 'text-transparent';
        else textColorClass = 'text-blue-800';
    }

    // Highlight active line - User requested NO background.
    // Maybe just bold or marker? Leaving "scale-105" for subtle active indication without bg.
    const containerClasses = isActive ? 'scale-105' : 'opacity-60'; // Dim inactive lines to focus? User said "Direct text".

    return (
        <div
            ref={ref}
            className={clsx(
                "py-2 px-4 transition-all duration-300 ease-in-out",
                containerClasses
            )}
        >
            <div className="flex items-baseline justify-between mb-1">
                <span className={clsx(
                    "text-xs font-bold uppercase tracking-wide",
                    (isUser || isTogether) ? "text-purple-600" : "text-blue-500"
                )}>
                    {roleName} {isTogether && '(合)'}
                </span>
            </div>
            <p className={clsx("text-2xl font-medium leading-relaxed font-serif", textColorClass)}>
                {line.content}
            </p>
        </div>
    );
};
