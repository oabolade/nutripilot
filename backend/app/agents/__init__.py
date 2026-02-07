"""
NutriPilot AI - Agents Module

Specialized agents for the Observe-Think-Act pipeline:
- VisionAnalyst: Image analysis with Gemini Vision
- BioDataScout: Health constraint queries (mock HealthKit)
- NutriAuditor: Nutrition data validation (USDA API)
- GoalEvaluator: Goal alignment scoring
- NutriCalibrator: Accuracy calibration and prompt improvement
"""

from app.agents.vision_analyst import VisionAnalyst
from app.agents.biodata_scout import BioDataScout
from app.agents.nutri_auditor import NutriAuditor
from app.agents.goal_evaluator import GoalEvaluator
from app.agents.nutri_calibrator import NutriCalibrator

__all__ = ["VisionAnalyst", "BioDataScout", "NutriAuditor", "GoalEvaluator", "NutriCalibrator"]

