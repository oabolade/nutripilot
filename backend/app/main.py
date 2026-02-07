"""
NutriPilot AI - FastAPI Application

Main entry point for the NutriPilot backend API.
Implements the /analyze endpoint and health checks.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.config import get_settings
from app.core.orchestrator import StudioOrchestrator
from app.core.state import MealState, MealType
from app.core.user_goals import (
    UserProfile, 
    MealLogEntry, 
    DashboardData, 
    HealthGoal, 
    HealthCondition,
    DailyNutrientTargets,
    GoalEvaluation,
)
from app.core.storage import storage
from app.agents.goal_evaluator import GoalEvaluator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# === Lifespan Management ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup application resources."""
    settings = get_settings()
    
    # Startup
    logger.info("🚀 Starting NutriPilot AI Backend")
    logger.info(f"Environment: {settings.environment}")
    
    # Validate API keys
    key_status = settings.validate_required_keys()
    for key, configured in key_status.items():
        status = "✅" if configured else "⚠️ Missing"
        logger.info(f"  {key}: {status}")
    
    # Initialize Opik if available
    if settings.opik_api_key:
        try:
            import opik
            opik.configure(api_key=settings.opik_api_key)
            logger.info(f"📊 Opik tracing enabled - Project: {settings.opik_project_name}")
        except Exception as e:
            logger.warning(f"⚠️ Opik initialization failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down NutriPilot AI Backend")


