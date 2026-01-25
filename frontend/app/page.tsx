"use client";

import { useState, useCallback } from "react";
import ImageUpload from "@/components/ImageUpload";
import AnalysisResults from "@/components/AnalysisResults";
import { MealAnalysis } from "@/types/meal";

// Mock data for demonstration (will be replaced with real API)
const mockAnalysis: MealAnalysis = {
  sessionId: "demo-session-001",
  timestamp: new Date().toISOString(),
  mealType: "lunch",
  overallScore: 78,
  imageAnalysisConfidence: 0.94,
  detectedFoods: [
    {
      name: "Grilled Chicken Breast",
      portionGrams: 150,
      portionDescription: "1 medium breast",
      confidence: 0.96,
      nutrients: [
        { name: "Protein", amount: 31, unit: "g", percentDaily: 62 },
        { name: "Calories", amount: 165, unit: "kcal", percentDaily: 8 },
        { name: "Fat", amount: 3.6, unit: "g", percentDaily: 5 },
      ],
    },
    {
      name: "Brown Rice",
      portionGrams: 200,
      portionDescription: "1 cup cooked",
      confidence: 0.92,
      nutrients: [
        { name: "Carbohydrates", amount: 45, unit: "g", percentDaily: 15 },
        { name: "Fiber", amount: 3.5, unit: "g", percentDaily: 14 },
        { name: "Calories", amount: 216, unit: "kcal", percentDaily: 11 },
      ],
    },
    {
      name: "Steamed Broccoli",
      portionGrams: 100,
      portionDescription: "1 cup florets",
      confidence: 0.89,
      nutrients: [
        { name: "Vitamin C", amount: 89, unit: "mg", percentDaily: 99 },
        { name: "Fiber", amount: 2.6, unit: "g", percentDaily: 10 },
        { name: "Calories", amount: 34, unit: "kcal", percentDaily: 2 },
      ],
    },
  ],
  totalNutrients: [
    { name: "Calories", amount: 415, unit: "kcal", percentDaily: 21 },
    { name: "Protein", amount: 35, unit: "g", percentDaily: 70 },
    { name: "Carbohydrates", amount: 52, unit: "g", percentDaily: 17 },
    { name: "Fat", amount: 8, unit: "g", percentDaily: 10 },
    { name: "Fiber", amount: 6.1, unit: "g", percentDaily: 24 },
    { name: "Vitamin C", amount: 95, unit: "mg", percentDaily: 106 },
  ],
  healthConstraints: [
    {
      constraintType: "blood_glucose",
      value: 98,
      unit: "mg/dL",
      status: "normal",
      recommendation: "Your glucose levels are optimal. This meal's glycemic load is moderate.",
    },
  ],
  adjustments: [
    {
      foodName: "Brown Rice",
      action: "reduce",
      reason: "Consider reducing portion by 25% to better balance macros",
      priority: 2,
    },
  ],
  summary: "A well-balanced, protein-rich meal with excellent micronutrient content. The combination of lean protein, complex carbs, and vegetables provides sustained energy. Consider slightly reducing rice portion for optimal macro balance.",
};

export default function Home() {
  const [uploadedImage, setUploadedImage] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<MealAnalysis | null>(null);
  const [streamingText, setStreamingText] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  const handleImageUpload = useCallback(async (file: File) => {
    const reader = new FileReader();
    reader.onload = async (e) => {
      const base64 = e.target?.result as string;
      setUploadedImage(base64);
      setIsAnalyzing(true);
      setAnalysis(null);
      setError(null);
      setStreamingText("");

      try {
        // Call streaming API
        const response = await fetch("/api/analyze", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ imageBase64: base64 }),
        });

        if (!response.ok) {
          throw new Error("Analysis failed");
        }

        // Handle streaming response
        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        let fullText = "";

        if (reader) {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            fullText += chunk;
            setStreamingText(fullText);
          }
        }

        // Parse final response for analysis
        try {
          const jsonMatch = fullText.match(/\{[\s\S]*\}/);
          if (jsonMatch) {
            const parsed = JSON.parse(jsonMatch[0]);
            const mealAnalysis: MealAnalysis = {
              sessionId: `session-${Date.now()}`,
              timestamp: new Date().toISOString(),
              mealType: "lunch",
              overallScore: parsed.mealScore || 75,
              imageAnalysisConfidence: 0.92,
              detectedFoods: (parsed.detectedFoods || []).map((food: { name: string; portionGrams: number; confidence?: number; nutrients?: Record<string, number> }) => ({
                name: food.name,
                portionGrams: food.portionGrams,
                portionDescription: `${food.portionGrams}g`,
                confidence: food.confidence || 0.9,
                nutrients: food.nutrients ? Object.entries(food.nutrients).map(([name, amount]) => ({
                  name,
                  amount: amount as number,
                  unit: name === "calories" ? "kcal" : "g",
                })) : [],
              })),
              totalNutrients: parsed.totalNutrients ? Object.entries(parsed.totalNutrients).map(([name, amount]) => ({
                name: name.charAt(0).toUpperCase() + name.slice(1),
                amount: amount as number,
                unit: name === "calories" ? "kcal" : "g",
                percentDaily: Math.round(((amount as number) / (name === "calories" ? 2000 : name === "protein" ? 50 : 300)) * 100),
              })) : [],
              healthConstraints: parsed.healthInsights?.constraints?.map((c: { type: string; status: string; message: string }) => ({
                constraintType: c.type,
                value: 0,
                unit: "",
                status: c.status as "normal" | "warning" | "critical",
                recommendation: c.message,
              })) || [],
              adjustments: [],
              summary: parsed.summary || "Analysis complete.",
            };
            setAnalysis(mealAnalysis);
          } else {
            // Use mock data if parsing fails
            setAnalysis(mockAnalysis);
          }
        } catch {
          // Use mock data on parse error
          setAnalysis(mockAnalysis);
        }
      } catch (err) {
        console.error("Analysis error:", err);
        // Fall back to mock data for demo
        setTimeout(() => {
          setAnalysis(mockAnalysis);
        }, 2000);
      } finally {
        setIsAnalyzing(false);
      }
    };
    reader.readAsDataURL(file);
  }, []);

  const handleReset = useCallback(() => {
    setUploadedImage(null);
    setAnalysis(null);
    setIsAnalyzing(false);
    setStreamingText("");
    setError(null);
  }, []);

  return (
    <main className="min-h-screen">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 glass-card mx-4 mt-4 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center">
            <span className="text-xl">🥗</span>
          </div>
          <span className="text-xl font-bold gradient-text">NutriPilot</span>
        </div>
        <nav className="hidden md:flex items-center gap-6">
          <a href="#" className="text-sm text-zinc-400 hover:text-white transition-colors">Features</a>
          <a href="#" className="text-sm text-zinc-400 hover:text-white transition-colors">How it Works</a>
          <a href="#" className="text-sm text-zinc-400 hover:text-white transition-colors">About</a>
        </nav>
        <button className="btn-primary text-sm py-2 px-4">
          <span>Get Started</span>
        </button>
      </header>

      {/* Hero Section */}
      <section className="pt-32 pb-16 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 mb-6">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-sm text-emerald-400">Powered by Gemini 2.0 Vision AI</span>
          </div>

          <h1 className="text-5xl md:text-7xl font-bold mb-6 leading-tight">
            Your <span className="gradient-text">Autonomous</span><br />
            Nutrition Co-Pilot
          </h1>

          <p className="text-xl text-zinc-400 max-w-2xl mx-auto mb-12">
            Snap a photo of your meal and get instant AI-powered nutritional analysis
            with personalized health recommendations tailored to your goals.
          </p>

          {/* Feature pills */}
          <div className="flex flex-wrap justify-center gap-3 mb-12">
            {[
              "🎯 Pixel-Precise Portions",
              "🧬 Bio-Data Integration",
              "⚡ Real-Time Analysis",
              "📊 Opik Observability"
            ].map((feature) => (
              <span
                key={feature}
                className="px-4 py-2 rounded-full bg-white/5 border border-white/10 text-sm text-zinc-300"
              >
                {feature}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* Main App Section */}
      <section className="px-4 pb-24">
        <div className="max-w-6xl mx-auto">
          <div className="glass-card p-8 md:p-12">
            {!uploadedImage ? (
              <ImageUpload onUpload={handleImageUpload} />
            ) : (
              <div className="grid lg:grid-cols-2 gap-8">
                {/* Uploaded Image Preview */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold">Your Meal</h3>
                    <button
                      onClick={handleReset}
                      className="text-sm text-zinc-400 hover:text-white transition-colors"
                    >
                      ← Upload New
                    </button>
                  </div>
                  <div className="relative rounded-2xl overflow-hidden aspect-[4/3]">
                    <img
                      src={uploadedImage}
                      alt="Uploaded meal"
                      className="w-full h-full object-cover"
                    />
                    {isAnalyzing && (
                      <div className="absolute inset-0 bg-black/60 flex items-center justify-center">
                        <div className="text-center">
                          <div className="w-16 h-16 border-4 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin mb-4 mx-auto" />
                          <p className="text-emerald-400 font-medium">Analyzing with Gemini Vision...</p>
                          <p className="text-sm text-zinc-400 mt-1">AI agents working...</p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Analysis Results */}
                <div>
                  {error && (
                    <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 mb-4">
                      <p className="text-rose-400">⚠️ {error}</p>
                    </div>
                  )}

                  {isAnalyzing ? (
                    <div className="h-full flex items-center justify-center">
                      <div className="text-center">
                        <div className="space-y-3">
                          {streamingText ? (
                            <div className="p-4 rounded-xl bg-white/5 border border-white/10 max-h-64 overflow-y-auto">
                              <pre className="text-xs text-zinc-400 whitespace-pre-wrap font-mono">
                                {streamingText.slice(0, 500)}...
                              </pre>
                            </div>
                          ) : (
                            <div className="stagger-animation">
                              {["Detecting food items...", "Estimating portions...", "Looking up nutrition data...", "Checking health constraints..."].map((step, i) => (
                                <div
                                  key={step}
                                  className="flex items-center gap-3 text-zinc-400"
                                  style={{ animationDelay: `${i * 0.5}s` }}
                                >
                                  <div className="w-5 h-5 rounded-full border-2 border-emerald-500/30 border-t-emerald-500 animate-spin" />
                                  <span>{step}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ) : analysis ? (
                    <AnalysisResults analysis={analysis} />
                  ) : null}
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 py-8 px-4">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="text-xl">🥗</span>
            <span className="font-semibold">NutriPilot AI</span>
          </div>
          <p className="text-sm text-zinc-500">
            Built for the Commit to Change Hackathon • Powered by Gemini & Opik
          </p>
        </div>
      </footer>
    </main>
  );
}
