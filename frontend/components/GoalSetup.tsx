'use client';

import { useState, useEffect } from 'react';
import { API_BASE_URL } from '@/lib/api';

interface Goal {
    value: string;
    label: string;
}

interface Condition {
    value: string;
    label: string;
}

interface DailyTargets {
    calories: number;
    protein_g: number;
    carbs_g: number;
    fat_g: number;
    fiber_g: number;
    sodium_mg: number;
    sugar_g: number;
}

interface GoalSetupProps {
    userId: string;
    isOpen: boolean;
    onClose: () => void;
    onSave: () => void;
}

const DEFAULT_TARGETS: DailyTargets = {
    calories: 2000,
    protein_g: 50,
    carbs_g: 250,
    fat_g: 65,
    fiber_g: 25,
    sodium_mg: 2300,
    sugar_g: 50,
};

export default function GoalSetup({ userId, isOpen, onClose, onSave }: GoalSetupProps) {
    const [step, setStep] = useState(1);
    const [availableGoals, setAvailableGoals] = useState<Goal[]>([]);
    const [availableConditions, setAvailableConditions] = useState<Condition[]>([]);
    const [selectedGoals, setSelectedGoals] = useState<string[]>([]);
    const [selectedConditions, setSelectedConditions] = useState<string[]>([]);
    const [dietaryRestrictions, setDietaryRestrictions] = useState<string[]>([]);
    const [restrictionInput, setRestrictionInput] = useState('');
    const [dailyTargets, setDailyTargets] = useState<DailyTargets>(DEFAULT_TARGETS);
    const [timelineWeeks, setTimelineWeeks] = useState(12);
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);

    // Fetch available goals and conditions
    useEffect(() => {
        if (isOpen) {
            fetch(`${API_BASE_URL}/goals/available`)
                .then(res => res.json())
                .then(data => {
                    setAvailableGoals(data.goals || []);
                    setAvailableConditions(data.conditions || []);
                })
                .catch(err => console.error('Failed to fetch goals:', err));

            // Also fetch existing profile if any
            fetch(`${API_BASE_URL}/users/${userId}/profile`)
                .then(res => {
                    if (res.ok) return res.json();
                    throw new Error('No profile');
                })
                .then(profile => {
                    setSelectedGoals(profile.goals || []);
                    setSelectedConditions(profile.conditions || []);
                    setDietaryRestrictions(profile.dietary_restrictions || []);
                    setDailyTargets(profile.daily_targets || DEFAULT_TARGETS);
                    setTimelineWeeks(profile.timeline_weeks || 12);
                })
                .catch(() => {/* No existing profile */ });
        }
    }, [isOpen, userId]);

    const toggleGoal = (value: string) => {
        setSelectedGoals(prev =>
            prev.includes(value)
                ? prev.filter(g => g !== value)
                : [...prev, value]
        );
    };

    const toggleCondition = (value: string) => {
        setSelectedConditions(prev =>
            prev.includes(value)
                ? prev.filter(c => c !== value)
                : [...prev, value]
        );
    };

    const addRestriction = () => {
        if (restrictionInput.trim() && !dietaryRestrictions.includes(restrictionInput.trim())) {
            setDietaryRestrictions(prev => [...prev, restrictionInput.trim()]);
            setRestrictionInput('');
        }
    };

    const removeRestriction = (r: string) => {
        setDietaryRestrictions(prev => prev.filter(x => x !== r));
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            const response = await fetch(`${API_BASE_URL}/users/${userId}/profile`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    goals: selectedGoals,
                    conditions: selectedConditions,
                    dietary_restrictions: dietaryRestrictions,
                    daily_targets: dailyTargets,
                    timeline_weeks: timelineWeeks,
                }),
            });

            if (response.ok) {
                onSave();
                onClose();
            }
        } catch (err) {
            console.error('Failed to save profile:', err);
        } finally {
            setSaving(false);
        }
    };

    if (!isOpen) return null;

    const totalSteps = 4;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
            <div className="w-full max-w-lg bg-[#0a0a0f] border border-white/10 rounded-2xl shadow-2xl overflow-hidden">
                {/* Header */}
                <div className="p-6 border-b border-white/10">
                    <div className="flex items-center justify-between">
                        <h2 className="text-xl font-bold text-white">Set Your Health Goals</h2>
                        <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-lg transition-colors">
                            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                    {/* Progress bar */}
                    <div className="mt-4 flex gap-2">
                        {Array.from({ length: totalSteps }).map((_, i) => (
                            <div
                                key={i}
                                className={`h-1 flex-1 rounded-full transition-colors ${i < step ? 'bg-emerald-500' : 'bg-white/10'
                                    }`}
                            />
                        ))}
                    </div>
                </div>

                {/* Content */}
                <div className="p-6 max-h-[60vh] overflow-y-auto">
                    {/* Step 1: Goals */}
                    {step === 1 && (
                        <div className="space-y-4">
                            <h3 className="text-lg font-semibold text-white">What are your health goals?</h3>
                            <p className="text-sm text-gray-400">Select all that apply</p>
                            <div className="grid grid-cols-2 gap-3">
                                {availableGoals.map(goal => (
                                    <button
                                        key={goal.value}
                                        onClick={() => toggleGoal(goal.value)}
                                        className={`p-4 rounded-xl border text-left transition-all ${selectedGoals.includes(goal.value)
                                            ? 'border-emerald-500 bg-emerald-500/10 text-white'
                                            : 'border-white/10 hover:border-white/20 text-gray-300'
                                            }`}
                                    >
                                        <span className="text-sm font-medium">{goal.label}</span>
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Step 2: Conditions */}
                    {step === 2 && (
                        <div className="space-y-4">
                            <h3 className="text-lg font-semibold text-white">Any health conditions?</h3>
                            <p className="text-sm text-gray-400">We'll customize recommendations based on your conditions</p>
                            <div className="grid grid-cols-2 gap-3">
                                {availableConditions.map(cond => (
                                    <button
                                        key={cond.value}
                                        onClick={() => toggleCondition(cond.value)}
                                        className={`p-4 rounded-xl border text-left transition-all ${selectedConditions.includes(cond.value)
                                            ? 'border-amber-500 bg-amber-500/10 text-white'
                                            : 'border-white/10 hover:border-white/20 text-gray-300'
                                            }`}
                                    >
                                        <span className="text-sm font-medium">{cond.label}</span>
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Step 3: Daily Targets */}
                    {step === 3 && (
                        <div className="space-y-4">
                            <h3 className="text-lg font-semibold text-white">Daily Nutrient Targets</h3>
                            <p className="text-sm text-gray-400">Customize your daily goals</p>

                            <div className="space-y-4">
                                <div>
                                    <label className="flex justify-between text-sm text-gray-300 mb-2">
                                        <span>Calories</span>
                                        <span className="text-emerald-400">{dailyTargets.calories} kcal</span>
                                    </label>
                                    <input
                                        type="range"
                                        min="1200"
                                        max="4000"
                                        step="100"
                                        value={dailyTargets.calories}
                                        onChange={e => setDailyTargets(prev => ({ ...prev, calories: Number(e.target.value) }))}
                                        className="w-full accent-emerald-500"
                                    />
                                </div>

                                <div>
                                    <label className="flex justify-between text-sm text-gray-300 mb-2">
                                        <span>Protein</span>
                                        <span className="text-emerald-400">{dailyTargets.protein_g}g</span>
                                    </label>
                                    <input
                                        type="range"
                                        min="30"
                                        max="200"
                                        step="5"
                                        value={dailyTargets.protein_g}
                                        onChange={e => setDailyTargets(prev => ({ ...prev, protein_g: Number(e.target.value) }))}
                                        className="w-full accent-emerald-500"
                                    />
                                </div>

                                <div>
                                    <label className="flex justify-between text-sm text-gray-300 mb-2">
                                        <span>Carbs</span>
                                        <span className="text-emerald-400">{dailyTargets.carbs_g}g</span>
                                    </label>
                                    <input
                                        type="range"
                                        min="50"
                                        max="400"
                                        step="10"
                                        value={dailyTargets.carbs_g}
                                        onChange={e => setDailyTargets(prev => ({ ...prev, carbs_g: Number(e.target.value) }))}
                                        className="w-full accent-emerald-500"
                                    />
                                </div>

                                <div>
                                    <label className="flex justify-between text-sm text-gray-300 mb-2">
                                        <span>Sugar Limit</span>
                                        <span className="text-emerald-400">{dailyTargets.sugar_g}g</span>
                                    </label>
                                    <input
                                        type="range"
                                        min="10"
                                        max="100"
                                        step="5"
                                        value={dailyTargets.sugar_g}
                                        onChange={e => setDailyTargets(prev => ({ ...prev, sugar_g: Number(e.target.value) }))}
                                        className="w-full accent-emerald-500"
                                    />
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Step 4: Timeline */}
                    {step === 4 && (
                        <div className="space-y-4">
                            <h3 className="text-lg font-semibold text-white">Set Your Timeline</h3>
                            <p className="text-sm text-gray-400">How long do you want to track your progress?</p>

                            <div className="flex flex-wrap gap-3">
                                {[4, 8, 12, 24, 52].map(weeks => (
                                    <button
                                        key={weeks}
                                        onClick={() => setTimelineWeeks(weeks)}
                                        className={`px-4 py-3 rounded-xl border transition-all ${timelineWeeks === weeks
                                            ? 'border-emerald-500 bg-emerald-500/10 text-white'
                                            : 'border-white/10 hover:border-white/20 text-gray-300'
                                            }`}
                                    >
                                        {weeks < 12 ? `${weeks} weeks` : `${Math.round(weeks / 4)} months`}
                                    </button>
                                ))}
                            </div>

                            {/* Summary */}
                            <div className="mt-6 p-4 rounded-xl bg-white/5 border border-white/10">
                                <h4 className="text-sm font-semibold text-white mb-3">Your Plan Summary</h4>
                                <div className="space-y-2 text-sm">
                                    <div className="flex justify-between">
                                        <span className="text-gray-400">Goals:</span>
                                        <span className="text-emerald-400">{selectedGoals.length} selected</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-400">Conditions:</span>
                                        <span className="text-amber-400">{selectedConditions.length} selected</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-400">Daily Calories:</span>
                                        <span className="text-white">{dailyTargets.calories} kcal</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-400">Timeline:</span>
                                        <span className="text-white">{timelineWeeks} weeks</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-6 border-t border-white/10 flex justify-between">
                    <button
                        onClick={() => step > 1 ? setStep(step - 1) : onClose()}
                        className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
                    >
                        {step > 1 ? 'Back' : 'Cancel'}
                    </button>

                    {step < totalSteps ? (
                        <button
                            onClick={() => setStep(step + 1)}
                            className="px-6 py-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg font-medium transition-colors"
                        >
                            Continue
                        </button>
                    ) : (
                        <button
                            onClick={handleSave}
                            disabled={saving}
                            className="px-6 py-2 bg-emerald-500 hover:bg-emerald-600 disabled:bg-emerald-500/50 text-white rounded-lg font-medium transition-colors"
                        >
                            {saving ? 'Saving...' : 'Save Goals'}
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