# === FastAPI Application ===
app = FastAPI(
    title="NutriPilot AI",
    description="Autonomous Nutrition Agent with Observe-Think-Act Architecture",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Request/Response Models ===
class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    api_keys_configured: dict[str, bool]


class AnalyzeResponse(BaseModel):
    """Response from the /analyze endpoint."""
    session_id: str
    detected_foods: list[dict]
    total_nutrients: dict
    health_insights: dict
    meal_score: float | None
    summary: str
    adjustments: list[dict]
    processing_time_ms: int
    # Goal-related fields
    goal_alignment: float | None = None
    goal_feedback: list[str] = []
    # Verification
    entry_id: str | None = None


# === Endpoints ===
@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "NutriPilot AI",
        "version": "0.1.0",
        "description": "Autonomous Nutrition Agent",
        "docs_url": "/docs",
    }


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """Health check endpoint for monitoring."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        timestamp=datetime.utcnow().isoformat(),
        version="0.1.0",
        api_keys_configured=settings.validate_required_keys(),
    )


@app.post("/analyze", response_model=AnalyzeResponse, tags=["analysis"])
async def analyze_meal(
    image: UploadFile | None = File(None, description="Food image to analyze"),
    text_input: str | None = Form(None, description="Text description of the meal"),
    user_id: str = Form(default="demo_user", description="User identifier"),
    meal_type: str | None = Form(None, description="Meal type: breakfast, lunch, dinner, snack"),
):
    """
    Analyze a meal from an image or text description.
    
    This endpoint orchestrates the Observe-Think-Act pipeline:
    1. **Observe**: Analyze the image with Gemini Vision to detect foods
    2. **Think**: Query health constraints and lookup nutrition data
    3. **Act**: Generate recommendations and calculate meal score
    
    Returns a comprehensive meal analysis with detected foods, nutrients,
    health insights, and personalized recommendations.
    """
    import time
    start_time = time.time()
    
    # Validate input
    if not image and not text_input:
        raise HTTPException(
            status_code=400,
            detail="Either an image or text description is required"
        )
    
    # Parse meal type
    parsed_meal_type = None
    if meal_type:
        try:
            parsed_meal_type = MealType(meal_type.lower())
        except ValueError:
            pass  # Keep as None if invalid
    
    # Read image bytes if provided
    image_bytes = None
    if image:
        image_bytes = await image.read()
        logger.info(f"Received image: {len(image_bytes)} bytes")
    
    # Fetch user profile for goal-based personalization
    user_profile = storage.get_profile(user_id)
    if user_profile:
        logger.info(f"Found user profile with goals: {[g.value for g in user_profile.goals]}")
    
    # Initialize orchestrator
    orchestrator = StudioOrchestrator()
    
    try:
        # Run the Observe-Think-Act pipeline
        result: MealState = await orchestrator.process(
            user_id=user_id,
            image_bytes=image_bytes,
            text_input=text_input,
            meal_type=parsed_meal_type,
            user_profile=user_profile,  # Pass profile for goal-based recommendations
        )
        
        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # === Goal Evaluation ===
        goal_alignment = None
        goal_feedback = []
        
        profile = storage.get_profile(user_id)
        if profile and profile.goals and result.detected_foods:
            try:
                goal_evaluator = GoalEvaluator()
                eval_result = await goal_evaluator.execute((result, profile))
                if eval_result.success and eval_result.output:
                    goal_alignment = eval_result.output.alignment_score
                    goal_feedback = eval_result.output.feedback
            except Exception as e:
                logger.warning(f"Goal evaluation failed: {e}")
        
        # === Log Meal for Tracking ===
        entry_id = None
        if result.detected_foods:  # Only log if food was detected
            # Extract nutrient totals for logging
            nutrients = {n.name: n.amount for n in result.total_nutrients}
            
            meal_entry = MealLogEntry(
                user_id=user_id,
                meal_type=meal_type or "snack",
                food_names=[f.name for f in result.detected_foods],
                total_calories=nutrients.get("calories", 0),
                total_protein=nutrients.get("protein", 0),
                total_carbs=nutrients.get("carbohydrates", 0),
                total_fat=nutrients.get("fat", 0),
                total_fiber=nutrients.get("fiber", 0),
                total_sodium=nutrients.get("sodium", 0),
                meal_score=result.overall_score or 0,
                goal_alignment_score=goal_alignment or 0,
                goal_feedback=goal_feedback,
            )
            storage.log_meal(meal_entry)
            entry_id = meal_entry.entry_id  # Capture the entry ID for verification
        
        # Format response
        response = AnalyzeResponse(
            session_id=result.session_id,
            detected_foods=[
                {
                    "name": food.name,
                    "portion_grams": food.portion_grams,
                    "portion_description": food.portion_description,
                    "confidence": food.confidence,
                    "nutrients": [
                        {"name": n.name, "amount": n.amount, "unit": n.unit}
                        for n in food.nutrients
                    ],
                }
                for food in result.detected_foods
            ],
            total_nutrients={
                n.name: {"amount": n.amount, "unit": n.unit}
                for n in result.total_nutrients
            },
            health_insights={
                "constraints": [
                    {
                        "type": c.constraint_type,
                        "value": c.value,
                        "unit": c.unit,
                        "status": c.status.value,
                        "recommendation": c.recommendation,
                    }
                    for c in result.health_constraints
                ],
                "violations": result.constraint_violations,
            },
            meal_score=result.overall_score,
            summary=result.summary or "Analysis complete",
            adjustments=[
                {
                    "food": adj.food_name,
                    "action": adj.action.value,
                    "reason": adj.reason,
                    "alternative": adj.alternative,
                }
                for adj in result.adjustments
            ],
            processing_time_ms=processing_time_ms,
            goal_alignment=goal_alignment,
            goal_feedback=goal_feedback,
            entry_id=entry_id,  # Include entry ID for verification
        )
        
        logger.info(f"Analysis complete in {processing_time_ms}ms for session {result.session_id}")
        return response
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


# === User Profile Endpoints ===

class ProfileCreateRequest(BaseModel):
    """Request to create/update a user profile."""
    display_name: str | None = None
    goals: list[str] = []  # List of HealthGoal values
    conditions: list[str] = []  # List of HealthCondition values
    dietary_restrictions: list[str] = []
    daily_targets: dict | None = None
    timeline_weeks: int = 12


@app.get("/users/{user_id}/profile", tags=["users"])
async def get_user_profile(user_id: str):
    """Get a user's profile with goals and settings."""
    profile = storage.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile.model_dump()


