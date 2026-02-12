/**
 * NutriPilot API Client
 * 
 * Connects the frontend to the Python backend API for meal analysis.
 */

import { MealAnalysis, FoodItem, NutrientInfo, HealthConstraint, MealAdjustment } from "@/types/meal";

// Backend API URL - use environment variable or default to localhost
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Backend API response types (matching Python Pydantic models)
 */
interface BackendNutrientInfo {
    name: string;
    amount: number;
    unit: string;
    percent_daily?: number;
}

interface BackendFoodItem {
    name: string;
    portion_grams: number;
    portion_description: string;
    confidence: number;
    nutrients: BackendNutrientInfo[];
    bounding_box?: {
        x1: number;
        y1: number;
        x2: number;
        y2: number;
    };
}

interface BackendHealthConstraint {
    type: string;
    value: number;
    unit: string;
    status: "normal" | "warning" | "critical";
    recommendation?: string;
}

interface BackendAdjustment {
    food: string;
    action: "reduce" | "replace" | "remove" | "add";
    reason: string;
    alternative?: string;
}

interface BackendAnalysisResponse {
    session_id: string;
    detected_foods: BackendFoodItem[];
    total_nutrients: Record<string, { amount: number; unit: string }>;
    health_insights: {
        constraints: BackendHealthConstraint[];
        violations: string[];
    };
    meal_score: number;
    summary: string;
    adjustments: BackendAdjustment[];
    processing_time_ms: number;
    entry_id?: string;  // ID for meal verification
    goal_alignment?: number;
    goal_feedback?: string[];
}

/**
 * Map backend nutrient to frontend format
 */
function mapNutrient(nutrient: BackendNutrientInfo): NutrientInfo {
    // Calculate percent daily value for common nutrients
    const dailyValues: Record<string, number> = {
        calories: 2000,
        protein: 50,
        carbohydrates: 275,
        fat: 78,
        fiber: 28,
        sodium: 2300,
        sugar: 50,
        vitamin_c: 90,
        calcium: 1300,
        iron: 18,
    };

    const percentDaily = dailyValues[nutrient.name.toLowerCase()]
        ? Math.round((nutrient.amount / dailyValues[nutrient.name.toLowerCase()]) * 100)
        : undefined;

    return {
        name: nutrient.name.charAt(0).toUpperCase() + nutrient.name.slice(1),
        amount: nutrient.amount,
        unit: nutrient.unit,
        percentDaily,
    };
}

/**
 * Map backend food item to frontend format
 */
function mapFoodItem(food: BackendFoodItem): FoodItem {
    return {
        name: food.name,
        portionGrams: food.portion_grams,
        portionDescription: food.portion_description,
        confidence: food.confidence,
        nutrients: food.nutrients.map(mapNutrient),
        boundingBox: food.bounding_box,
    };
}

/**
 * Map backend health constraint to frontend format
 */
function mapHealthConstraint(constraint: BackendHealthConstraint): HealthConstraint {
    return {
        constraintType: constraint.type,
        value: constraint.value,
        unit: constraint.unit,
        status: constraint.status,
        recommendation: constraint.recommendation,
    };
}

/**
 * Map backend adjustment to frontend format
 */
function mapAdjustment(adjustment: BackendAdjustment, index: number): MealAdjustment {
    return {
        foodName: adjustment.food,
        action: adjustment.action,
        reason: adjustment.reason,
        alternative: adjustment.alternative,
        priority: index + 1,
    };
}

/**
 * Map backend total nutrients to frontend format
 */
function mapTotalNutrients(
    totals: Record<string, { amount: number; unit: string }>
): NutrientInfo[] {
    const dailyValues: Record<string, number> = {
        calories: 2000,
        protein: 50,
        carbohydrates: 275,
        fat: 78,
        fiber: 28,
        sodium: 2300,
        sugar: 50,
        vitamin_c: 90,
        calcium: 1300,
        iron: 18,
    };

    return Object.entries(totals).map(([name, data]) => ({
        name: name.charAt(0).toUpperCase() + name.slice(1),
        amount: data.amount,
        unit: data.unit,
        percentDaily: dailyValues[name.toLowerCase()]
            ? Math.round((data.amount / dailyValues[name.toLowerCase()]) * 100)
            : undefined,
    }));
}

/**
 * Convert backend response to frontend MealAnalysis
 */
function mapBackendResponse(response: BackendAnalysisResponse): MealAnalysis {
    return {
        sessionId: response.session_id,
        timestamp: new Date().toISOString(),
        overallScore: response.meal_score,
        imageAnalysisConfidence: 0.9, // Backend doesn't expose this in response yet
        detectedFoods: response.detected_foods.map(mapFoodItem),
        totalNutrients: mapTotalNutrients(response.total_nutrients),
        healthConstraints: response.health_insights.constraints.map(mapHealthConstraint),
        adjustments: response.adjustments.map(mapAdjustment),
        summary: response.summary,
        entryId: response.entry_id,
        goalAlignment: response.goal_alignment,
        goalFeedback: response.goal_feedback,
    };
}

/**
 * Analyze a meal image using the backend API
 */
export async function analyzeMealImage(
    imageFile: File,
    userId: string = "demo_user",
    mealType?: string
): Promise<MealAnalysis> {
    const formData = new FormData();
    formData.append("image", imageFile);
    formData.append("user_id", userId);
    if (mealType) {
        formData.append("meal_type", mealType);
    }

    const response = await fetch(`${API_BASE_URL}/analyze`, {
        method: "POST",
        body: formData,
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Analysis failed: ${response.status} - ${errorText}`);
    }

    const data: BackendAnalysisResponse = await response.json();
    return mapBackendResponse(data);
}

/**
 * Analyze a meal from text description using the backend API
 */
export async function analyzeMealText(
    textInput: string,
    userId: string = "demo_user",
    mealType?: string
): Promise<MealAnalysis> {
    const formData = new FormData();
    formData.append("text_input", textInput);
    formData.append("user_id", userId);
    if (mealType) {
        formData.append("meal_type", mealType);
    }

    const response = await fetch(`${API_BASE_URL}/analyze`, {
        method: "POST",
        body: formData,
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Analysis failed: ${response.status} - ${errorText}`);
    }

    const data: BackendAnalysisResponse = await response.json();
    return mapBackendResponse(data);
}

/**
 * Check backend health status
 */
export async function checkHealth(): Promise<{
    status: string;
    version: string;
    apiKeysConfigured: Record<string, boolean>;
}> {
    const response = await fetch(`${API_BASE_URL}/health`);

    if (!response.ok) {
        throw new Error("Backend unavailable");
    }

    const data = await response.json();
    return {
        status: data.status,
        version: data.version,
        apiKeysConfigured: data.api_keys_configured,
    };
}
