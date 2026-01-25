import { google } from "@ai-sdk/google";
import { streamText } from "ai";
import { z } from "zod";

// Allow streaming responses up to 60 seconds
export const maxDuration = 60;

// Define tool schemas
const nutritionLookupSchema = z.object({
    foodName: z.string().describe("The name of the food to look up"),
    portionGrams: z.number().describe("The portion size in grams"),
});

const healthConstraintsSchema = z.object({
    totalCalories: z.number().describe("Total calories in the meal"),
    totalCarbs: z.number().describe("Total carbohydrates in grams"),
    totalSodium: z.number().optional().describe("Total sodium in mg if known"),
});

const scoreMealSchema = z.object({
    calories: z.number(),
    protein: z.number(),
    carbs: z.number(),
    fat: z.number(),
    fiber: z.number(),
    vegetableServings: z.number().describe("Number of vegetable servings detected"),
});

// Mock nutrition data
const nutritionData: Record<string, { calories: number; protein: number; carbs: number; fat: number; fiber: number }> = {
    "chicken breast": { calories: 165, protein: 31, carbs: 0, fat: 3.6, fiber: 0 },
    "grilled chicken": { calories: 165, protein: 31, carbs: 0, fat: 3.6, fiber: 0 },
    "brown rice": { calories: 111, protein: 2.6, carbs: 23, fat: 0.9, fiber: 1.8 },
    "rice": { calories: 130, protein: 2.7, carbs: 28, fat: 0.3, fiber: 0.4 },
    "broccoli": { calories: 34, protein: 2.8, carbs: 7, fat: 0.4, fiber: 2.6 },
    "steamed broccoli": { calories: 34, protein: 2.8, carbs: 7, fat: 0.4, fiber: 2.6 },
    "salmon": { calories: 208, protein: 20, carbs: 0, fat: 13, fiber: 0 },
    "apple": { calories: 52, protein: 0.3, carbs: 14, fat: 0.2, fiber: 2.4 },
    "banana": { calories: 89, protein: 1.1, carbs: 23, fat: 0.3, fiber: 2.6 },
    "eggs": { calories: 155, protein: 13, carbs: 1.1, fat: 11, fiber: 0 },
    "avocado": { calories: 160, protein: 2, carbs: 9, fat: 15, fiber: 7 },
};

export async function POST(req: Request) {
    const { imageBase64, mealDescription } = await req.json();

    const analysisPrompt = imageBase64
        ? `You are NutriPilot, an expert nutritionist AI. Analyze this food image and identify all visible food items with estimated portion sizes.

For each food item you identify, estimate the portion size in grams based on visual cues.

Provide a detailed but friendly analysis in this exact JSON format:
{
  "detectedFoods": [{"name": "food name", "portionGrams": 100, "confidence": 0.9}],
  "totalNutrients": {"calories": 400, "protein": 30, "carbohydrates": 40, "fat": 10, "fiber": 5},
  "healthInsights": {"glucoseStatus": "normal", "constraints": [], "recommendations": "Your recommendations here"},
  "mealScore": 75,
  "summary": "Your summary of the meal analysis"
}`
        : `You are NutriPilot, an expert nutritionist AI. Analyze this meal description: "${mealDescription}"

Provide your analysis in the same JSON format with detectedFoods, totalNutrients, healthInsights, mealScore, and summary.`;

    const result = streamText({
        model: google("gemini-2.0-flash"),
        messages: [
            {
                role: "user",
                content: imageBase64
                    ? [
                        { type: "text", text: analysisPrompt },
                        { type: "image", image: imageBase64 },
                    ]
                    : [{ type: "text", text: analysisPrompt }],
            },
        ],
    });

    return result.toTextStreamResponse();
}