@app.post("/users/{user_id}/profile", tags=["users"])
async def create_or_update_profile(user_id: str, request: ProfileCreateRequest):
    """Create or update a user profile with goals and conditions."""
    # Parse goals
    goals = []
    for goal_str in request.goals:
        try:
            goals.append(HealthGoal(goal_str))
        except ValueError:
            logger.warning(f"Invalid goal: {goal_str}")
    
    # Parse conditions
    conditions = []
    for cond_str in request.conditions:
        try:
            conditions.append(HealthCondition(cond_str))
        except ValueError:
            logger.warning(f"Invalid condition: {cond_str}")
    
    # Parse daily targets
    daily_targets = DailyNutrientTargets()
    if request.daily_targets:
        daily_targets = DailyNutrientTargets(**request.daily_targets)
    
    # Check if profile exists
    existing = storage.get_profile(user_id)
    
    if existing:
        # Update existing profile
        existing.display_name = request.display_name or existing.display_name
        existing.goals = goals
        existing.conditions = conditions
        existing.dietary_restrictions = request.dietary_restrictions
        existing.daily_targets = daily_targets
        existing.timeline_weeks = request.timeline_weeks
        profile = storage.save_profile(existing)
    else:
        # Create new profile
        profile = UserProfile(
            user_id=user_id,
            display_name=request.display_name,
            goals=goals,
            conditions=conditions,
            dietary_restrictions=request.dietary_restrictions,
            daily_targets=daily_targets,
            timeline_weeks=request.timeline_weeks,
        )
        profile = storage.save_profile(profile)
    
    logger.info(f"Saved profile for user {user_id}: {len(goals)} goals, {len(conditions)} conditions")
    return profile.model_dump()


@app.delete("/users/{user_id}/profile", tags=["users"])
async def delete_profile(user_id: str):
    """Delete a user profile."""
    if storage.delete_profile(user_id):
        return {"message": "Profile deleted"}
    raise HTTPException(status_code=404, detail="Profile not found")


# === Goals Endpoints ===

@app.get("/goals/available", tags=["goals"])
async def get_available_goals():
    """Get all available health goals and conditions."""
    return {
        "goals": [
            {"value": g.value, "label": g.value.replace("_", " ").title()}
            for g in HealthGoal
        ],
        "conditions": [
            {"value": c.value, "label": c.value.replace("_", " ").title()}
            for c in HealthCondition
        ],
    }


@app.get("/users/{user_id}/goals", tags=["goals"])
async def get_user_goals(user_id: str):
    """Get a user's current goals and progress."""
    profile = storage.get_profile(user_id)
    if not profile:
        return {"goals": [], "conditions": [], "message": "No profile set up yet"}
    
    return {
        "goals": [g.value for g in profile.goals],
        "conditions": [c.value for c in profile.conditions],
        "timeline_weeks": profile.timeline_weeks,
        "start_date": profile.start_date.isoformat(),
        "daily_targets": profile.daily_targets.model_dump(),
    }


# === Dashboard Endpoint ===

@app.get("/users/{user_id}/dashboard", tags=["dashboard"])
async def get_dashboard(user_id: str):
    """Get dashboard data with progress metrics and meal history."""
    dashboard = storage.get_dashboard_data(user_id)
    return dashboard.model_dump()


# === Meal History Endpoints ===

@app.get("/users/{user_id}/meals", tags=["meals"])
async def get_meal_history(user_id: str, days: int = 30, limit: int = 50):
    """Get meal history for a user."""
    meals = storage.get_meal_history(user_id, days=days, limit=limit)
    return {"meals": [m.model_dump() for m in meals], "total": len(meals)}


# === Calibration Endpoints ===

class VerifyCaloriesRequest(BaseModel):
    """Request to verify actual calories for a meal."""
    actual_calories: float

class CalibrationRequest(BaseModel):
    """Request for running calibration."""
    limit: int = 50


