"""
NutriPilot AI - MealState Pydantic Schema

This module defines the type-safe data structures for state hand-offs
between agents in the Observe-Think-Act pipeline.

Imported from the core project state.py for backend use.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
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
    """Individual nutrient measurement."""
    name: str = Field(..., description="Nutrient name (e.g., 'protein', 'vitamin_c')")
    amount: float = Field(..., ge=0, description="Quantity of the nutrient")
    unit: str = Field(default="g", description="Unit of measurement")
    percent_daily: Optional[float] = Field(
        default=None, 
        ge=0, 
        le=1000,
        description="Percentage of daily recommended value"
    )


class BoundingBox(BaseModel):
    """Normalized bounding box coordinates."""
    x1: float = Field(..., ge=0, le=1, description="Left edge")
    y1: float = Field(..., ge=0, le=1, description="Top edge")
    x2: float = Field(..., ge=0, le=1, description="Right edge")
    y2: float = Field(..., ge=0, le=1, description="Bottom edge")


class FoodItem(BaseModel):
    """A single detected food item from image analysis."""
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
    nutrients: list[NutrientInfo] = Field(
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


class ConstraintStatus(str, Enum):
    """Health constraint alert levels."""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


class HealthConstraint(BaseModel):
    """User health constraint from BioData integration."""
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


class AdjustmentAction(str, Enum):
    """Types of meal adjustments."""
    REDUCE = "reduce"
    REPLACE = "replace"
    REMOVE = "remove"
    ADD = "add"


class MealAdjustment(BaseModel):
    """Suggested modification to improve the meal."""
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


class MealState(BaseModel):
    """
    Primary state object passed between agents.
    
    Represents the complete understanding of a meal analysis session,
    accumulating data through Observe → Think → Act phases.
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
    detected_foods: list[FoodItem] = Field(
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
    health_constraints: list[HealthConstraint] = Field(
        default_factory=list,
        description="Active health constraints for this user"
    )
    total_nutrients: list[NutrientInfo] = Field(
        default_factory=list,
        description="Aggregated nutritional totals for the meal"
    )
    constraint_violations: list[str] = Field(
        default_factory=list,
        description="List of violated health constraints"
    )
    
    # === Act Phase Outputs ===
    adjustments: list[MealAdjustment] = Field(
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
    agent_calls: list[str] = Field(
        default_factory=list,
        description="Ordered list of agents consulted"
    )
    processing_time_ms: Optional[int] = Field(
        default=None,
        ge=0,
        description="Total processing time in milliseconds"
    )


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
    foods: list[FoodItem] = Field(default_factory=list)
    ocr_text: Optional[str] = Field(default=None)
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    model_used: str = Field(default="gemini-2.0-flash")
    latency_ms: int = Field(default=0, ge=0)


class BioDataQuery(BaseModel):
    """Input to BioDataScout agent."""
    user_id: str = Field(...)
    constraint_types: Optional[list[str]] = Field(
        default=None,
        description="Specific constraints to query (None = all)"
    )


class BioDataReport(BaseModel):
    """Output from BioDataScout agent."""
    user_id: str = Field(...)
    constraints: list[HealthConstraint] = Field(default_factory=list)
    alerts: list[str] = Field(
        default_factory=list,
        description="Critical health alerts requiring immediate attention"
    )
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class NutriAuditRequest(BaseModel):
    """Input to NutriAuditor agent."""
    foods: list[FoodItem] = Field(...)
    user_constraints: list[HealthConstraint] = Field(default_factory=list)
    daily_targets: Optional[dict] = Field(
        default=None,
        description="User's daily nutritional targets"
    )


class NutriAuditReport(BaseModel):
    """Output from NutriAuditor agent."""
    total_nutrients: list[NutrientInfo] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    suggestions: list[MealAdjustment] = Field(default_factory=list)
    foods_matched: int = Field(default=0, ge=0)
    foods_unmatched: list[str] = Field(default_factory=list)
