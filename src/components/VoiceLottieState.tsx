// src/components/VoiceLottieState.tsx
import Lottie from 'lottie-react';
import { useAppStore } from '../store/useAppStore';

// Build imports for assets/lottie
// @ts-ignore
import boySpeaking from '../assets/lottie/boy_speaking.json';
// @ts-ignore
import blueMicrophone from '../assets/lottie/blue_microphone.json';
// @ts-ignore
import boyWandering from '../assets/lottie/boy_wandering.json';

export const VoiceLottieState = () => {
    const { practiceState } = useAppStore();

    let animationData = boyWandering;

    if (practiceState === 'COMPANION_SPEAKING' || practiceState === 'TOGETHER_SPEAKING') {
        animationData = boySpeaking;
    } else if (practiceState === 'USER_SPEAKING') {
        animationData = blueMicrophone;
    }

    return (
        <div className="w-[80%] aspect-square flex items-center justify-center">
            <Lottie animationData={animationData} loop={true} />
        </div>
    );
};
