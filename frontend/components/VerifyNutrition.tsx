'use client';

import { useState } from 'react';
import { API_BASE_URL } from '@/lib/api';

interface VerifyNutritionProps {
    entryId: string;
    estimatedValues: {
        calories: number;
        protein: number;
        carbs: number;
        fat: number;
        fiber?: number;
        sodium?: number;
    };
    onVerified?: (result: VerificationResult) => void;
    onCancel?: () => void;
}

interface VerificationResult {
    status: string;
    entry_id: string;
    verified_at: string;
    verification_source: string;
    comparison: {
        calories: { estimated: number; actual: number; error: number; error_percent: number };
        protein?: { estimated: number; actual: number; error: number; error_percent: number };
        carbs?: { estimated: number; actual: number; error: number; error_percent: number };
        fat?: { estimated: number; actual: number; error: number; error_percent: number };
    };
}

const VERIFICATION_SOURCES = [
    { value: 'nutrition_label', label: '📋 Nutrition Label', desc: 'From packaged food' },
    { value: 'food_scale', label: '⚖️ Food Scale', desc: 'Weighed ingredients' },
    { value: 'recipe_calculation', label: '📝 Recipe Calculation', desc: 'Calculated from recipe' },
    { value: 'database', label: '🔍 Nutrition Database', desc: 'USDA, MyFitnessPal, etc.' },
];

