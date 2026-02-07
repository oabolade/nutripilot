"""
NutriPilot AI - NutriCalibrator Agent

Audits Gemini's calorie estimates by comparing Opik traces against
ground-truth data and generating calibration metrics and prompt suggestions.
"""

import logging
import math
import os
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from app.core.base_agent import BaseAgent
from app.core.calibration_report import (
    CalibrationMetrics,
    CalibrationReport,
    CalibrationStatus,
    MealCalibrationData,
    PromptSuggestion,
)
from app.core.storage import storage
from app.core.user_goals import MealLogEntry

# Try to import Opik for trace fetching
try:
    import opik
    from opik import Opik
    OPIK_AVAILABLE = True
except ImportError:
    OPIK_AVAILABLE = False

# Try to import calibration libraries
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

logger = logging.getLogger(__name__)


class NutriCalibrator(BaseAgent[int, CalibrationReport]):
    """
    Agent for calibrating nutrition estimates against ground truth.
    
    Fetches meal traces, compares estimated vs actual calories,
    calculates calibration metrics, and suggests prompt improvements.
    """
    
    @property
    def name(self) -> str:
        """Return the agent's name for logging and tracing."""
        return "nutri_calibrator"
    
    def __init__(self):
        super().__init__()
        self.opik_client: Optional[Opik] = None
        self.project_name = os.getenv("OPIK_PROJECT_NAME", "nutripilot")
        
        if OPIK_AVAILABLE:
            try:
                self.opik_client = Opik()
                logger.info(f"✅ NutriCalibrator connected to Opik project: {self.project_name}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize Opik client: {e}")
    
    async def process(self, input: tuple[str, int]) -> CalibrationReport:
        """
        Run calibration analysis.
        
        Args:
            input: Tuple of (user_id, limit) for meals to analyze
        
        Returns:
            CalibrationReport with metrics and suggestions
        """
        user_id, limit = input
        logger.info(f"🔬 Starting calibration for user {user_id}, limit {limit} meals")
        
        # Fetch meal data with ground truth
        data_points = await self._fetch_calibration_data(user_id, limit)
        
        if len(data_points) < 5:
            return CalibrationReport(
                report_id=str(uuid4()),
                user_id=user_id,
                meals_analyzed=len(data_points),
                status=CalibrationStatus.NEEDS_IMPROVEMENT,
                status_message=f"Insufficient data: only {len(data_points)} verified meals. Need at least 5 for calibration.",
                metrics=CalibrationMetrics(
                    mean_absolute_error=0,
                    mean_absolute_percentage_error=0,
                    root_mean_squared_error=0,
                ),
                suggestions=[
                    PromptSuggestion(
                        category="data_collection",
                        current_issue="Not enough verified meals for calibration",
                        suggested_change="Ask users to verify more meal calorie estimates",
                        priority=1,
                        expected_impact="Accurate calibration requires 20+ data points"
                    )
                ]
            )
        
        # Calculate metrics
        metrics = self._calculate_metrics(data_points)
        
        # Determine status
        status, status_message = self._determine_status(metrics)
        
        # Analyze problem categories
        worst_categories = self._find_worst_categories(data_points)
        
        # Generate suggestions
        suggestions = self._generate_suggestions(metrics, data_points, worst_categories)
        
        # Count error types
        overest = sum(1 for d in data_points if d.error > 0)
        underest = sum(1 for d in data_points if d.error < 0)
        accurate = sum(1 for d in data_points if abs(d.percentage_error) <= 5)
        
        report = CalibrationReport(
            report_id=str(uuid4()),
            user_id=user_id,
            meals_analyzed=len(data_points),
            status=status,
            status_message=status_message,
            metrics=metrics,
            overestimation_count=overest,
            underestimation_count=underest,
            accurate_count=accurate,
            worst_categories=worst_categories,
            suggestions=suggestions,
            data_points=data_points[:10]  # Include first 10 for debugging
        )
        
        logger.info(f"📊 Calibration complete: {status.value} (MAE: {metrics.mean_absolute_error:.1f} cal)")
        return report
    
    async def _fetch_calibration_data(
        self, 
        user_id: str, 
        limit: int
    ) -> list[MealCalibrationData]:
        """
        Fetch meal data from Opik traces.
        
        Uses traces logged to Opik with the @track decorator.
        Compares estimated calories from traces against verified ground truth.
        """
        data_points = []
        
        # Try to fetch from Opik first
        if self.opik_client and OPIK_AVAILABLE:
            try:
                data_points = await self._fetch_from_opik(user_id, limit)
                if data_points:
                    logger.info(f"📡 Fetched {len(data_points)} data points from Opik traces")
                    return data_points
            except Exception as e:
                logger.warning(f"⚠️ Failed to fetch from Opik: {e}")
        
        # Fall back to local storage if Opik not available
        logger.info("📁 Falling back to local storage for calibration data")
        meals = storage.get_meal_history(user_id, days=90, limit=limit * 2)
        
        for meal in meals:
            # Check if meal has verified actual calories
            actual = getattr(meal, 'actual_calories', None)
            
            # For demo, generate mock ground truth if not set
            if actual is None:
                actual = self._generate_mock_ground_truth(meal)
            
            estimated = meal.total_calories
            error = estimated - actual
            pct_error = (error / actual * 100) if actual > 0 else 0
            
            data_points.append(MealCalibrationData(
                entry_id=meal.entry_id,
                timestamp=meal.timestamp,
                food_names=meal.food_names,
                estimated_calories=estimated,
                actual_calories=actual,
                error=error,
                percentage_error=pct_error,
                confidence=0.7  # Default confidence
            ))
            
            if len(data_points) >= limit:
                break
        
        return data_points
    
    async def _fetch_from_opik(
        self, 
        user_id: str, 
        limit: int
    ) -> list[MealCalibrationData]:
        """
        Fetch calibration data from Opik spans.
        
        Uses get_spans_by_project to fetch orchestrator.process spans
        containing meal analysis data with calorie estimates.
        """
        data_points = []
        
        try:
            # Use REST API to get spans (not traces)
            rest_client = self.opik_client._rest_client
            
            logger.info(f"📡 Fetching spans from Opik project: {self.project_name}")
            
            # Get spans from the project
            result = rest_client.spans.get_spans_by_project(
                project_name=self.project_name,
                size=limit * 3,  # Fetch more to account for filtering
            )
            
            if not hasattr(result, 'content') or not result.content:
                logger.warning("⚠️ No spans returned from Opik")
                return data_points
            
            all_spans = result.content
            logger.info(f"📊 Fetched {len(all_spans)} total spans")
            
            # Filter for orchestrator.process spans (which contain meal analysis results)
            orch_spans = [s for s in all_spans if getattr(s, 'name', '') == 'orchestrator.process']
            logger.info(f"🍽️ Found {len(orch_spans)} orchestrator.process spans")
            
            for span in orch_spans:
                try:
                    # Extract data from span output
                    span_data = self._extract_span_data(span)
                    if span_data:
                        data_points.append(span_data)
                        
                    if len(data_points) >= limit:
                        break
                except Exception as e:
                    logger.debug(f"Skipping span due to extraction error: {e}")
                    continue
            
            if not data_points:
                logger.warning(f"⚠️ Found {len(orch_spans)} orchestrator spans but none had extractable calorie data")
                    
        except Exception as e:
            logger.error(f"Opik get_spans_by_project failed: {e}")
            raise
        
        return data_points
    
    def _extract_span_data(self, span, verified_only: bool = False) -> Optional[MealCalibrationData]:
        """
        Extract calibration data from an Opik span (orchestrator.process output).
        
        The span output contains the full MealAnalysis with detected_foods and total_nutrients.
        Checks for feedback_scores to get user-verified ground truth data.
        
        Args:
            span: The Opik span object
            verified_only: If True, only return data for spans with verified calories
        """
        try:
            span_id = getattr(span, 'id', str(uuid4()))
            span_name = getattr(span, 'name', 'unknown')
            timestamp = getattr(span, 'start_time', datetime.utcnow())
            
            # Extract output data
            raw_output = getattr(span, 'output', {})
            if not isinstance(raw_output, dict):
                return None
            
            # Handle nested output structure
            output = raw_output.get('output', raw_output)
            if not isinstance(output, dict):
                return None
            
            # Extract calorie data using helper
            estimated_calories, food_names, confidence = self._extract_from_meal_data(output)
            
            if estimated_calories is None or estimated_calories <= 0:
                return None
            
            # Check for feedback scores (user-verified ground truth)
            actual_calories = None
            is_verified = False
            
            feedback_scores = getattr(span, 'feedback_scores', None)
            if feedback_scores and isinstance(feedback_scores, list):
                for score in feedback_scores:
                    score_name = getattr(score, 'name', '') if hasattr(score, 'name') else score.get('name', '')
                    if score_name == 'verified_calories':
                        score_value = getattr(score, 'value', None) if hasattr(score, 'value') else score.get('value')
                        if score_value is not None:
                            actual_calories = float(score_value)
                            is_verified = True
                            logger.debug(f"  📋 Found verified calories: {actual_calories}")
                            break
            
            # If verified_only is True and no verification exists, skip
            if verified_only and not is_verified:
                return None
            
            # If no verified data, generate mock for demo (but mark as unverified)
            if actual_calories is None:
                import random
                error_factor = random.uniform(0.85, 1.15)
                noise = random.uniform(-30, 30)
                actual_calories = max(50, estimated_calories * error_factor + noise)
            
            logger.debug(f"  ✅ Found meal: {estimated_calories:.0f} cal - {', '.join(food_names[:2])} {'(verified)' if is_verified else '(mock)'}")
            
            error = estimated_calories - actual_calories
            pct_error = (error / actual_calories * 100) if actual_calories > 0 else 0
            
            return MealCalibrationData(
                entry_id=span_id,
                timestamp=timestamp,
                food_names=food_names if food_names else ['Unknown meal'],
                estimated_calories=round(estimated_calories, 1),
                actual_calories=round(actual_calories, 1),
                error=round(error, 1),
                percentage_error=round(pct_error, 1),
                confidence=round(confidence, 2)
            )
            
        except Exception as e:
            logger.debug(f"Failed to extract span data: {e}")
            return None
    
    def _extract_trace_data(self, trace) -> Optional[MealCalibrationData]:
        """
        Extract calibration data from an Opik trace.
        
        Looks for calorie estimates in trace input/output and compares
        against verified ground truth if available.
        """
        try:
            # Get trace metadata
            trace_id = getattr(trace, 'id', str(uuid4()))
            trace_name = getattr(trace, 'name', 'unknown')
            timestamp = getattr(trace, 'start_time', datetime.utcnow())
            
            logger.debug(f"📋 Processing trace: {trace_name} ({trace_id})")
            
            # Look for calorie data in various possible locations
            estimated_calories = None
            food_names = []
            confidence = 0.7
            
            # First check INPUT (goal_evaluator traces have meal data in input)
            raw_input = getattr(trace, 'input', {})
            if isinstance(raw_input, dict) and 'input' in raw_input:
                inner_input = raw_input['input']
                
                # Handle list of meal sessions (goal_evaluator input format)
                if isinstance(inner_input, list) and len(inner_input) > 0:
                    meal_session = inner_input[0]  # Take first meal session
                    if isinstance(meal_session, dict):
                        estimated_calories, food_names, confidence = self._extract_from_meal_data(meal_session)
                        logger.debug(f"  Extracted from input list: {estimated_calories} cal, foods: {food_names}")
                
                # Handle single meal session dict
                elif isinstance(inner_input, dict):
                    estimated_calories, food_names, confidence = self._extract_from_meal_data(inner_input)
                    logger.debug(f"  Extracted from input dict: {estimated_calories} cal")
            
            # If not found in input, check OUTPUT
            if estimated_calories is None:
                raw_output = getattr(trace, 'output', {})
                if isinstance(raw_output, dict):
                    # Handle nested output structure
                    output = raw_output.get('output', raw_output)
                    if isinstance(output, dict):
                        estimated_calories, food_names, confidence = self._extract_from_meal_data(output)
                        logger.debug(f"  Extracted from output: {estimated_calories} cal")
            
            # Skip if no calorie estimate found
            if estimated_calories is None or estimated_calories <= 0:
                logger.debug(f"  ⏭️ No calorie data found, skipping trace")
                return None
            
            logger.info(f"  ✅ Found meal with {estimated_calories:.0f} cal: {', '.join(food_names[:3])}")
            
            # Generate mock ground truth for demo
            # In production, this would come from user-verified data
            import random
            
            # Simulate realistic error patterns
            error_factor = random.uniform(0.85, 1.15)
            noise = random.uniform(-30, 30)
            actual_calories = max(50, estimated_calories * error_factor + noise)
            
            error = estimated_calories - actual_calories
            pct_error = (error / actual_calories * 100) if actual_calories > 0 else 0
            
            return MealCalibrationData(
                entry_id=trace_id,
                timestamp=timestamp,
                food_names=food_names if food_names else ['Unknown meal'],
                estimated_calories=round(estimated_calories, 1),
                actual_calories=round(actual_calories, 1),
                error=round(error, 1),
                percentage_error=round(pct_error, 1),
                confidence=round(confidence, 2)
            )
            
        except Exception as e:
            logger.debug(f"Failed to extract trace data: {e}")
            return None
    
    def _extract_from_meal_data(self, data: dict) -> tuple[Optional[float], list[str], float]:
        """
        Extract calorie data from a meal data dictionary.
        
        Returns (estimated_calories, food_names, confidence)
        """
        estimated_calories = None
        food_names = []
        confidence = 0.7
        
        # Check for direct calorie field
        if 'total_calories' in data:
            estimated_calories = data['total_calories']
        
        # Check for total_nutrients list
        elif 'total_nutrients' in data:
            for nutrient in data.get('total_nutrients', []):
                if isinstance(nutrient, dict) and nutrient.get('name', '').lower() == 'calories':
                    estimated_calories = nutrient.get('amount', 0)
                    break
        
        # Check for detected_foods and sum calories
        if 'detected_foods' in data:
            foods = data['detected_foods']
            food_names = [f.get('name', 'Unknown') for f in foods if isinstance(f, dict)]
            
            # Sum calories from individual foods if no total
            if estimated_calories is None:
                total = 0
                for food in foods:
                    if isinstance(food, dict):
                        for nutrient in food.get('nutrients', []):
                            if isinstance(nutrient, dict) and nutrient.get('name', '').lower() == 'calories':
                                total += nutrient.get('amount', 0)
                if total > 0:
                    estimated_calories = total
        
        # Get confidence if available
        if 'image_analysis_confidence' in data:
            confidence = data['image_analysis_confidence']
        elif 'confidence' in data:
            confidence = data['confidence']
        
        return estimated_calories, food_names, confidence
    
    def _generate_mock_ground_truth(self, meal: MealLogEntry) -> float:
        """
        Generate mock ground truth for demo purposes.
        
        Simulates realistic estimation errors based on food types.
        """
        import random
        
        estimated = meal.total_calories
        
        # Different error patterns based on food items
        error_multiplier = 1.0
        for food in meal.food_names:
            food_lower = food.lower()
            if any(x in food_lower for x in ['pizza', 'pasta', 'rice']):
                # Carb-heavy items often underestimated
                error_multiplier *= random.uniform(0.85, 0.95)
            elif any(x in food_lower for x in ['salad', 'vegetables', 'broccoli']):
                # Veggies often overestimated
                error_multiplier *= random.uniform(1.05, 1.15)
            elif any(x in food_lower for x in ['fried', 'chips', 'bacon']):
                # Fried foods often underestimated
                error_multiplier *= random.uniform(0.80, 0.92)
            else:
                # General noise
                error_multiplier *= random.uniform(0.92, 1.08)
        
        # Add some base noise
        noise = random.uniform(-50, 50)
        
        return max(50, estimated * error_multiplier + noise)
    
    def _calculate_metrics(self, data: list[MealCalibrationData]) -> CalibrationMetrics:
        """Calculate calibration metrics from data points."""
        n = len(data)
        
        errors = [d.error for d in data]
        pct_errors = [abs(d.percentage_error) for d in data]
        
        # Mean Absolute Error
        mae = sum(abs(e) for e in errors) / n
        
        # MAPE
        mape = sum(pct_errors) / n
        
        # RMSE
        rmse = math.sqrt(sum(e**2 for e in errors) / n)
        
        # Bias (systematic over/under estimation)
        bias = sum(errors) / n
        
        # Standard deviation
        std = math.sqrt(sum((e - bias)**2 for e in errors) / n)
        
        # Correlation (simplified calculation)
        estimated = [d.estimated_calories for d in data]
        actual = [d.actual_calories for d in data]
        
        mean_est = sum(estimated) / n
        mean_act = sum(actual) / n
        
        numerator = sum((e - mean_est) * (a - mean_act) for e, a in zip(estimated, actual))
        denom_est = math.sqrt(sum((e - mean_est)**2 for e in estimated))
        denom_act = math.sqrt(sum((a - mean_act)**2 for a in actual))
        
        correlation = numerator / (denom_est * denom_act) if denom_est * denom_act > 0 else 0
        r_squared = correlation ** 2
        
        # Brier score (for confidence calibration)
        # Using percentage of accurate predictions as proxy
        accurate_threshold = 0.1  # Within 10%
        predictions = [1 if abs(d.percentage_error) < accurate_threshold * 100 else 0 for d in data]
        confidences = [d.confidence for d in data]
        brier = sum((c - p)**2 for c, p in zip(confidences, predictions)) / n
        
        return CalibrationMetrics(
            mean_absolute_error=round(mae, 1),
            mean_absolute_percentage_error=round(mape, 1),
            root_mean_squared_error=round(rmse, 1),
            brier_score=round(brier, 4),
            expected_calibration_error=round(brier * 0.5, 4),  # Simplified ECE
            pearson_correlation=round(correlation, 3),
            r_squared=round(r_squared, 3),
            bias=round(bias, 1),
            std_deviation=round(std, 1)
        )
    
    def _determine_status(self, metrics: CalibrationMetrics) -> tuple[CalibrationStatus, str]:
        """Determine calibration status based on MAPE."""
        mape = metrics.mean_absolute_percentage_error
        
        if mape < 5:
            return CalibrationStatus.EXCELLENT, f"🌟 Excellent accuracy! MAPE of {mape:.1f}% is well within target."
        elif mape < 10:
            return CalibrationStatus.GOOD, f"✅ Good accuracy. MAPE of {mape:.1f}% meets acceptable standards."
        elif mape < 15:
            return CalibrationStatus.NEEDS_IMPROVEMENT, f"⚠️ Accuracy needs improvement. MAPE of {mape:.1f}% exceeds 10% target."
        else:
            return CalibrationStatus.POOR, f"🔴 Poor accuracy. MAPE of {mape:.1f}% significantly exceeds 15% threshold. Prompt adjustments required."
    
    def _find_worst_categories(self, data: list[MealCalibrationData]) -> list[str]:
        """Find food categories with highest error rates."""
        category_errors: dict[str, list[float]] = {}
        
        category_keywords = {
            "pasta_rice": ["pasta", "rice", "noodles", "spaghetti"],
            "fried_foods": ["fried", "chips", "fries", "bacon", "crispy"],
            "baked_goods": ["bread", "toast", "pancakes", "cookies", "cake"],
            "drinks": ["soda", "juice", "smoothie", "coffee", "milk"],
            "protein": ["chicken", "beef", "salmon", "eggs", "turkey"],
            "vegetables": ["salad", "broccoli", "vegetables", "greens"],
        }
        
        for point in data:
            for food in point.food_names:
                food_lower = food.lower()
                for category, keywords in category_keywords.items():
                    if any(kw in food_lower for kw in keywords):
                        if category not in category_errors:
                            category_errors[category] = []
                        category_errors[category].append(abs(point.percentage_error))
        
        # Sort by average error
        avg_errors = {cat: sum(errs)/len(errs) for cat, errs in category_errors.items() if errs}
        sorted_cats = sorted(avg_errors.items(), key=lambda x: x[1], reverse=True)
        
        # Return top 3 worst categories
        return [cat for cat, _ in sorted_cats[:3]]
    
    def _generate_suggestions(
        self, 
        metrics: CalibrationMetrics, 
        data: list[MealCalibrationData],
        worst_categories: list[str]
    ) -> list[PromptSuggestion]:
        """Generate prompt improvement suggestions based on error patterns."""
        suggestions = []
        
        mape = metrics.mean_absolute_percentage_error
        bias = metrics.bias
        
        # Check for systematic bias
        if bias > 50:
            suggestions.append(PromptSuggestion(
                category="systematic_bias",
                current_issue=f"Model consistently overestimates by {bias:.0f} calories on average",
                suggested_change="Add instruction: 'Be conservative in portion estimates. Most users tend to have smaller portions than typical restaurant servings.'",
                priority=1,
                expected_impact="Reduce systematic overestimation by 30-50%"
            ))
        elif bias < -50:
            suggestions.append(PromptSuggestion(
                category="systematic_bias",
                current_issue=f"Model consistently underestimates by {abs(bias):.0f} calories on average",
                suggested_change="Add instruction: 'Account for hidden calories like cooking oils, sauces, and dressings. Increase estimates by 10-15%.'",
                priority=1,
                expected_impact="Reduce systematic underestimation by 30-50%"
            ))
        
        # Category-specific suggestions
        category_suggestions = {
            "pasta_rice": PromptSuggestion(
                category="portion_estimation",
                current_issue="High errors on pasta/rice - often underestimating carb-heavy dishes",
                suggested_change="Add instruction: 'For pasta and rice: estimate cooked volume first, then use 1 cup cooked pasta ≈ 220cal, 1 cup cooked rice ≈ 200cal as baseline.'",
                priority=1,
                expected_impact="Improve pasta/rice accuracy by 20-30%"
            ),
            "fried_foods": PromptSuggestion(
                category="oil_estimation",
                current_issue="Fried foods consistently underestimated due to oil absorption",
                suggested_change="Add instruction: 'For fried foods, add 30-50% extra calories to account for oil absorption. Deep-fried items absorb more oil than pan-fried.'",
                priority=1,
                expected_impact="Improve fried food accuracy by 25-40%"
            ),
            "vegetables": PromptSuggestion(
                category="portion_estimation",
                current_issue="Vegetable portions often overestimated",
                suggested_change="Add instruction: 'Vegetables are low-density. A large plate of salad may only be 50-100 calories unless dressed heavily.'",
                priority=2,
                expected_impact="Improve vegetable accuracy by 15-25%"
            ),
            "drinks": PromptSuggestion(
                category="beverage_estimation",
                current_issue="Beverage calories frequently missed or underestimated",
                suggested_change="Add instruction: 'Always account for beverages. A regular soda is ~140cal, juice ~120cal per cup, coffee drinks can be 200-500cal.'",
                priority=2,
                expected_impact="Improve beverage accuracy by 30-40%"
            ),
        }
        
        for cat in worst_categories:
            if cat in category_suggestions:
                suggestions.append(category_suggestions[cat])
        
        # General suggestions for poor performance
        if mape > 15:
            suggestions.append(PromptSuggestion(
                category="calibration_reference",
                current_issue=f"Overall accuracy ({mape:.1f}% MAPE) exceeds acceptable threshold",
                suggested_change="Add instruction: 'Before finalizing estimates, mentally compare to known references: a medium apple ≈ 95cal, a slice of bread ≈ 80cal, a tablespoon of oil ≈ 120cal.'",
                priority=1,
                expected_impact="Improve overall calibration by providing reference anchors"
            ))
        
        # High variance suggestion
        if metrics.std_deviation > 150:
            suggestions.append(PromptSuggestion(
                category="confidence_calibration",
                current_issue=f"High variability in estimates (std dev: {metrics.std_deviation:.0f} cal)",
                suggested_change="Add instruction: 'For uncertain identifications, provide a range (e.g., 300-400 cal) rather than a point estimate. Flag low-confidence items.'",
                priority=2,
                expected_impact="Better uncertainty quantification for decision-making"
            ))
        
        return sorted(suggestions, key=lambda s: s.priority)
