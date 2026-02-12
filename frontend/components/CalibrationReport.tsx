'use client';

import { useState } from 'react';
import { API_BASE_URL } from '@/lib/api';

interface CalibrationMetrics {
    mean_absolute_error: number;
    mean_absolute_percentage_error: number;
    root_mean_squared_error: number;
    brier_score?: number;
    pearson_correlation?: number;
    r_squared?: number;
    bias?: number;
    std_deviation?: number;
}

interface PromptSuggestion {
    category: string;
    current_issue: string;
    suggested_change: string;
    priority: number;
    expected_impact: string;
}

interface MealCalibrationData {
    entry_id: string;
    timestamp: string;
    food_names: string[];
    estimated_calories: number;
    actual_calories: number;
    error: number;
    percentage_error: number;
}

interface CalibrationReportData {
    report_id: string;
    user_id: string;
    meals_analyzed: number;
    status: 'excellent' | 'good' | 'needs_improvement' | 'poor';
    status_message: string;
    metrics: CalibrationMetrics;
    overestimation_count?: number;
    underestimation_count?: number;
    accurate_count?: number;
    worst_categories?: string[];
    suggestions: PromptSuggestion[];
    data_points?: MealCalibrationData[];
}

interface CalibrationReportProps {
    userId: string;
    isOpen: boolean;
    onClose: () => void;
}

