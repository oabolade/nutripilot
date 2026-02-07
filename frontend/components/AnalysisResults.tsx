"use client";

import { MealAnalysis } from "@/types/meal";
import VerifyNutrition from "./VerifyNutrition";

interface AnalysisResultsProps {
    analysis: MealAnalysis;
}

export default function AnalysisResults({ analysis }: AnalysisResultsProps) {
    const getScoreColor = (score: number) => {
        if (score >= 80) return "text-emerald-400";
        if (score >= 60) return "text-yellow-400";
        return "text-rose-400";
    };

    const getConfidenceLabel = (confidence: number) => {
        if (confidence >= 0.9) return { label: "High", color: "text-emerald-400" };
        if (confidence >= 0.7) return { label: "Medium", color: "text-yellow-400" };
        return { label: "Low", color: "text-rose-400" };
    };

    // Extract estimated values for verification
    const getEstimatedValues = () => {
        const nutrients = analysis.totalNutrients;
        return {
            calories: nutrients.find(n => n.name === "calories")?.amount || 0,
            protein: nutrients.find(n => n.name === "protein")?.amount || 0,
            carbs: nutrients.find(n => n.name === "carbohydrates")?.amount || 0,
            fat: nutrients.find(n => n.name === "fat")?.amount || 0,
            fiber: nutrients.find(n => n.name === "fiber")?.amount,
            sodium: nutrients.find(n => n.name === "sodium")?.amount,
        };
    };

    return (
        <div className="space-y-6 stagger-animation">
            {/* Score and Summary */}
            <div className="flex items-start gap-6">
                {/* Score Ring */}
                <div
                    className="score-ring shrink-0"
                    style={{ "--score": analysis.overallScore } as React.CSSProperties}
                >
                    <span className={`score-value ${getScoreColor(analysis.overallScore)}`}>
                        {analysis.overallScore}
                    </span>
                </div>

                <div className="flex-1">
                    <h3 className="text-lg font-semibold mb-2">Meal Score</h3>
                    <p className="text-sm text-zinc-400 leading-relaxed">
                        {analysis.summary}
                    </p>
                </div>
            </div>

            {/* Detected Foods */}
            <div>
                <h4 className="text-sm font-medium text-zinc-400 uppercase tracking-wider mb-3">
                    Detected Foods ({analysis.detectedFoods.length})
                </h4>
                <div className="space-y-2">
                    {analysis.detectedFoods.map((food, index) => {
                        const conf = getConfidenceLabel(food.confidence);
                        return (
                            <div key={index} className="food-item-card">
                                <div className="flex items-start justify-between mb-2">
                                    <div>
                                        <span className="font-medium">{food.name}</span>
                                        <span className="text-sm text-zinc-500 ml-2">
                                            {food.portionDescription}
                                        </span>
                                    </div>
                                    <span className={`text-xs ${conf.color}`}>
                                        {Math.round(food.confidence * 100)}% {conf.label}
                                    </span>
                                </div>
                                <div className="flex flex-wrap gap-2">
                                    {food.nutrients.slice(0, 3).map((nutrient, nIndex) => (
                                        <span
                                            key={nIndex}
                                            className="text-xs px-2 py-1 rounded-md bg-white/5 text-zinc-400"
                                        >
                                            {nutrient.name}: {nutrient.amount}{nutrient.unit}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Nutrient Totals */}
            <div>
                <h4 className="text-sm font-medium text-zinc-400 uppercase tracking-wider mb-3">
                    Nutritional Breakdown
                </h4>
                <div className="grid grid-cols-2 gap-3">
                    {analysis.totalNutrients.slice(0, 6).map((nutrient, index) => (
                        <div key={index} className="space-y-1">
                            <div className="flex justify-between text-sm">
                                <span className="text-zinc-400">{nutrient.name}</span>
                                <span className="font-medium">
                                    {nutrient.amount}{nutrient.unit}
                                </span>
                            </div>
                            <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                                <div
                                    className="nutrient-bar"
                                    style={{
                                        width: `${Math.min(nutrient.percentDaily || 0, 100)}%`
                                    }}
                                />
                            </div>
                            <div className="text-xs text-zinc-500 text-right">
                                {nutrient.percentDaily}% DV
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Health Insights */}
            {analysis.healthConstraints.length > 0 && (
                <div>
                    <h4 className="text-sm font-medium text-zinc-400 uppercase tracking-wider mb-3">
                        Health Insights
                    </h4>
                    {analysis.healthConstraints.map((constraint, index) => (
                        <div
                            key={index}
                            className={`p-4 rounded-xl border ${constraint.status === "normal"
                                ? "bg-emerald-500/10 border-emerald-500/20"
                                : constraint.status === "warning"
                                    ? "bg-yellow-500/10 border-yellow-500/20"
                                    : "bg-rose-500/10 border-rose-500/20"
                                }`}
                        >
                            <div className="flex items-center gap-2 mb-1">
                                <span className="text-lg">
                                    {constraint.status === "normal" ? "✅" : constraint.status === "warning" ? "⚠️" : "🚨"}
                                </span>
                                <span className="font-medium capitalize">
                                    {constraint.constraintType.replace("_", " ")}
                                </span>
                                <span className="text-sm text-zinc-400">
                                    {constraint.value} {constraint.unit}
                                </span>
                            </div>
                            {constraint.recommendation && (
                                <p className="text-sm text-zinc-400 ml-7">
                                    {constraint.recommendation}
                                </p>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {/* Adjustments */}
            {analysis.adjustments.length > 0 && (
                <div>
                    <h4 className="text-sm font-medium text-zinc-400 uppercase tracking-wider mb-3">
                        Suggested Adjustments
                    </h4>
                    <div className="space-y-2">
                        {analysis.adjustments.map((adj, index) => (
                            <div
                                key={index}
                                className="flex items-start gap-3 p-3 rounded-xl bg-white/5"
                            >
                                <span className="text-lg shrink-0">
                                    {adj.action === "reduce" ? "📉" :
                                        adj.action === "replace" ? "🔄" :
                                            adj.action === "remove" ? "❌" : "➕"}
                                </span>
                                <div>
                                    <p className="font-medium">
                                        <span className="capitalize">{adj.action}</span> {adj.foodName}
                                    </p>
                                    <p className="text-sm text-zinc-400">{adj.reason}</p>
                                    {adj.alternative && (
                                        <p className="text-sm text-emerald-400 mt-1">
                                            Try: {adj.alternative}
                                        </p>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Verify Nutrition - for building ground truth dataset */}
            {analysis.entryId && (
                <VerifyNutrition
                    entryId={analysis.entryId}
                    estimatedValues={getEstimatedValues()}
                    onVerified={(result) => {
                        console.log("Verification submitted:", result);
                    }}
                />
            )}
        </div>
    );
}

