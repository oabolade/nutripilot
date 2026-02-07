'use client';

import { useState, useEffect } from 'react';

interface DashboardData {
    user_id: string;
    profile: {
        display_name: string | null;
        goals: string[];
        conditions: string[];
        daily_targets: {
            calories: number;
            protein_g: number;
            carbs_g: number;
            fiber_g: number;
        };
        timeline_weeks: number;
        start_date: string;
    } | null;
    days_active: number;
    meals_logged: number;
    average_meal_score: number;
    average_goal_alignment: number;
    goal_progress: Record<string, number>;
    nutrient_trends: Record<string, { average: number; target: number; percent: number }>;
    recent_meals: Array<{
        entry_id: string;
        timestamp: string;
        meal_type: string;
        food_names: string[];
        meal_score: number;
        goal_alignment_score: number;
    }>;
}

interface DashboardProps {
    userId: string;
    isOpen: boolean;
    onClose: () => void;
    onEditGoals: () => void;
    onResetProfile?: () => void;  // Called after profile is successfully deleted
}

export default function Dashboard({ userId, isOpen, onClose, onEditGoals, onResetProfile }: DashboardProps) {
    const [data, setData] = useState<DashboardData | null>(null);
    const [loading, setLoading] = useState(true);
    const [resetting, setResetting] = useState(false);
    const [showResetConfirm, setShowResetConfirm] = useState(false);

    const handleResetProfile = async () => {
        setResetting(true);
        try {
            const res = await fetch(`http://localhost:8000/users/${userId}/profile`, {
                method: 'DELETE',
            });

            if (res.ok) {
                setData(null);
                setShowResetConfirm(false);
                onResetProfile?.();
                onClose();
            } else {
                alert('Failed to reset profile');
            }
        } catch (err) {
            console.error('Reset failed:', err);
            alert('Failed to reset profile');
        } finally {
            setResetting(false);
        }
    };

    useEffect(() => {
        if (isOpen) {
            setLoading(true);
            fetch(`http://localhost:8000/users/${userId}/dashboard`)
                .then(res => res.json())
                .then(setData)
                .catch(err => console.error('Failed to fetch dashboard:', err))
                .finally(() => setLoading(false));
        }
    }, [isOpen, userId]);

    if (!isOpen) return null;

    const formatGoalLabel = (goal: string) => goal.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
            <div className="w-full max-w-4xl max-h-[90vh] bg-[#0a0a0f] border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
                {/* Header */}
                <div className="p-6 border-b border-white/10 flex-shrink-0">
                    <div className="flex items-center justify-between">
                        <div>
                            <h2 className="text-xl font-bold text-white">Your Progress Dashboard</h2>
                            {data?.profile?.display_name && (
                                <p className="text-sm text-gray-400 mt-1">Welcome back, {data.profile.display_name}!</p>
                            )}
                        </div>
                        <div className="flex items-center gap-3">
                            <button
                                onClick={onEditGoals}
                                className="px-4 py-2 text-sm bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-gray-300 transition-colors"
                            >
                                Edit Goals
                            </button>
                            <button
                                onClick={() => setShowResetConfirm(true)}
                                disabled={resetting}
                                className="px-4 py-2 text-sm bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 rounded-lg text-red-400 transition-colors disabled:opacity-50"
                            >
                                {resetting ? 'Resetting...' : '🗑️ Reset'}
                            </button>
                            <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-lg transition-colors">
                                <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6">
                    {loading ? (
                        <div className="flex items-center justify-center h-64">
                            <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
                        </div>
                    ) : !data?.profile ? (
                        <div className="text-center py-12">
                            <p className="text-gray-400 mb-4">No profile set up yet.</p>
                            <button
                                onClick={onEditGoals}
                                className="px-6 py-3 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg font-medium transition-colors"
                            >
                                Set Up Your Goals
                            </button>
                        </div>
                    ) : (
                        <div className="space-y-6">
                            {/* Stats Row */}
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                <StatCard
                                    label="Days Active"
                                    value={data.days_active}
                                    icon="📅"
                                />
                                <StatCard
                                    label="Meals Logged"
                                    value={data.meals_logged}
                                    icon="🍽️"
                                />
                                <StatCard
                                    label="Avg Meal Score"
                                    value={`${data.average_meal_score.toFixed(0)}%`}
                                    icon="⭐"
                                    color="emerald"
                                />
                                <StatCard
                                    label="Goal Alignment"
                                    value={`${data.average_goal_alignment.toFixed(0)}%`}
                                    icon="🎯"
                                    color="amber"
                                />
                            </div>

                            {/* Goal Progress */}
                            {Object.keys(data.goal_progress).length > 0 && (
                                <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                                    <h3 className="text-sm font-semibold text-white mb-4">Goal Progress</h3>
                                    <div className="space-y-4">
                                        {Object.entries(data.goal_progress).map(([goal, progress]) => (
                                            <div key={goal}>
                                                <div className="flex justify-between text-sm mb-1">
                                                    <span className="text-gray-300">{formatGoalLabel(goal)}</span>
                                                    <span className="text-emerald-400">{progress.toFixed(0)}%</span>
                                                </div>
                                                <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                                                    <div
                                                        className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400 rounded-full transition-all duration-500"
                                                        style={{ width: `${Math.min(100, progress)}%` }}
                                                    />
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Nutrient Trends */}
                            {Object.keys(data.nutrient_trends).length > 0 && (
                                <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                                    <h3 className="text-sm font-semibold text-white mb-4">Daily Nutrient Intake (7-day avg)</h3>
                                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                                        {Object.entries(data.nutrient_trends).slice(0, 6).map(([nutrient, trend]) => (
                                            <NutrientCard key={nutrient} nutrient={nutrient} trend={trend} />
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Recent Meals */}
                            {data.recent_meals.length > 0 && (
                                <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                                    <h3 className="text-sm font-semibold text-white mb-4">Recent Meals</h3>
                                    <div className="space-y-3">
                                        {data.recent_meals.slice(0, 5).map(meal => (
                                            <div
                                                key={meal.entry_id}
                                                className="flex items-center justify-between p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
                                            >
                                                <div className="flex-1">
                                                    <div className="flex items-center gap-2">
                                                        <span className="text-xs px-2 py-0.5 bg-white/10 rounded text-gray-400 capitalize">
                                                            {meal.meal_type}
                                                        </span>
                                                        <span className="text-xs text-gray-500">
                                                            {new Date(meal.timestamp).toLocaleDateString()}
                                                        </span>
                                                    </div>
                                                    <p className="text-sm text-white mt-1 truncate">
                                                        {meal.food_names.slice(0, 3).join(', ')}
                                                        {meal.food_names.length > 3 && ` +${meal.food_names.length - 3} more`}
                                                    </p>
                                                </div>
                                                <div className="flex items-center gap-4">
                                                    <div className="text-right">
                                                        <p className="text-xs text-gray-500">Score</p>
                                                        <p className={`text-sm font-medium ${meal.meal_score >= 70 ? 'text-emerald-400' : meal.meal_score >= 50 ? 'text-amber-400' : 'text-red-400'}`}>
                                                            {meal.meal_score.toFixed(0)}%
                                                        </p>
                                                    </div>
                                                    <div className="text-right">
                                                        <p className="text-xs text-gray-500">Goals</p>
                                                        <p className={`text-sm font-medium ${meal.goal_alignment_score >= 70 ? 'text-emerald-400' : meal.goal_alignment_score >= 50 ? 'text-amber-400' : 'text-red-400'}`}>
                                                            {meal.goal_alignment_score.toFixed(0)}%
                                                        </p>
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Active Goals */}
                            <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                                <h3 className="text-sm font-semibold text-white mb-3">Active Goals & Conditions</h3>
                                <div className="flex flex-wrap gap-2">
                                    {data.profile.goals.map(goal => (
                                        <span key={goal} className="px-3 py-1 text-xs rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                                            🎯 {formatGoalLabel(goal)}
                                        </span>
                                    ))}
                                    {data.profile.conditions.filter(c => c !== 'none').map(cond => (
                                        <span key={cond} className="px-3 py-1 text-xs rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30">
                                            ⚠️ {formatGoalLabel(cond)}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Reset Confirmation Modal */}
            {showResetConfirm && (
                <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/80">
                    <div className="w-full max-w-md bg-zinc-900 border border-white/10 rounded-xl p-6 shadow-2xl">
                        <h3 className="text-lg font-bold text-white mb-2">🚨 Reset All Data?</h3>
                        <p className="text-gray-400 mb-6">
                            This will delete your profile, goals, and all meal history. This action cannot be undone.
                        </p>
                        <div className="flex gap-3 justify-end">
                            <button
                                onClick={() => setShowResetConfirm(false)}
                                className="px-4 py-2 text-sm bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-gray-300 transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleResetProfile}
                                disabled={resetting}
                                className="px-4 py-2 text-sm bg-red-500 hover:bg-red-600 rounded-lg text-white font-medium transition-colors disabled:opacity-50"
                            >
                                {resetting ? 'Resetting...' : 'Yes, Reset Everything'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

function StatCard({ label, value, icon, color = 'white' }: { label: string; value: string | number; icon: string; color?: string }) {
    const colorClass = color === 'emerald' ? 'text-emerald-400' : color === 'amber' ? 'text-amber-400' : 'text-white';

    return (
        <div className="p-4 rounded-xl bg-white/5 border border-white/10">
            <div className="flex items-center gap-2 mb-2">
                <span className="text-lg">{icon}</span>
                <span className="text-xs text-gray-500">{label}</span>
            </div>
            <p className={`text-2xl font-bold ${colorClass}`}>{value}</p>
        </div>
    );
}

function NutrientCard({ nutrient, trend }: { nutrient: string; trend: { average: number; target: number; percent: number } }) {
    const isOver = trend.percent > 100;
    const colorClass = isOver ? 'text-amber-400' : 'text-emerald-400';
    const unit = nutrient === 'calories' ? 'kcal' : nutrient === 'sodium' ? 'mg' : 'g';

    return (
        <div className="p-3 rounded-lg bg-white/5">
            <p className="text-xs text-gray-500 capitalize mb-1">{nutrient}</p>
            <p className={`text-lg font-semibold ${colorClass}`}>
                {trend.average.toFixed(0)}<span className="text-xs text-gray-500">/{trend.target}{unit}</span>
            </p>
            <p className="text-xs text-gray-500">{trend.percent.toFixed(0)}% of target</p>
        </div>
    );
}
