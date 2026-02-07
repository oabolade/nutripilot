"""
NutriPilot AI - User Goals & Profile Models

Defines data structures for user personalization including:
- Health goals (weight loss, glycemic control, etc.)
- Health conditions (diabetes, hypertension, etc.)
- Daily nutrient targets
- Meal logging for progress tracking
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum
from uuid import uuid4


class HealthGoal(str, Enum):
    """User-defined health objectives."""
    WEIGHT_LOSS = "weight_loss"
    WEIGHT_GAIN = "weight_gain"
    GLYCEMIC_CONTROL = "glycemic_control"  # Blood sugar management
    LOWER_CHOLESTEROL = "lower_cholesterol"
    HEART_HEALTH = "heart_health"
    MUSCLE_BUILDING = "muscle_building"
    GENERAL_WELLNESS = "general_wellness"


class HealthCondition(str, Enum):
    """Known health conditions affecting dietary needs."""
    TYPE_2_DIABETES = "type_2_diabetes"
    TYPE_1_DIABETES = "type_1_diabetes"
    HYPERTENSION = "hypertension"
    HIGH_CHOLESTEROL = "high_cholesterol"
    CELIAC_DISEASE = "celiac_disease"
    LACTOSE_INTOLERANT = "lactose_intolerant"
    KIDNEY_DISEASE = "kidney_disease"
    NONE = "none"


class DailyNutrientTargets(BaseModel):
    """Customizable daily nutritional targets."""
    calories: int = Field(default=2000, ge=1000, le=5000, description="Daily calorie target")
    protein_g: int = Field(default=50, ge=10, le=300, description="Protein target in grams")
    carbs_g: int = Field(default=250, ge=20, le=500, description="Carbohydrate target in grams")
    fat_g: int = Field(default=65, ge=10, le=200, description="Fat target in grams")
    fiber_g: int = Field(default=25, ge=10, le=60, description="Fiber target in grams")
    sodium_mg: int = Field(default=2300, ge=500, le=4000, description="Sodium target in mg")
    sugar_g: int = Field(default=50, ge=0, le=150, description="Sugar limit in grams")


class UserProfile(BaseModel):
    """Complete user profile with goals and preferences."""
    user_id: str = Field(..., description="Unique user identifier")
    display_name: Optional[str] = Field(default=None, description="User's display name")
    
    # Goals and conditions
    goals: list[HealthGoal] = Field(default_factory=list, description="Active health goals")
    conditions: list[HealthCondition] = Field(default_factory=list, description="Health conditions")
    dietary_restrictions: list[str] = Field(
        default_factory=list, 
        description="Dietary restrictions (e.g., 'vegetarian', 'nut-free')"
    )
    
    # Nutrient targets
    daily_targets: DailyNutrientTargets = Field(
        default_factory=DailyNutrientTargets,
        description="Customized daily nutritional targets"
    )
    
    # Timeline
    timeline_weeks: int = Field(default=12, ge=1, le=52, description="Goal timeline in weeks")
    start_date: datetime = Field(default_factory=datetime.utcnow, description="When goals were set")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MealLogEntry(BaseModel):
    """A logged meal for progress tracking."""
    entry_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique entry ID")
    user_id: str = Field(..., description="User who logged the meal")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When meal was logged")
    meal_type: str = Field(default="snack", description="Type of meal")
    
    # Meal data (from analysis)
    food_names: list[str] = Field(default_factory=list, description="Detected food items")
    total_calories: float = Field(default=0, ge=0, description="Total calories")
    total_protein: float = Field(default=0, ge=0, description="Total protein in grams")
    total_carbs: float = Field(default=0, ge=0, description="Total carbs in grams")
    total_fat: float = Field(default=0, ge=0, description="Total fat in grams")
    total_fiber: float = Field(default=0, ge=0, description="Total fiber in grams")
    total_sodium: float = Field(default=0, ge=0, description="Total sodium in mg")
    
    # Scores
    meal_score: float = Field(default=0, ge=0, le=100, description="Overall meal quality score")
    goal_alignment_score: float = Field(
        default=0, ge=0, le=100, 
        description="How well meal aligns with user's goals"
    )
    
    # Ground truth for calibration (user-verified)
    is_verified: bool = Field(default=False, description="Whether user verified the nutrition data")
    verified_at: Optional[datetime] = Field(default=None, description="When verification was done")
    actual_calories: Optional[float] = Field(default=None, ge=0, description="Verified calories")
    actual_protein: Optional[float] = Field(default=None, ge=0, description="Verified protein (g)")
    actual_carbs: Optional[float] = Field(default=None, ge=0, description="Verified carbs (g)")
    actual_fat: Optional[float] = Field(default=None, ge=0, description="Verified fat (g)")
    actual_fiber: Optional[float] = Field(default=None, ge=0, description="Verified fiber (g)")
    actual_sodium: Optional[float] = Field(default=None, ge=0, description="Verified sodium (mg)")
    verification_source: Optional[str] = Field(
        default=None, 
        description="Source of verification (e.g., 'nutrition_label', 'food_scale', 'recipe_calculation')"
    )
    verification_notes: Optional[str] = Field(default=None, description="User notes about verification")
    
    # Feedback
    goal_feedback: list[str] = Field(
        default_factory=list,
        description="Goal-specific feedback messages"
    )


class GoalEvaluation(BaseModel):
    """Result of evaluating a meal against user goals."""
    alignment_score: float = Field(default=0, ge=0, le=100, description="Overall goal alignment")
    goal_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Individual score per goal (0-100)"
    )
    feedback: list[str] = Field(
        default_factory=list,
        description="Goal-specific feedback messages"
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Actionable recommendations based on goals"
    )


class DashboardData(BaseModel):
    """Aggregated data for the user dashboard."""
    user_id: str
    profile: Optional[UserProfile] = None
    
    # Progress metrics
    days_active: int = Field(default=0, description="Days since goal start")
    meals_logged: int = Field(default=0, description="Total meals logged")
    average_meal_score: float = Field(default=0, description="Average meal quality")
    average_goal_alignment: float = Field(default=0, description="Average goal alignment")
    
    # Goal progress (mock for now, can be extended)
    goal_progress: dict[str, float] = Field(
        default_factory=dict,
        description="Progress percentage per goal (0-100)"
    )
    
    # Nutrient trends (daily averages vs targets)
    nutrient_trends: dict[str, dict] = Field(
        default_factory=dict,
        description="Nutrient intake vs targets over time"
    )
    
    # Recent meals
    recent_meals: list[MealLogEntry] = Field(
        default_factory=list,
        description="Most recent meal entries"
    )


# Goal-specific nutrient rules for evaluation
GOAL_NUTRIENT_RULES: dict[HealthGoal, dict] = {
    HealthGoal.WEIGHT_LOSS: {
        "calories": {"max_percent": 90, "weight": 0.4},  # Stay under calorie target
        "protein": {"min_percent": 100, "weight": 0.3},  # Hit protein target
        "fiber": {"min_percent": 100, "weight": 0.2},    # High fiber for satiety
        "sugar": {"max_percent": 80, "weight": 0.1},     # Limit sugar
    },
    HealthGoal.GLYCEMIC_CONTROL: {
        "sugar": {"max_percent": 60, "weight": 0.4},     # Strict sugar limit
        "carbs": {"max_percent": 80, "weight": 0.3},     # Moderate carbs
        "fiber": {"min_percent": 120, "weight": 0.2},    # High fiber slows glucose
        "protein": {"min_percent": 100, "weight": 0.1},  # Protein helps stability
    },
    HealthGoal.LOWER_CHOLESTEROL: {
        "fiber": {"min_percent": 120, "weight": 0.4},    # High fiber reduces cholesterol
        "fat": {"max_percent": 80, "weight": 0.3},       # Limit total fat
        "sodium": {"max_percent": 90, "weight": 0.2},    # Watch sodium
        "protein": {"min_percent": 90, "weight": 0.1},   # Lean protein
    },
    HealthGoal.HEART_HEALTH: {
        "sodium": {"max_percent": 70, "weight": 0.4},    # Low sodium critical
        "fiber": {"min_percent": 100, "weight": 0.3},    # Heart-healthy fiber
        "fat": {"max_percent": 85, "weight": 0.2},       # Moderate fat
        "sugar": {"max_percent": 80, "weight": 0.1},     # Limit sugar
    },
    HealthGoal.WEIGHT_GAIN: {
        "calories": {"min_percent": 120, "weight": 0.4},  # Caloric surplus needed
        "protein": {"min_percent": 130, "weight": 0.35},  # High protein for growth
        "carbs": {"min_percent": 110, "weight": 0.25},    # Carbs for energy and mass
    },
    HealthGoal.MUSCLE_BUILDING: {
        "protein": {"min_percent": 150, "weight": 0.5},  # High protein
        "calories": {"min_percent": 100, "weight": 0.3}, # Meet calorie needs
        "carbs": {"min_percent": 100, "weight": 0.2},    # Carbs for energy
    },
    HealthGoal.GENERAL_WELLNESS: {
        "protein": {"min_percent": 90, "weight": 0.25},
        "fiber": {"min_percent": 90, "weight": 0.25},
        "sodium": {"max_percent": 100, "weight": 0.25},
        "sugar": {"max_percent": 100, "weight": 0.25},
    },
}


# Condition-specific restrictions
CONDITION_RESTRICTIONS: dict[HealthCondition, dict] = {
    HealthCondition.TYPE_2_DIABETES: {
        "sugar_max_g": 25,
        "carbs_max_g": 150,
        "warnings": ["Avoid high-glycemic foods", "Monitor carbohydrate portions"],
    },
    HealthCondition.TYPE_1_DIABETES: {
        "sugar_max_g": 30,
        "warnings": ["Count carbohydrates carefully", "Monitor blood glucose after meals"],
    },
    HealthCondition.HYPERTENSION: {
        "sodium_max_mg": 1500,
        "warnings": ["Limit processed foods", "Avoid added salt"],
    },
    HealthCondition.HIGH_CHOLESTEROL: {
        "fat_max_g": 50,
        "warnings": ["Limit saturated fats", "Choose lean proteins"],
    },
    HealthCondition.CELIAC_DISEASE: {
        "avoid_foods": ["wheat", "barley", "rye", "bread", "pasta"],
        "warnings": ["Avoid gluten-containing foods"],
    },
    HealthCondition.LACTOSE_INTOLERANT: {
        "avoid_foods": ["milk", "cheese", "yogurt", "ice cream"],
        "warnings": ["Choose lactose-free dairy alternatives"],
    },
    HealthCondition.KIDNEY_DISEASE: {
        "sodium_max_mg": 1500,
        "protein_max_g": 50,
        "warnings": ["Limit sodium and protein intake", "Monitor phosphorus"],
    },
}