export default function VerifyNutrition({ entryId, estimatedValues, onVerified, onCancel }: VerifyNutritionProps) {
    const [isExpanded, setIsExpanded] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [result, setResult] = useState<VerificationResult | null>(null);

    // Form state
    const [actualCalories, setActualCalories] = useState<string>(estimatedValues.calories.toString());
    const [actualProtein, setActualProtein] = useState<string>(estimatedValues.protein.toString());
    const [actualCarbs, setActualCarbs] = useState<string>(estimatedValues.carbs.toString());
    const [actualFat, setActualFat] = useState<string>(estimatedValues.fat.toString());
    const [verificationSource, setVerificationSource] = useState<string>('');
    const [notes, setNotes] = useState<string>('');

    const handleSubmit = async () => {
        if (!verificationSource) {
            alert('Please select a verification source');
            return;
        }

        setIsSubmitting(true);
        try {
            const response = await fetch(`${API_BASE_URL}/meals/${entryId}/verify`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    actual_calories: parseFloat(actualCalories) || null,
                    actual_protein: parseFloat(actualProtein) || null,
                    actual_carbs: parseFloat(actualCarbs) || null,
                    actual_fat: parseFloat(actualFat) || null,
                    verification_source: verificationSource,
                    notes: notes || null,
                }),
            });

            if (response.ok) {
                const data = await response.json();
                setResult(data);
                onVerified?.(data);
            } else {
                alert('Failed to verify nutrition data');
            }
        } catch (error) {
            console.error('Verification error:', error);
            alert('Error connecting to server');
        } finally {
            setIsSubmitting(false);
        }
    };

    const getErrorColor = (errorPercent: number | null | undefined) => {
        if (errorPercent === null || errorPercent === undefined) return 'text-gray-400';
        const absError = Math.abs(errorPercent);
        if (absError <= 5) return 'text-green-400';
        if (absError <= 15) return 'text-yellow-400';
        return 'text-red-400';
    };

    const formatError = (error: number | null | undefined, errorPercent: number | null | undefined) => {
        if (error === null || error === undefined) return '—';
        const sign = error > 0 ? '+' : '';
        return `${sign}${error.toFixed(0)} (${sign}${errorPercent?.toFixed(1)}%)`;
    };

    // If already verified, show result
    if (result) {
        return (
            <div className="mt-4 p-4 bg-green-500/10 border border-green-500/30 rounded-xl">
                <div className="flex items-center gap-2 mb-3">
                    <span className="text-lg">✅</span>
                    <span className="font-semibold text-green-400">Verification Submitted</span>
                </div>
                <p className="text-sm text-gray-300 mb-3">
                    Thanks! Your verified data helps improve our AI's accuracy.
                </p>

                <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                        <span className="text-gray-400">Calories Error:</span>
                        <span className={`ml-2 ${getErrorColor(result.comparison.calories?.error_percent)}`}>
                            {formatError(result.comparison.calories?.error, result.comparison.calories?.error_percent)}
                        </span>
                    </div>
                    {result.comparison.protein && (
                        <div>
                            <span className="text-gray-400">Protein Error:</span>
                            <span className={`ml-2 ${getErrorColor(result.comparison.protein?.error_percent)}`}>
                                {formatError(result.comparison.protein?.error, result.comparison.protein?.error_percent)}
                            </span>
                        </div>
                    )}
                </div>
            </div>
        );
    }

    return (
        <div className="mt-4">
            {!isExpanded ? (
                <button
                    onClick={() => setIsExpanded(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-purple-500/20 hover:bg-purple-500/30 border border-purple-500/30 rounded-lg transition-all text-sm"
                >
                    <span>📊</span>
                    <span>Verify Actual Nutrition</span>
                    <span className="text-xs text-gray-400">(Helps improve AI accuracy)</span>
                </button>
            ) : (
                <div className="p-4 bg-gray-800/50 border border-gray-700 rounded-xl">
                    <div className="flex justify-between items-center mb-4">
                        <h4 className="font-semibold text-purple-300">📊 Verify Nutrition Values</h4>
                        <button onClick={() => { setIsExpanded(false); onCancel?.(); }} className="text-gray-400 hover:text-white">
                            ✕
                        </button>
                    </div>

                    <p className="text-sm text-gray-400 mb-4">
                        Enter the actual nutrition values to help calibrate our estimates.
                    </p>

                    {/* Verification Source */}
                    <div className="mb-4">
                        <label className="block text-sm text-gray-300 mb-2">How did you verify? *</label>
                        <div className="grid grid-cols-2 gap-2">
                            {VERIFICATION_SOURCES.map(source => (
                                <button
                                    key={source.value}
                                    onClick={() => setVerificationSource(source.value)}
                                    className={`p-2 rounded-lg text-left text-sm transition-all ${verificationSource === source.value
                                        ? 'bg-purple-500/30 border-purple-500'
                                        : 'bg-gray-700/50 hover:bg-gray-700 border-gray-600'
                                        } border`}
                                >
                                    <div className="font-medium">{source.label}</div>
                                    <div className="text-xs text-gray-400">{source.desc}</div>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Nutrient Inputs */}
                    <div className="grid grid-cols-2 gap-3 mb-4">
                        <div>
                            <label className="block text-xs text-gray-400 mb-1">Calories (kcal)</label>
                            <div className="flex items-center gap-2">
                                <span className="text-xs text-gray-500">Est: {estimatedValues.calories}</span>
                                <input
                                    type="number"
                                    value={actualCalories}
                                    onChange={(e) => setActualCalories(e.target.value)}
                                    className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:border-purple-500 focus:outline-none"
                                    placeholder="Actual"
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-xs text-gray-400 mb-1">Protein (g)</label>
                            <div className="flex items-center gap-2">
                                <span className="text-xs text-gray-500">Est: {estimatedValues.protein}g</span>
                                <input
                                    type="number"
                                    value={actualProtein}
                                    onChange={(e) => setActualProtein(e.target.value)}
                                    className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:border-purple-500 focus:outline-none"
                                    placeholder="Actual"
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-xs text-gray-400 mb-1">Carbs (g)</label>
                            <div className="flex items-center gap-2">
                                <span className="text-xs text-gray-500">Est: {estimatedValues.carbs}g</span>
                                <input
                                    type="number"
                                    value={actualCarbs}
                                    onChange={(e) => setActualCarbs(e.target.value)}
                                    className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:border-purple-500 focus:outline-none"
                                    placeholder="Actual"
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-xs text-gray-400 mb-1">Fat (g)</label>
                            <div className="flex items-center gap-2">
                                <span className="text-xs text-gray-500">Est: {estimatedValues.fat}g</span>
                                <input
                                    type="number"
                                    value={actualFat}
                                    onChange={(e) => setActualFat(e.target.value)}
                                    className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:border-purple-500 focus:outline-none"
                                    placeholder="Actual"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Notes */}
                    <div className="mb-4">
                        <label className="block text-xs text-gray-400 mb-1">Notes (optional)</label>
                        <input
                            type="text"
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:border-purple-500 focus:outline-none"
                            placeholder="e.g., Homemade recipe, restaurant portion, etc."
                        />
                    </div>

                    {/* Submit */}
                    <div className="flex gap-2">
                        <button
                            onClick={handleSubmit}
                            disabled={isSubmitting || !verificationSource}
                            className={`flex-1 py-2 rounded-lg font-medium transition-all ${isSubmitting || !verificationSource
                                ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
                                : 'bg-purple-600 hover:bg-purple-500 text-white'
                                }`}
                        >
                            {isSubmitting ? '⏳ Submitting...' : '✅ Submit Verification'}
                        </button>
                        <button
                            onClick={() => setIsExpanded(false)}
                            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-gray-300 transition-all"
                        >
                            Cancel
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
