// Type definitions for NutriPilot meal analysis

export interface NutrientInfo {
    name: string;
    amount: number;
    unit: string;
    percentDaily?: number;
}

export interface FoodItem {
    name: string;
    portionGrams: number;
    portionDescription: string;
    confidence: number;
    nutrients: NutrientInfo[];
    usdaFdcId?: string;
    boundingBox?: {
        x1: number;
        y1: number;
        x2: number;
        y2: number;
    };
}

export type ConstraintStatus = "normal" | "warning" | "critical";

export interface HealthConstraint {
    constraintType: string;
    value: number;
    unit: string;
    status: ConstraintStatus;
    thresholdLow?: number;
    thresholdHigh?: number;
    recommendation?: string;
}

export type AdjustmentAction = "reduce" | "replace" | "remove" | "add";

export interface MealAdjustment {
    foodName: string;
    action: AdjustmentAction;
    reason: string;
    alternative?: string;
    priority: number;
}

export interface MealAnalysis {
    sessionId: string;
    timestamp: string;
    mealType?: "breakfast" | "lunch" | "dinner" | "snack";
    overallScore: number;
    imageAnalysisConfidence: number;
    detectedFoods: FoodItem[];
    totalNutrients: NutrientInfo[];
    healthConstraints: HealthConstraint[];
    adjustments: MealAdjustment[];
    summary: string;
}
