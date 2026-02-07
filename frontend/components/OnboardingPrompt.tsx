'use client';

import { useEffect, useRef } from 'react';

interface OnboardingPromptProps {
    isOpen: boolean;
    onSetupGoals: () => void;
    onDismiss: () => void;
}

/**
 * Onboarding prompt modal that encourages first-time users
 * to set up their nutrition goals before analyzing meals.
 */
export default function OnboardingPrompt({
    isOpen,
    onSetupGoals,
    onDismiss
}: OnboardingPromptProps) {
    const modalRef = useRef<HTMLDivElement>(null);

    // Handle escape key to close
    useEffect(() => {
        const handleEscape = (e: KeyboardEvent) => {
            if (e.key === 'Escape' && isOpen) {
                onDismiss();
            }
        };
        window.addEventListener('keydown', handleEscape);
        return () => window.removeEventListener('keydown', handleEscape);
    }, [isOpen, onDismiss]);

    // Focus trap
    useEffect(() => {
        if (isOpen && modalRef.current) {
            modalRef.current.focus();
        }
    }, [isOpen]);

    if (!isOpen) return null;

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            role="dialog"
            aria-modal="true"
            aria-labelledby="onboarding-title"
        >
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                onClick={onDismiss}
            />

            {/* Modal */}
            <div
                ref={modalRef}
                tabIndex={-1}
                className="relative w-full max-w-md bg-gradient-to-br from-zinc-900 to-zinc-800 
                   rounded-2xl shadow-2xl border border-zinc-700/50 overflow-hidden
                   animate-in fade-in zoom-in-95 duration-200"
            >
                {/* Decorative gradient top */}
                <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-emerald-400 via-teal-400 to-cyan-400" />

                {/* Content */}
                <div className="p-8">
                    {/* Icon */}
                    <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-gradient-to-br from-emerald-500/20 to-teal-500/20 
                          flex items-center justify-center border border-emerald-500/30">
                        <span className="text-4xl">🎯</span>
                    </div>

                    {/* Title */}
                    <h2
                        id="onboarding-title"
                        className="text-2xl font-bold text-center text-white mb-3"
                    >
                        Welcome to NutriPilot! 👋
                    </h2>

                    {/* Description */}
                    <p className="text-zinc-300 text-center mb-6 leading-relaxed">
                        Before we analyze your meal, let's set up your <span className="text-emerald-400 font-medium">nutrition goals</span> and <span className="text-emerald-400 font-medium">health conditions</span>.
                    </p>

                    {/* Benefits list */}
                    <div className="bg-zinc-800/50 rounded-xl p-4 mb-6 space-y-3">
                        <div className="flex items-start gap-3">
                            <span className="text-emerald-400 mt-0.5">✓</span>
                            <p className="text-sm text-zinc-300">
                                <span className="font-medium text-white">Personalized Feedback</span> — Get advice tailored to YOUR goals
                            </p>
                        </div>
                        <div className="flex items-start gap-3">
                            <span className="text-emerald-400 mt-0.5">✓</span>
                            <p className="text-sm text-zinc-300">
                                <span className="font-medium text-white">Health-Aware Analysis</span> — We'll flag foods that conflict with your conditions
                            </p>
                        </div>
                        <div className="flex items-start gap-3">
                            <span className="text-emerald-400 mt-0.5">✓</span>
                            <p className="text-sm text-zinc-300">
                                <span className="font-medium text-white">Smart Tracking</span> — Monitor progress toward your targets
                            </p>
                        </div>
                    </div>

                    {/* Buttons */}
                    <div className="flex flex-col gap-3">
                        <button
                            onClick={onSetupGoals}
                            className="w-full py-3 px-6 bg-gradient-to-r from-emerald-500 to-teal-500 
                         hover:from-emerald-400 hover:to-teal-400
                         text-white font-semibold rounded-xl
                         transition-all duration-200 transform hover:scale-[1.02]
                         shadow-lg shadow-emerald-500/25"
                        >
                            Set Up My Goals
                        </button>

                        <button
                            onClick={onDismiss}
                            className="w-full py-3 px-6 text-zinc-400 hover:text-white
                         font-medium rounded-xl transition-colors duration-200
                         hover:bg-zinc-800/50"
                        >
                            Maybe Later
                        </button>
                    </div>

                    {/* Note */}
                    <p className="text-xs text-zinc-500 text-center mt-4">
                        ⚠️ Without goals, you'll receive generic feedback only
                    </p>
                </div>
            </div>
        </div>
    );
}