class VerifyNutritionRequest(BaseModel):
    """Full nutrition verification request."""
    actual_calories: Optional[float] = None
    actual_protein: Optional[float] = None
    actual_carbs: Optional[float] = None
    actual_fat: Optional[float] = None
    actual_fiber: Optional[float] = None
    actual_sodium: Optional[float] = None
    verification_source: Optional[str] = None  # 'nutrition_label', 'food_scale', 'recipe_calculation', 'database'
    notes: Optional[str] = None


@app.post("/calibrate/{user_id}", tags=["calibration"])
async def run_calibration(user_id: str, request: CalibrationRequest = CalibrationRequest()):
    """
    Run nutrition calibration analysis.
    
    Compares estimated vs actual calories to generate metrics and prompt suggestions.
    Requires verified meals with actual_calories set.
    """
    from app.agents.nutri_calibrator import NutriCalibrator
    
    calibrator = NutriCalibrator()
    report = await calibrator.process((user_id, request.limit))
    
    return report.model_dump()


@app.post("/meals/{entry_id}/verify", tags=["calibration"])
async def verify_meal_nutrition(entry_id: str, request: VerifyNutritionRequest):
    """
    Submit user-verified nutrition data for a meal.
    
    Creates ground truth data for calibration, model evaluation, and dataset generation.
    
    **Verification Sources:**
    - `nutrition_label`: From packaged food nutrition label
    - `food_scale`: Weighed on a food scale
    - `recipe_calculation`: Calculated from recipe ingredients
    - `database`: Looked up in nutrition database (USDA, etc.)
    """
    from datetime import datetime
    
    # Find the meal in storage
    for user_id, meals in storage._meal_logs.items():
        for meal in meals:
            if meal.entry_id == entry_id:
                # Update verification fields
                meal.is_verified = True
                meal.verified_at = datetime.utcnow()
                
                if request.actual_calories is not None:
                    meal.actual_calories = request.actual_calories
                if request.actual_protein is not None:
                    meal.actual_protein = request.actual_protein
                if request.actual_carbs is not None:
                    meal.actual_carbs = request.actual_carbs
                if request.actual_fat is not None:
                    meal.actual_fat = request.actual_fat
                if request.actual_fiber is not None:
                    meal.actual_fiber = request.actual_fiber
                if request.actual_sodium is not None:
                    meal.actual_sodium = request.actual_sodium
                if request.verification_source:
                    meal.verification_source = request.verification_source
                if request.notes:
                    meal.verification_notes = request.notes
                
                # Calculate errors
                def calc_error(estimated, actual):
                    if actual is None or actual == 0:
                        return None, None
                    error = estimated - actual
                    pct = round(error / actual * 100, 1)
                    return error, pct
                
                cal_error, cal_pct = calc_error(meal.total_calories, meal.actual_calories)
                protein_error, protein_pct = calc_error(meal.total_protein, meal.actual_protein)
                carbs_error, carbs_pct = calc_error(meal.total_carbs, meal.actual_carbs)
                fat_error, fat_pct = calc_error(meal.total_fat, meal.actual_fat)
                
                logger.info(f"✅ Verified meal {entry_id}: calories={meal.actual_calories}, source={meal.verification_source}")
                
                # Log to Opik for persistent storage
                if meal.actual_calories is not None:
                    await _log_verification_to_opik(
                        entry_id=entry_id,
                        actual_calories=meal.actual_calories,
                        estimated_calories=meal.total_calories,
                        verification_source=meal.verification_source or "unknown"
                    )
                
                return {
                    "status": "success",
                    "entry_id": entry_id,
                    "verified_at": meal.verified_at.isoformat(),
                    "verification_source": meal.verification_source,
                    "comparison": {
                        "calories": {
                            "estimated": meal.total_calories,
                            "actual": meal.actual_calories,
                            "error": cal_error,
                            "error_percent": cal_pct
                        },
                        "protein": {
                            "estimated": meal.total_protein,
                            "actual": meal.actual_protein,
                            "error": protein_error,
                            "error_percent": protein_pct
                        } if meal.actual_protein else None,
                        "carbs": {
                            "estimated": meal.total_carbs,
                            "actual": meal.actual_carbs,
                            "error": carbs_error,
                            "error_percent": carbs_pct
                        } if meal.actual_carbs else None,
                        "fat": {
                            "estimated": meal.total_fat,
                            "actual": meal.actual_fat,
                            "error": fat_error,
                            "error_percent": fat_pct
                        } if meal.actual_fat else None,
                    }
                }
    
    raise HTTPException(status_code=404, detail=f"Meal {entry_id} not found")


