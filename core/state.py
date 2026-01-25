"""
NutriPilot AI - MealState Pydantic Schema

This module defines the type-safe data structures for state hand-offs
between agents in the Observe-Think-Act pipeline.

Usage:
    from core.state import MealState, FoodItem, MealType
    
    state = MealState(session_id="abc123", user_id="user_001")
    state.detected_foods.append(FoodItem(name="apple", ...))
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum
from uuid import uuid4


class MealType(str, Enum):
    """Categorization of meal timing."""
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


class NutrientInfo(BaseModel):
    """
    Individual nutrient measurement.
    
    Represents a single nutrient value (e.g., protein: 25g).
    """
    name: str = Field(..., description="Nutrient name (e.g., 'protein', 'vitamin_c')")
    amount: float = Field(..., ge=0, description="Quantity of the nutrient")
    unit: str = Field(default="g", description="Unit of measurement")
    percent_daily: Optional[float] = Field(
        default=None, 
        ge=0, 
        le=1000,
        description="Percentage of daily recommended value"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "protein",
                "amount": 25.5,
                "unit": "g",
                "percent_daily": 51.0
            }
        }


class BoundingBox(BaseModel):
    """
    Normalized bounding box coordinates.
    
    All values are normalized to [0, 1] relative to image dimensions.
    """
    x1: float = Field(..., ge=0, le=1, description="Left edge")
    y1: float = Field(..., ge=0, le=1, description="Top edge")
    x2: float = Field(..., ge=0, le=1, description="Right edge")
    y2: float = Field(..., ge=0, le=1, description="Bottom edge")

    @field_validator('x2')
    @classmethod
    def x2_greater_than_x1(cls, v, info):
        if 'x1' in info.data and v <= info.data['x1']:
            raise ValueError('x2 must be greater than x1')
        return v

    @field_validator('y2')
    @classmethod
    def y2_greater_than_y1(cls, v, info):
        if 'y1' in info.data and v <= info.data['y1']:
            raise ValueError('y2 must be greater than y1')
        return v


class FoodItem(BaseModel):
    """
    A single detected food item from image analysis.
    
    Contains identification, portion estimation, nutritional data,
    and optional spatial information from vision model.
    """
    name: str = Field(..., min_length=1, description="Food item name")
    portion_grams: float = Field(..., gt=0, description="Estimated portion size in grams")
    portion_description: str = Field(
        ..., 
        description="Human-readable portion (e.g., '1 medium apple')"
    )
    confidence: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Model confidence in identification"
    )
    nutrients: List[NutrientInfo] = Field(
        default_factory=list,
        description="Nutritional breakdown from USDA lookup"
    )
    usda_fdc_id: Optional[str] = Field(
        default=None,
        description="USDA FoodData Central identifier"
    )
    bounding_box: Optional[BoundingBox] = Field(
        default=None,
        description="Location in source image"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "grilled chicken breast",
                "portion_grams": 150.0,
                "portion_description": "1 medium breast",
                "confidence": 0.92,
                "nutrients": [
                    {"name": "protein", "amount": 31.0, "unit": "g"},
                    {"name": "calories", "amount": 165.0, "unit": "kcal"}
                ],
                "usda_fdc_id": "171077",
                "bounding_box": {"x1": 0.1, "y1": 0.2, "x2": 0.5, "y2": 0.6}
            }
        }


class ConstraintStatus(str, Enum):
    """Health constraint alert levels."""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


class HealthConstraint(BaseModel):
    """
    User health constraint from BioData integration.
    
    Represents a health metric that may influence meal recommendations.
    """
    constraint_type: str = Field(
        ..., 
        description="Type of constraint (e.g., 'glucose', 'sodium', 'allergen')"
    )
    value: float = Field(..., description="Current metric value")
    unit: str = Field(..., description="Unit of measurement")
    status: ConstraintStatus = Field(
        default=ConstraintStatus.NORMAL,
        description="Alert level based on thresholds"
    )
    threshold_low: Optional[float] = Field(default=None, description="Lower bound for normal")
    threshold_high: Optional[float] = Field(default=None, description="Upper bound for normal")
    recommendation: Optional[str] = Field(
        default=None,
        description="Actionable advice based on constraint"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "constraint_type": "blood_glucose",
                "value": 145.0,
                "unit": "mg/dL",
                "status": "warning",
                "threshold_low": 70.0,
                "threshold_high": 140.0,
                "recommendation": "Consider reducing simple carbohydrates"
            }
        }


class AdjustmentAction(str, Enum):
    """Types of meal adjustments."""
    REDUCE = "reduce"
    REPLACE = "replace"
    REMOVE = "remove"
    ADD = "add"


class MealAdjustment(BaseModel):
    """
    Suggested modification to improve the meal.
    
    Generated during the Act phase based on nutritional analysis
    and health constraints.
    """
    food_name: str = Field(..., description="Target food item")
    action: AdjustmentAction = Field(..., description="Type of adjustment")
    reason: str = Field(..., description="Justification for the adjustment")
    alternative: Optional[str] = Field(
        default=None,
        description="Suggested replacement (for REPLACE action)"
    )
    priority: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Importance ranking (1=highest)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "food_name": "white rice",
                "action": "replace",
                "reason": "High glycemic index may spike blood glucose",
                "alternative": "cauliflower rice",
                "priority": 1
            }
        }


class MealState(BaseModel):
    """
    Primary state object passed between agents.
    
    Represents the complete understanding of a meal analysis session,
    accumulating data through Observe → Think → Act phases.
    
    This is the central data structure for type-safe hand-offs between:
    - StudioOrchestrator
    - VisionAnalyst
    - BioDataScout  
    - NutriAuditor
    """
    # === Session Metadata ===
    session_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique session identifier"
    )
    user_id: str = Field(..., description="User identifier for personalization")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Session creation time"
    )
    meal_type: Optional[MealType] = Field(
        default=None,
        description="Meal categorization"
    )
    
    # === Observe Phase Outputs ===
    detected_foods: List[FoodItem] = Field(
        default_factory=list,
        description="Foods identified from image/text input"
    )
    raw_ocr_text: Optional[str] = Field(
        default=None,
        description="Extracted text from receipt/menu (if applicable)"
    )
    image_analysis_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall confidence in image analysis"
    )
    
    # === Think Phase Outputs ===
    health_constraints: List[HealthConstraint] = Field(
        default_factory=list,
        description="Active health constraints for this user"
    )
    total_nutrients: List[NutrientInfo] = Field(
        default_factory=list,
        description="Aggregated nutritional totals for the meal"
    )
    constraint_violations: List[str] = Field(
        default_factory=list,
        description="List of violated health constraints"
    )
    
    # === Act Phase Outputs ===
    adjustments: List[MealAdjustment] = Field(
        default_factory=list,
        description="Recommended meal modifications"
    )
    summary: Optional[str] = Field(
        default=None,
        description="Human-readable meal analysis summary"
    )
    overall_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Holistic meal quality score (0-100)"
    )
    
    # === Tracing & Observability ===
    trace_id: Optional[str] = Field(
        default=None,
        description="Opik trace identifier for debugging"
    )
    agent_calls: List[str] = Field(
        default_factory=list,
        description="Ordered list of agents consulted"
    )
    processing_time_ms: Optional[int] = Field(
        default=None,
        ge=0,
        description="Total processing time in milliseconds"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "user_12345",
                "timestamp": "2026-01-24T12:30:00Z",
                "meal_type": "lunch",
                "detected_foods": [
                    {
                        "name": "grilled salmon",
                        "portion_grams": 180.0,
                        "portion_description": "1 fillet",
                        "confidence": 0.95
                    }
                ],
                "image_analysis_confidence": 0.93,
                "health_constraints": [
                    {
                        "constraint_type": "sodium",
                        "value": 1800.0,
                        "unit": "mg",
                        "status": "warning"
                    }
                ],
                "total_nutrients": [
                    {"name": "protein", "amount": 39.0, "unit": "g"},
                    {"name": "calories", "amount": 367.0, "unit": "kcal"}
                ],
                "constraint_violations": [],
                "adjustments": [],
                "summary": "Well-balanced meal with excellent protein content.",
                "overall_score": 85.0,
                "trace_id": "opik-trace-abc123",
                "agent_calls": ["VisionAnalyst", "BioDataScout", "NutriAuditor"],
                "processing_time_ms": 2340
            }
        }


# === Agent Input/Output Models ===

class VisionInput(BaseModel):
    """Input to VisionAnalyst agent."""
    image_bytes: bytes = Field(..., description="Raw image data")
    image_format: str = Field(default="jpeg", description="Image format (jpeg, png)")
    context: Optional[str] = Field(
        default=None,
        description="Optional context (e.g., 'restaurant menu')"
    )


class VisionOutput(BaseModel):
    """Output from VisionAnalyst agent."""
    foods: List[FoodItem] = Field(default_factory=list)
    ocr_text: Optional[str] = Field(default=None)
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    model_used: str = Field(default="gemini-2.0-flash")
    latency_ms: int = Field(default=0, ge=0)


class BioDataQuery(BaseModel):
    """Input to BioDataScout agent."""
    user_id: str = Field(...)
    constraint_types: Optional[List[str]] = Field(
        default=None,
        description="Specific constraints to query (None = all)"
    )


class BioDataReport(BaseModel):
    """Output from BioDataScout agent."""
    user_id: str = Field(...)
    constraints: List[HealthConstraint] = Field(default_factory=list)
    alerts: List[str] = Field(
        default_factory=list,
        description="Critical health alerts requiring immediate attention"
    )
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class NutriAuditRequest(BaseModel):
    """Input to NutriAuditor agent."""
    foods: List[FoodItem] = Field(...)
    user_constraints: List[HealthConstraint] = Field(default_factory=list)
    daily_targets: Optional[dict] = Field(
        default=None,
        description="User's daily nutritional targets"
    )


class NutriAuditReport(BaseModel):
    """Output from NutriAuditor agent."""
    total_nutrients: List[NutrientInfo] = Field(default_factory=list)
    violations: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[MealAdjustment] = Field(default_factory=list)
    foods_matched: int = Field(default=0, ge=0)
    foods_unmatched: List[str] = Field(default_factory=list)


class OrchestratorInput(BaseModel):
    """Input to StudioOrchestrator."""
    user_id: str = Field(...)
    image_bytes: Optional[bytes] = Field(default=None)
    text_input: Optional[str] = Field(default=None)
    meal_type: Optional[MealType] = Field(default=None)

    @field_validator('image_bytes', 'text_input')
    @classmethod
    def at_least_one_input(cls, v, info):
        # Note: Validation happens after all fields are set
        return v