export default function CalibrationReport({ userId, isOpen, onClose }: CalibrationReportProps) {
    const [report, setReport] = useState<CalibrationReportData | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [limit, setLimit] = useState(25);

    const runCalibration = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(`${API_BASE_URL}/calibrate/${userId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                },
                body: JSON.stringify({ limit }),
                cache: 'no-store',
            });

            if (!res.ok) {
                throw new Error('Failed to run calibration');
            }

            const data = await res.json();
            console.log('📊 Calibration response:', data);
            console.log(`   meals_analyzed: ${data.meals_analyzed}, status: ${data.status}`);
            setReport(data);
        } catch (err) {
            console.error('Calibration failed:', err);
            setError('Failed to run calibration. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'excellent': return 'text-emerald-400';
            case 'good': return 'text-green-400';
            case 'needs_improvement': return 'text-amber-400';
            case 'poor': return 'text-red-400';
            default: return 'text-gray-400';
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'excellent': return '🌟';
            case 'good': return '✅';
            case 'needs_improvement': return '⚠️';
            case 'poor': return '🔴';
            default: return '📊';
        }
    };

    const formatCategory = (category: string) =>
        category.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
            <div className="w-full max-w-4xl max-h-[90vh] bg-[#0a0a0f] border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
                {/* Header */}
                <div className="p-6 border-b border-white/10 flex-shrink-0">
                    <div className="flex items-center justify-between">
                        <div>
                            <h2 className="text-xl font-bold text-white flex items-center gap-2">
                                🔬 Calibration Report
                            </h2>
                            <p className="text-sm text-gray-400 mt-1">
                                Analyze estimation accuracy against verified meals
                            </p>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-2 text-gray-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6 space-y-6">
                    {/* Run Calibration Controls */}
                    {!report && (
                        <div className="bg-gradient-to-br from-purple-500/10 to-blue-500/10 border border-purple-500/20 rounded-xl p-6">
                            <div className="flex items-center gap-3 mb-4">
                                <h3 className="text-lg font-semibold text-white">Run Calibration Analysis</h3>
                                <span className="px-2 py-0.5 text-xs bg-purple-500/20 text-purple-300 rounded-full flex items-center gap-1">
                                    📡 Opik Traces
                                </span>
                            </div>
                            <p className="text-gray-400 text-sm mb-4">
                                Fetches meal analysis traces from <strong className="text-purple-300">Opik</strong> to compare Gemini's calorie estimates against verified data. Generates accuracy metrics and prompt improvement suggestions.
                            </p>

                            <div className="flex items-center gap-4 mb-4">
                                <label className="text-sm text-gray-300">Meals to analyze:</label>
                                <select
                                    value={limit}
                                    onChange={(e) => setLimit(Number(e.target.value))}
                                    className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm"
                                >
                                    <option value={25}>Last 25 meals (recommended)</option>
                                    <option value={50}>Last 50 meals</option>
                                    <option value={100}>Last 100 meals</option>
                                    <option value={10}>Last 10 meals</option>
                                </select>
                            </div>

                            <button
                                onClick={runCalibration}
                                disabled={loading}
                                className="px-6 py-3 bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600 text-white font-semibold rounded-lg transition-all disabled:opacity-50"
                            >
                                {loading ? (
                                    <span className="flex items-center gap-2">
                                        <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                        </svg>
                                        Analyzing...
                                    </span>
                                ) : 'Run Calibration'}
                            </button>

                            {error && (
                                <p className="mt-3 text-red-400 text-sm">{error}</p>
                            )}
                        </div>
                    )}

                    {/* Report Results */}
                    {report && (
                        <>
                            {/* Status Banner */}
                            <div className={`rounded-xl p-4 border ${report.status === 'excellent' ? 'bg-emerald-500/10 border-emerald-500/30' :
                                report.status === 'good' ? 'bg-green-500/10 border-green-500/30' :
                                    report.status === 'needs_improvement' ? 'bg-amber-500/10 border-amber-500/30' :
                                        'bg-red-500/10 border-red-500/30'
                                }`}>
                                <div className="flex items-center gap-3">
                                    <span className="text-2xl">{getStatusIcon(report.status)}</span>
                                    <div>
                                        <h3 className={`font-semibold ${getStatusColor(report.status)}`}>
                                            {formatCategory(report.status)}
                                        </h3>
                                        <p className="text-gray-300 text-sm">{report.status_message}</p>
                                    </div>
                                </div>
                            </div>

                            {/* Metrics Grid */}
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                <div className="bg-white/5 border border-white/10 rounded-xl p-4 text-center">
                                    <p className="text-gray-400 text-xs uppercase mb-1">Meals Analyzed</p>
                                    <p className="text-2xl font-bold text-white">{report.meals_analyzed}</p>
                                </div>

                                <div className="bg-white/5 border border-white/10 rounded-xl p-4 text-center">
                                    <p className="text-gray-400 text-xs uppercase mb-1">Avg Error</p>
                                    <p className="text-2xl font-bold text-white">
                                        {report.metrics.mean_absolute_error.toFixed(0)}
                                        <span className="text-sm text-gray-400 ml-1">cal</span>
                                    </p>
                                </div>

                                <div className="bg-white/5 border border-white/10 rounded-xl p-4 text-center">
                                    <p className="text-gray-400 text-xs uppercase mb-1">MAPE</p>
                                    <p className={`text-2xl font-bold ${report.metrics.mean_absolute_percentage_error < 10 ? 'text-green-400' :
                                        report.metrics.mean_absolute_percentage_error < 15 ? 'text-amber-400' :
                                            'text-red-400'
                                        }`}>
                                        {report.metrics.mean_absolute_percentage_error.toFixed(1)}%
                                    </p>
                                </div>

                                <div className="bg-white/5 border border-white/10 rounded-xl p-4 text-center">
                                    <p className="text-gray-400 text-xs uppercase mb-1">Correlation</p>
                                    <p className="text-2xl font-bold text-white">
                                        {report.metrics.pearson_correlation?.toFixed(2) || 'N/A'}
                                    </p>
                                </div>
                            </div>

                            {/* Error Distribution */}
                            {(report.overestimation_count !== undefined || report.underestimation_count !== undefined) && (
                                <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                                    <h4 className="text-white font-semibold mb-3">Error Distribution</h4>
                                    <div className="flex items-center gap-4">
                                        <div className="flex-1">
                                            <div className="flex justify-between text-sm mb-1">
                                                <span className="text-red-400">Overestimated</span>
                                                <span className="text-gray-400">{report.overestimation_count || 0}</span>
                                            </div>
                                            <div className="h-2 bg-red-500/20 rounded-full overflow-hidden">
                                                <div
                                                    className="h-full bg-red-500 rounded-full"
                                                    style={{ width: `${((report.overestimation_count || 0) / report.meals_analyzed) * 100}%` }}
                                                />
                                            </div>
                                        </div>
                                        <div className="flex-1">
                                            <div className="flex justify-between text-sm mb-1">
                                                <span className="text-green-400">Accurate (±5%)</span>
                                                <span className="text-gray-400">{report.accurate_count || 0}</span>
                                            </div>
                                            <div className="h-2 bg-green-500/20 rounded-full overflow-hidden">
                                                <div
                                                    className="h-full bg-green-500 rounded-full"
                                                    style={{ width: `${((report.accurate_count || 0) / report.meals_analyzed) * 100}%` }}
                                                />
                                            </div>
                                        </div>
                                        <div className="flex-1">
                                            <div className="flex justify-between text-sm mb-1">
                                                <span className="text-blue-400">Underestimated</span>
                                                <span className="text-gray-400">{report.underestimation_count || 0}</span>
                                            </div>
                                            <div className="h-2 bg-blue-500/20 rounded-full overflow-hidden">
                                                <div
                                                    className="h-full bg-blue-500 rounded-full"
                                                    style={{ width: `${((report.underestimation_count || 0) / report.meals_analyzed) * 100}%` }}
                                                />
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Worst Categories */}
                            {report.worst_categories && report.worst_categories.length > 0 && (
                                <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4">
                                    <h4 className="text-amber-400 font-semibold mb-2 flex items-center gap-2">
                                        <span>⚠️</span> Categories Needing Attention
                                    </h4>
                                    <div className="flex flex-wrap gap-2">
                                        {report.worst_categories.map((cat, i) => (
                                            <span key={i} className="px-3 py-1 bg-amber-500/20 text-amber-300 text-sm rounded-full">
                                                {formatCategory(cat)}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Suggestions */}
                            {report.suggestions.length > 0 && (
                                <div className="space-y-3">
                                    <h4 className="text-white font-semibold">Prompt Improvement Suggestions</h4>
                                    {report.suggestions.map((suggestion, i) => (
                                        <div key={i} className="bg-white/5 border border-white/10 rounded-xl p-4">
                                            <div className="flex items-start gap-3">
                                                <span className={`px-2 py-0.5 text-xs rounded ${suggestion.priority === 1 ? 'bg-red-500/20 text-red-400' :
                                                    suggestion.priority === 2 ? 'bg-amber-500/20 text-amber-400' :
                                                        'bg-blue-500/20 text-blue-400'
                                                    }`}>
                                                    P{suggestion.priority}
                                                </span>
                                                <div className="flex-1">
                                                    <p className="text-gray-400 text-sm mb-2">
                                                        <strong className="text-gray-300">Issue:</strong> {suggestion.current_issue}
                                                    </p>
                                                    <p className="text-white text-sm mb-2">
                                                        <strong className="text-emerald-400">Suggestion:</strong> {suggestion.suggested_change}
                                                    </p>
                                                    <p className="text-gray-500 text-xs">
                                                        Expected Impact: {suggestion.expected_impact}
                                                    </p>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Sample Data Points */}
                            {report.data_points && report.data_points.length > 0 && (
                                <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                                    <h4 className="text-white font-semibold mb-3">Sample Data Points</h4>
                                    <div className="overflow-x-auto">
                                        <table className="w-full text-sm">
                                            <thead>
                                                <tr className="text-gray-400 border-b border-white/10">
                                                    <th className="text-left py-2 px-2">Foods</th>
                                                    <th className="text-right py-2 px-2">Estimated</th>
                                                    <th className="text-right py-2 px-2">Actual</th>
                                                    <th className="text-right py-2 px-2">Error</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {report.data_points.slice(0, 5).map((point, i) => (
                                                    <tr key={i} className="border-b border-white/5">
                                                        <td className="py-2 px-2 text-gray-300">
                                                            {point.food_names.slice(0, 2).join(', ')}
                                                            {point.food_names.length > 2 && '...'}
                                                        </td>
                                                        <td className="py-2 px-2 text-right text-white">
                                                            {point.estimated_calories.toFixed(0)} cal
                                                        </td>
                                                        <td className="py-2 px-2 text-right text-white">
                                                            {point.actual_calories.toFixed(0)} cal
                                                        </td>
                                                        <td className={`py-2 px-2 text-right ${point.error > 0 ? 'text-red-400' : 'text-blue-400'
                                                            }`}>
                                                            {point.error > 0 ? '+' : ''}{point.error.toFixed(0)}
                                                            <span className="text-gray-500 ml-1">
                                                                ({point.percentage_error.toFixed(1)}%)
                                                            </span>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            )}

                            {/* Run Again Button */}
                            <div className="flex justify-center">
                                <button
                                    onClick={() => setReport(null)}
                                    className="px-4 py-2 text-sm bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-gray-300 transition-colors"
                                >
                                    ← Run New Analysis
                                </button>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
