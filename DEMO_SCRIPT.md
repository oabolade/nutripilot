# NutriPilot Demo Video Script

> **Target Duration**: 2-3 minutes  
> **Hackathon**: Commit to Change: An AI Agents Hackathon

---

## Opening (0:00 - 0:20)

**[VISUAL: App logo or landing screen]**

> "Meet NutriPilot — your AI-powered nutrition co-pilot that turns any food photo into personalized health insights in seconds."

**[VISUAL: Quick montage of uploading food → seeing results]**

> "Built with Google's Gemini 2.0 Flash and Comet Opik for full observability."

---

## The Problem (0:20 - 0:45)

**[VISUAL: Show frustration of manual logging — a nutrition app with tiny food entry fields]**

> "Tracking nutrition is broken. Current apps require you to manually search and log every ingredient — it's tedious, inaccurate, and most people give up within a week."

> "And even if you log perfectly, generic apps don't know about YOUR health goals — whether you're managing diabetes, training for a marathon, or recovering from surgery."

**[VISUAL: Show a complex meal that would take 10+ steps to log manually]**

> "This plate? About 15 minutes to log accurately. With NutriPilot? Under 5 seconds."

---

## The Solution: NutriPilot Demo (0:45 - 2:00)

### Feature 1: Instant Photo Analysis

**[VISUAL: Upload a food photo in the app]**

> "Just snap a photo. NutriPilot uses Gemini 2.0 Flash's vision capabilities to identify every food item — fried plantains, tilapia, rice — along with accurate portion estimates."

**[VISUAL: Show the detected foods list with portions and calories]**

> "No searching. No guessing weights. The AI does the heavy lifting."

### Feature 2: Goal-Personalized Feedback

**[VISUAL: Show the goal setup screen — select "Weight Loss" and "Pre-Diabetic"]**

> "NutriPilot knows YOUR goals. Set up your health profile once — weight loss, diabetes management, heart health — and every meal gets evaluated against YOUR targets."

**[VISUAL: Show the analysis results with goal-specific feedback]**

> "See that amber warning? It's telling me this meal is high in carbs for my blood sugar goals, and suggesting I swap the rice for more vegetables."

### Feature 3: Calibration with Opik

**[VISUAL: Open the Calibration Report modal, show metrics]**

> "Here's where it gets interesting. NutriPilot learns from every analysis using Opik observability. The Calibration Report shows how accurate our calorie estimates are — currently 8% mean average error across 18 meal analyses."

**[VISUAL: Show the prompt improvement suggestions]**

> "And it generates specific suggestions to improve accuracy — like 'for fried foods, account for oil absorption' — that we can feed back into our prompts."

### Feature 4: Full Observability

**[VISUAL: Show Opik dashboard with traces]**

> "Every request is traced in Opik — you can see exactly how the orchestrator coordinates between VisionAnalyst, NutriAuditor, and GoalEvaluator. Full transparency, no black boxes."

---

## Tech Highlights (2:00 - 2:30)

**[VISUAL: Architecture diagram or code snippets]**

> "Under the hood, NutriPilot uses a multi-agent ReAct pattern:"

> "1. **Observe** — Gemini Vision analyzes the image  
> 2. **Think** — Agents fetch nutrition data and health constraints  
> 3. **Act** — Generate personalized recommendations"

> "All orchestrated with Pydantic type-safe handoffs and full Opik tracing."

---

## Closing (2:30 - 2:45)

**[VISUAL: Return to app showing a successful meal analysis]**

> "NutriPilot: Observe. Think. Act. Your nutrition, personalized."

> "Try it now at [demo URL] — and check out the full source on GitHub."

**[VISUAL: GitHub URL + Opik link]**

---

## Recording Tips

1. **Screen recording**: Use a clean browser window at 1920x1080
2. **Food images**: Use 3-4 diverse meals (breakfast, lunch, dinner)
3. **Audio**: Record voiceover separately for better quality
4. **Pace**: Pause on key visuals so viewers can read
5. **Music**: Subtle background music (optional, check licensing)

## Key Timestamps

| Section | Start | Duration |
|---------|-------|----------|
| Opening | 0:00 | 20s |
| Problem | 0:20 | 25s |
| Demo - Photo Analysis | 0:45 | 30s |
| Demo - Goals | 1:15 | 25s |
| Demo - Calibration | 1:40 | 20s |
| Tech Highlights | 2:00 | 30s |
| Closing | 2:30 | 15s |
