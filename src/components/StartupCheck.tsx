// src/components/StartupCheck.tsx
import { useEffect, useState } from 'react';
import { useAppStore } from '../store/useAppStore';
// import { Performer } from '../services/performer'; // TODO: Implement

export const StartupCheck = () => {
    const { setServerConfig, setPermissionsGranted, setPhase, setScript } = useAppStore();
    const [status, setStatus] = useState('Loading config...');
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        // 1. Fetch Config & Script
        const fetchInitData = async () => {
            try {
                // Fetch Config (Relative Path via Proxy)
                const resConfig = await fetch('api/config'); // Python API is /api/config (no .php)
                if (!resConfig.ok) throw new Error('Failed to load config');
                const configData = await resConfig.json();
                setServerConfig(configData);

                // Fetch Script
                const resScript = await fetch('api/script'); // Python API is /api/script
                if (!resScript.ok) throw new Error('Failed to load script');
                const scriptData = await resScript.json();
                setScript(scriptData); // Store the script

                setStatus('Checking permissions...');
                checkPermissions();
            } catch (err) {
                console.error(err);
                setError('无法连接服务器获取数据。请检查网络或后端接口。');
            }
        };

        fetchInitData();
    }, [setServerConfig, setScript]);

    const checkPermissions = async () => {
        // TODO: Use real Performer.checkSystem()
        // Mock for Phase 1
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            stream.getTracks().forEach(track => track.stop()); // Release immediately
            setPermissionsGranted(true);
            setPhase('ROLE_SELECT');
        } catch (err) {
            setError('无法访问麦克风。请允许浏览器使用麦克风权限。');
        }
    };

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center h-screen p-4 text-center">
                <h2 className="text-3xl font-bold text-red-600 mb-4">⚠️ 需要权限</h2>
                <p className="text-xl text-gray-700 mb-8">{error}</p>
                <button
                    onClick={() => window.location.reload()}
                    className="px-6 py-3 bg-blue-600 text-white rounded-lg text-lg font-semibold hover:bg-blue-700"
                >
                    重试
                </button>
            </div>
        );
    }

    return (
        <div className="flex flex-col items-center justify-center h-screen bg-gray-50">
            <h1 className="text-4xl font-bold text-gray-800 mb-4 animate-bounce">
                ScriptBuddy
            </h1>
            <p className="text-gray-600 text-lg">{status}</p>
        </div>
    );
};