async def _log_verification_to_opik(
    entry_id: str, 
    actual_calories: float,
    estimated_calories: float,
    verification_source: str
):
    """
    Log verified meal data to Opik as feedback scores.
    
    This ensures ground truth data is persisted for calibration even if
    the local storage is reset.
    """
    try:
        from opik import Opik
        import os
        
        client = Opik()
        rest_client = client._rest_client
        project_name = os.getenv("OPIK_PROJECT_NAME", "nutripilot")
        
        # Search for the span with this entry_id in metadata or by finding
        # the orchestrator.process span that matches this meal
        # For now, we'll use the entry_id as a correlation key
        
        # Calculate error metrics
        error = estimated_calories - actual_calories
        error_pct = round(error / actual_calories * 100, 1) if actual_calories > 0 else 0
        
        # Log as a feedback score to the most recent matching span
        # First find recent orchestrator.process spans
        result = rest_client.spans.get_spans_by_project(
            project_name=project_name,
            size=50
        )
        
        if hasattr(result, 'content') and result.content:
            # Find spans that might match (by timestamp proximity or output content)
            orch_spans = [s for s in result.content if getattr(s, 'name', '') == 'orchestrator.process']
            
            for span in orch_spans[:10]:
                span_id = getattr(span, 'id', None)
                
                # Check if this span has matching calories in output
                output = getattr(span, 'output', {})
                if isinstance(output, dict):
                    out = output.get('output', output)
                    if isinstance(out, dict):
                        for n in out.get('total_nutrients', []):
                            if isinstance(n, dict) and n.get('name', '').lower() == 'calories':
                                span_calories = n.get('amount', 0)
                                # Match if estimated calories are close
                                if abs(span_calories - estimated_calories) < 1:
                                    # Found matching span - add feedback score
                                    rest_client.spans.add_span_feedback_score(
                                        id=span_id,
                                        name="verified_calories",
                                        value=actual_calories,
                                        source="user_verification",
                                        reason=f"Verified via {verification_source}"
                                    )
                                    
                                    rest_client.spans.add_span_feedback_score(
                                        id=span_id,
                                        name="calorie_error",
                                        value=error,
                                        source="user_verification",
                                        reason=f"Error: {error:.1f} cal ({error_pct:.1f}%)"
                                    )
                                    
                                    logger.info(f"📊 Logged verification to Opik span {span_id[:8]}")
                                    return True
        
        logger.warning("⚠️ Could not find matching Opik span for verification")
        return False
        
    except Exception as e:
        logger.error(f"❌ Failed to log verification to Opik: {e}")
        return False


@app.get("/calibration/status", tags=["calibration"])
async def get_calibration_status():
    """Get overall calibration status and recent metrics."""
    # Count meals with verified calories
    verified_count = 0
    total_count = 0
    
    for user_id, meals in storage._meal_logs.items():
        for meal in meals:
            total_count += 1
            if meal.actual_calories is not None:
                verified_count += 1
    
    return {
        "total_meals": total_count,
        "verified_meals": verified_count,
        "verification_rate": round(verified_count / total_count * 100, 1) if total_count > 0 else 0,
        "ready_for_calibration": verified_count >= 5,
        "message": f"{verified_count}/{total_count} meals have verified calories"
    }


# === Run with Uvicorn ===
if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )

