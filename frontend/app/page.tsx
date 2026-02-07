"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import ImageUpload from "@/components/ImageUpload";
import AnalysisResults from "@/components/AnalysisResults";
import GoalSetup from "@/components/GoalSetup";
import Dashboard from "@/components/Dashboard";
import OnboardingPrompt from "@/components/OnboardingPrompt";
import CalibrationReport from "@/components/CalibrationReport";
import { MealAnalysis } from "@/types/meal";
import { analyzeMealImage, checkHealth } from "@/lib/api";

// Mock data for fallback when backend is unavailable
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
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<MealAnalysis | null>(null);
  const [analysisSteps, setAnalysisSteps] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "offline">("checking");
  const [heroOpacity, setHeroOpacity] = useState(1);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [showGoalSetup, setShowGoalSetup] = useState(false);
  const [showDashboard, setShowDashboard] = useState(false);
  const [showCalibration, setShowCalibration] = useState(false);
  const [showOnboardingPrompt, setShowOnboardingPrompt] = useState(false);
  const [hasProfile, setHasProfile] = useState(false);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const heroRef = useRef<HTMLElement>(null);
  const userId = "demo_user"; // In production, this would come from auth

  // Check backend health on mount
  useEffect(() => {
    const checkBackend = async () => {
      try {
        await checkHealth();
        setBackendStatus("online");
      } catch {
        setBackendStatus("offline");
      }
    };
    checkBackend();
  }, []);

  // Check if user has a profile
  useEffect(() => {
    const checkProfile = async () => {
      try {
        const res = await fetch(`http://localhost:8000/users/${userId}/profile`);
        setHasProfile(res.ok);
      } catch {
        setHasProfile(false);
      }
    };
    checkProfile();
  }, [showGoalSetup]);

  // Scroll-based hero fade effect
  useEffect(() => {
    const handleScroll = () => {
      const scrollY = window.scrollY;
      // Start fading at 50px scroll, fully faded by 250px
      const fadeStart = 50;
      const fadeEnd = 250;

      if (scrollY <= fadeStart) {
        setHeroOpacity(1);
      } else if (scrollY >= fadeEnd) {
        setHeroOpacity(0);
      } else {
        const opacity = 1 - (scrollY - fadeStart) / (fadeEnd - fadeStart);
        setHeroOpacity(opacity);
      }
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Check if user can upload (returns false to block file picker)
  const handleBeforeUpload = useCallback(() => {
    if (!hasProfile) {
      setShowOnboardingPrompt(true);
      return false;  // Don't open file picker
    }
    return true;  // Proceed to open file picker
  }, [hasProfile]);

  const handleImageUpload = useCallback(async (file: File) => {
    // This is called after file is selected, so profile check was already done
    // But keep a safety check in case of direct API usage
    if (!hasProfile) {
      setPendingFile(file);  // Store file to process after onboarding
      setShowOnboardingPrompt(true);
      return;
    }

    // Proceed with analysis
    await processImageUpload(file);
  }, [hasProfile]);

  // Actual image processing logic (extracted for reuse after onboarding)
  const processImageUpload = useCallback(async (file: File) => {
    // Create preview URL
    const reader = new FileReader();
    reader.onload = (e) => {
      setUploadedImage(e.target?.result as string);
    };
    reader.readAsDataURL(file);

    // Store file for API call
    setUploadedFile(file);
    setIsAnalyzing(true);
    setAnalysis(null);
    setError(null);
    setAnalysisSteps([]);

    // Show progress steps
    const steps = [
      "🔍 Detecting food items...",
      "📏 Estimating portions...",
      "🧬 Checking health constraints...",
      "📊 Looking up nutrition data...",
      "🤖 Generating recommendations...",
    ];

    // Animate steps
    for (let i = 0; i < steps.length; i++) {
      setTimeout(() => {
        setAnalysisSteps((prev) => [...prev, steps[i]]);
      }, i * 400);
    }

    try {
      if (backendStatus === "online") {
        // Call real backend API
        const result = await analyzeMealImage(file, "demo_user", "lunch");
        setAnalysis(result);
      } else {
        // Use mock data if backend is offline
        await new Promise((resolve) => setTimeout(resolve, 2500));
        setAnalysis(mockAnalysis);
      }
    } catch (err) {
      console.error("Analysis error:", err);
      setError(err instanceof Error ? err.message : "Analysis failed");
      // Fall back to mock data
      setTimeout(() => {
        setAnalysis(mockAnalysis);
        setError(null);
      }, 1000);
    } finally {
      setIsAnalyzing(false);
    }
  }, [backendStatus]);

  // Handler for when user completes onboarding and wants to proceed with upload
  const handleOnboardingComplete = useCallback(() => {
    setShowOnboardingPrompt(false);
    setShowGoalSetup(false);

    // If there was a pending file, process it now
    if (pendingFile) {
      processImageUpload(pendingFile);
      setPendingFile(null);
    }
  }, [pendingFile, processImageUpload]);

  // Handler for starting goal setup from onboarding prompt
  const handleStartOnboarding = useCallback(() => {
    setShowOnboardingPrompt(false);
    setShowGoalSetup(true);
  }, []);

  // Handler for dismissing onboarding (allow with warning)
  const handleDismissOnboarding = useCallback(() => {
    setShowOnboardingPrompt(false);
    // If there was a pending file, process it anyway (generic feedback)
    if (pendingFile) {
      processImageUpload(pendingFile);
      setPendingFile(null);
    }
  }, [pendingFile, processImageUpload]);

  const handleReset = useCallback(() => {
    setUploadedImage(null);
    setUploadedFile(null);
    setAnalysis(null);
    setIsAnalyzing(false);
    setAnalysisSteps([]);
    setError(null);
  }, []);

  return (
    <main className="min-h-screen">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 glass-header mx-4 mt-4 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center shadow-lg">
            <span className="text-xl">🥗</span>
          </div>
          <span className="text-xl font-bold gradient-text">NutriPilot</span>
        </div>
        <nav
          className="hidden md:flex items-center gap-6"
          style={{
            opacity: heroOpacity,
            transition: 'opacity 0.15s ease-out',
            pointerEvents: heroOpacity < 0.3 ? 'none' : 'auto',
          }}
        >
          <a href="#" className="text-sm text-zinc-300 hover:text-white transition-colors font-medium">Features</a>
          <a href="#" className="text-sm text-zinc-300 hover:text-white transition-colors font-medium">How it Works</a>
          <a href="#" className="text-sm text-zinc-300 hover:text-white transition-colors font-medium">About</a>
        </nav>

        {/* Mobile hamburger menu button */}
        <button
          className="md:hidden flex flex-col gap-1.5 p-2"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-label="Toggle menu"
        >
          <span className={`block w-6 h-0.5 bg-white transition-transform ${mobileMenuOpen ? 'rotate-45 translate-y-2' : ''}`} />
          <span className={`block w-6 h-0.5 bg-white transition-opacity ${mobileMenuOpen ? 'opacity-0' : ''}`} />
          <span className={`block w-6 h-0.5 bg-white transition-transform ${mobileMenuOpen ? '-rotate-45 -translate-y-2' : ''}`} />
        </button>

        <div className="flex items-center gap-4">
          {/* Backend status indicator */}
          <div className="hidden sm:flex items-center gap-2 text-xs">
            <span className={`w-2 h-2 rounded-full ${backendStatus === "online"
              ? "bg-emerald-400 animate-pulse"
              : backendStatus === "offline"
                ? "bg-amber-400"
                : "bg-zinc-400"
              }`} />
            <span className="text-zinc-500">
              {backendStatus === "online" ? "Live API" : backendStatus === "offline" ? "Demo Mode" : "Checking..."}
            </span>
          </div>

          {/* Dashboard button - show if user has profile */}
          {hasProfile && (
            <button
              onClick={() => setShowDashboard(true)}
              className="hidden sm:flex items-center gap-2 px-3 py-2 text-sm rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 transition-colors"
            >
              <svg className="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <span className="text-zinc-300">Dashboard</span>
            </button>
          )}

          {/* Calibration button - show if user has profile */}
          {hasProfile && (
            <button
              onClick={() => setShowCalibration(true)}
              className="hidden sm:flex items-center gap-2 px-3 py-2 text-sm rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 transition-colors"
              title="Run calibration analysis"
            >
              <span className="text-purple-400">🔬</span>
              <span className="text-zinc-300">Calibrate</span>
            </button>
          )}

          <button
            onClick={() => setShowGoalSetup(true)}
            className="btn-primary text-sm py-2 px-4"
          >
            <span>{hasProfile ? '⚙️ Goals' : '🎯 Set Goals'}</span>
          </button>
        </div>
      </header>

      {/* Mobile Navigation Drawer */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setMobileMenuOpen(false)} />
          <nav className="absolute top-20 left-4 right-4 glass-card p-6 space-y-4 animate-fade-in">
            <a href="#" className="block text-lg text-zinc-200 hover:text-white transition-colors py-2">Features</a>
            <a href="#" className="block text-lg text-zinc-200 hover:text-white transition-colors py-2">How it Works</a>
            <a href="#" className="block text-lg text-zinc-200 hover:text-white transition-colors py-2">About</a>
          </nav>
        </div>
      )}

      {/* Hero Section */}
      <section
        ref={heroRef}
        className="pt-32 pb-16 px-4"
        style={{
          opacity: heroOpacity,
          transform: `translateY(${(1 - heroOpacity) * -20}px)`,
          transition: 'opacity 0.1s ease-out, transform 0.1s ease-out',
          pointerEvents: heroOpacity < 0.3 ? 'none' : 'auto',
        }}
      >
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 md:px-4 md:py-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 mb-6">
            <span className="w-1.5 h-1.5 md:w-2 md:h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs md:text-sm text-emerald-400">Powered by Gemini 2.0 Vision AI</span>
          </div>

          <h1 className="text-5xl md:text-7xl font-bold mb-6 leading-tight hero-text">
            Your <span className="gradient-text">Autonomous</span><br />
            Nutrition Co-Pilot
          </h1>

          <p className="text-xl hero-description max-w-2xl mx-auto mb-12">
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
              <ImageUpload
                onUpload={handleImageUpload}
                onBeforeUpload={handleBeforeUpload}
                hasProfile={hasProfile}
              />
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
                          <p className="text-sm text-zinc-400 mt-1">
                            {backendStatus === "online" ? "AI agents processing..." : "Using demo mode..."}
                          </p>
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
                      <p className="text-sm text-zinc-500 mt-1">Falling back to demo mode...</p>
                    </div>
                  )}

                  {isAnalyzing ? (
                    <div className="h-full flex items-center justify-center">
                      <div className="text-center w-full">
                        <div className="space-y-3 max-w-sm mx-auto">
                          {analysisSteps.map((step, i) => (
                            <div
                              key={step}
                              className="flex items-center gap-3 text-zinc-400 animate-fade-in"
                              style={{ animationDelay: `${i * 0.1}s` }}
                            >
                              <div className="w-5 h-5 rounded-full bg-emerald-500/20 flex items-center justify-center">
                                <span className="text-xs">✓</span>
                              </div>
                              <span className="text-sm">{step}</span>
                            </div>
                          ))}
                          {analysisSteps.length < 5 && (
                            <div className="flex items-center gap-3 text-zinc-500">
                              <div className="w-5 h-5 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" />
                              <span className="text-sm">Processing...</span>
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
      <footer className="border-t border-white/5 py-12 md:py-16 px-4">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="text-xl">🥗</span>
            <span className="font-semibold">NutriPilot AI</span>
          </div>
          <p className="text-sm text-zinc-500 text-center md:text-right">
            Built for the Commit to Change Hackathon • Powered by Gemini & Opik
          </p>
        </div>
      </footer>

      {/* Goal Setup Modal */}
      <GoalSetup
        userId={userId}
        isOpen={showGoalSetup}
        onClose={() => setShowGoalSetup(false)}
        onSave={() => {
          setHasProfile(true);
          handleOnboardingComplete();
        }}
      />

      {/* Onboarding Prompt Modal */}
      <OnboardingPrompt
        isOpen={showOnboardingPrompt}
        onSetupGoals={handleStartOnboarding}
        onDismiss={handleDismissOnboarding}
      />

      {/* Dashboard Modal */}
      <Dashboard
        userId={userId}
        isOpen={showDashboard}
        onClose={() => setShowDashboard(false)}
        onEditGoals={() => {
          setShowDashboard(false);
          setShowGoalSetup(true);
        }}
        onResetProfile={() => {
          setHasProfile(false);
          // Clear any pending file
          setPendingFile(null);
        }}
      />

      {/* Calibration Report Modal */}
      <CalibrationReport
        userId={userId}
        isOpen={showCalibration}
        onClose={() => setShowCalibration(false)}
      />
    </main>
  );
}
