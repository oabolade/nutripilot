"""
NutriPilot AI - Calibration Report Models

Data structures for nutrition calibration and accuracy assessment.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class CalibrationStatus(str, Enum):
    """Status of the calibration assessment."""
    EXCELLENT = "excellent"  # MAE < 5%
    GOOD = "good"            # MAE 5-10%
    NEEDS_IMPROVEMENT = "needs_improvement"  # MAE 10-15%
    POOR = "poor"            # MAE > 15%


class PromptSuggestion(BaseModel):
    """Suggested improvement for the Gemini prompt."""
    category: str = Field(..., description="Category of improvement (e.g., 'portion_estimation', 'food_identification')")
    current_issue: str = Field(..., description="What's currently going wrong")
    suggested_change: str = Field(..., description="Recommended prompt modification")
    priority: int = Field(default=2, ge=1, le=3, description="1=High, 2=Medium, 3=Low")
    expected_impact: str = Field(..., description="Expected improvement after applying this change")


class CalibrationMetrics(BaseModel):
    """Statistical metrics from calibration analysis."""
    # Error metrics
    mean_absolute_error: float = Field(..., ge=0, description="Mean Absolute Error (MAE) in calories")
    mean_absolute_percentage_error: float = Field(..., ge=0, description="MAPE as percentage")
    root_mean_squared_error: float = Field(..., ge=0, description="RMSE in calories")
    
    # Calibration metrics
    brier_score: Optional[float] = Field(default=None, description="Brier score for probability calibration")
    expected_calibration_error: Optional[float] = Field(default=None, description="ECE for calibration quality")
    
    # Correlation
    pearson_correlation: float = Field(default=0, description="Correlation between estimated and actual")
    r_squared: float = Field(default=0, ge=0, le=1, description="R² coefficient of determination")
    
    # Distribution stats
    bias: float = Field(default=0, description="Average over/under estimation (positive = overestimate)")
    std_deviation: float = Field(default=0, description="Standard deviation of errors")


class MealCalibrationData(BaseModel):
    """A single meal's calibration data point."""
    entry_id: str
    timestamp: datetime
    food_names: list[str]
    estimated_calories: float
    actual_calories: float
    error: float  # estimated - actual
    percentage_error: float
    confidence: float = Field(default=0.7, description="Model's confidence in the estimate")


class CalibrationReport(BaseModel):
    """Complete calibration report with metrics and suggestions."""
    # Metadata
    report_id: str = Field(..., description="Unique report identifier")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: str
    meals_analyzed: int
    
    # Status
    status: CalibrationStatus
    status_message: str
    
    # Metrics
    metrics: CalibrationMetrics
    
    # Breakdown by error type
    overestimation_count: int = 0
    underestimation_count: int = 0
    accurate_count: int = 0  # Within 5% error
    
    # Problem areas
    worst_categories: list[str] = Field(
        default_factory=list,
        description="Food categories with highest error rates"
    )
    
    # Improvement suggestions
    suggestions: list[PromptSuggestion] = Field(
        default_factory=list,
        description="Recommended prompt improvements"
    )
    
    # Raw data (optional, for debugging)
    data_points: list[MealCalibrationData] = Field(
        default_factory=list,
        description="Individual calibration data points"
    )
    
    # Reliability diagram path (if generated)
    reliability_diagram_path: Optional[str] = None
