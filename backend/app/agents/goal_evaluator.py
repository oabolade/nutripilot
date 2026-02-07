"""
NutriPilot AI - GoalEvaluator Agent

Evaluates meals against user-defined goals and health conditions.
Provides goal-specific feedback and recommendations.
"""

import logging
from typing import Optional

# Try to import Opik for tracing
try:
    from opik import track
    OPIK_AVAILABLE = True
except ImportError:
    OPIK_AVAILABLE = False
    def track(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

from app.core.base_agent import BaseAgent
from app.core.state import MealState, NutrientInfo
from app.core.user_goals import (
    UserProfile,
    GoalEvaluation,
    HealthGoal,
    HealthCondition,
    GOAL_NUTRIENT_RULES,
    CONDITION_RESTRICTIONS,
)

logger = logging.getLogger(__name__)


class GoalEvaluator(BaseAgent[MealState, GoalEvaluation]):
    """
    Evaluates meals against user-defined goals and conditions.
    
    For each goal type, applies specific nutrient rules to score
    how well the meal aligns with the user's objectives.
    
    Example:
        evaluator = GoalEvaluator()
        result = await evaluator.execute((meal_state, user_profile))
    """
    
    def __init__(self):
        super().__init__(max_retries=1, retry_delay=0.1)
        self._logger = logging.getLogger("nutripilot.goal_evaluator")
    
    @property
    def name(self) -> str:
        return "GoalEvaluator"
    
    @track(name="goal_evaluator.process")
    async def process(self, input: tuple[MealState, UserProfile]) -> GoalEvaluation:
        """
        Evaluate a meal against user goals and conditions.
        
        Args:
            input: Tuple of (MealState, UserProfile)
            
        Returns:
            GoalEvaluation with alignment score and feedback
        """
        meal_state, profile = input
        
        if not profile or not profile.goals:
            return GoalEvaluation(
                alignment_score=50.0,
                goal_scores={},
                feedback=["Set up your health goals to get personalized feedback!"],
                recommendations=[]
            )
        
        # Get nutrients from meal
        nutrients = self._extract_nutrients(meal_state)
        
        # Evaluate against each goal
        goal_scores = {}
        all_feedback = []
        all_recommendations = []
        
        for goal in profile.goals:
            score, feedback, recs = self._evaluate_goal(goal, nutrients, profile)
            goal_scores[goal.value] = score
            all_feedback.extend(feedback)
            all_recommendations.extend(recs)
        
        # Check condition restrictions
        condition_feedback = self._check_conditions(meal_state, profile, nutrients)
        all_feedback.extend(condition_feedback)
        
        # Calculate overall alignment score
        if goal_scores:
            alignment_score = sum(goal_scores.values()) / len(goal_scores)
        else:
            alignment_score = 50.0
        
        self._logger.info(
            f"Goal evaluation complete: {alignment_score:.1f}% alignment, "
            f"{len(goal_scores)} goals, {len(all_feedback)} feedback items"
        )
        
        return GoalEvaluation(
            alignment_score=round(alignment_score, 1),
            goal_scores=goal_scores,
            feedback=all_feedback[:5],  # Limit to top 5
            recommendations=all_recommendations[:3]  # Limit to top 3
        )
    
    def _extract_nutrients(self, meal_state: MealState) -> dict[str, float]:
        """Extract nutrient values from meal state."""
        nutrients = {}
        for nutrient in meal_state.total_nutrients:
            key = nutrient.name.lower()
            nutrients[key] = nutrient.amount
        
        # Ensure common nutrients exist with defaults
        defaults = {
            "calories": 0, "protein": 0, "carbohydrates": 0, "carbs": 0,
            "fat": 0, "fiber": 0, "sodium": 0, "sugar": 0
        }
        for key, default in defaults.items():
            if key not in nutrients:
                nutrients[key] = default
        
        # Normalize carbs key
        if nutrients.get("carbohydrates", 0) > 0:
            nutrients["carbs"] = nutrients["carbohydrates"]
        
        return nutrients
    
    def _evaluate_goal(
        self, 
        goal: HealthGoal, 
        nutrients: dict[str, float],
        profile: UserProfile
    ) -> tuple[float, list[str], list[str]]:
        """
        Evaluate nutrient intake against a specific goal.
        
        Returns: (score, feedback_list, recommendations_list)
        """
        rules = GOAL_NUTRIENT_RULES.get(goal, {})
        if not rules:
            return 50.0, [], []
        
        targets = profile.daily_targets
        target_map = {
            "calories": targets.calories,
            "protein": targets.protein_g,
            "carbs": targets.carbs_g,
            "fat": targets.fat_g,
            "fiber": targets.fiber_g,
            "sodium": targets.sodium_mg,
            "sugar": targets.sugar_g,
        }
        
        total_score = 0.0
        total_weight = 0.0
        feedback = []
        recommendations = []
        
        for nutrient, rule in rules.items():
            target = target_map.get(nutrient, 0)
            if target == 0:
                continue
            
            actual = nutrients.get(nutrient, 0)
            percent_of_target = (actual / target) * 100
            weight = rule.get("weight", 0.25)
            
            # Calculate score based on rule type
            if "max_percent" in rule:
                max_pct = rule["max_percent"]
                if percent_of_target <= max_pct:
                    score = 100
                else:
                    # Penalize proportionally for exceeding
                    overage = percent_of_target - max_pct
                    score = max(0, 100 - overage * 2)
                    if score < 50:
                        feedback.append(
                            f"⚠️ {goal.value.replace('_', ' ').title()}: "
                            f"{nutrient.title()} is {percent_of_target:.0f}% of target "
                            f"(goal: ≤{max_pct}%)"
                        )
                        recommendations.append(
                            f"Reduce {nutrient} intake for your {goal.value.replace('_', ' ')} goal"
                        )
            
            elif "min_percent" in rule:
                min_pct = rule["min_percent"]
                if percent_of_target >= min_pct:
                    score = 100
                else:
                    # Penalize proportionally for falling short
                    shortfall = min_pct - percent_of_target
                    score = max(0, 100 - shortfall)
                    if score < 50:
                        feedback.append(
                            f"📊 {goal.value.replace('_', ' ').title()}: "
                            f"{nutrient.title()} is {percent_of_target:.0f}% of target "
                            f"(goal: ≥{min_pct}%)"
                        )
                        recommendations.append(
                            f"Increase {nutrient} intake for your {goal.value.replace('_', ' ')} goal"
                        )
            else:
                score = 75  # Default neutral score
            
            total_score += score * weight
            total_weight += weight
        
        final_score = (total_score / total_weight) if total_weight > 0 else 50
        
        # Add positive feedback if score is good
        if final_score >= 80 and not feedback:
            feedback.append(
                f"✅ Great job! This meal aligns well with your "
                f"{goal.value.replace('_', ' ')} goal!"
            )
        
        return round(final_score, 1), feedback, recommendations
    
    def _check_conditions(
        self, 
        meal_state: MealState, 
        profile: UserProfile,
        nutrients: dict[str, float]
    ) -> list[str]:
        """Check meal against health condition restrictions."""
        feedback = []
        
        for condition in profile.conditions:
            if condition == HealthCondition.NONE:
                continue
            
            restrictions = CONDITION_RESTRICTIONS.get(condition, {})
            
            # Check nutrient limits
            if "sugar_max_g" in restrictions:
                if nutrients.get("sugar", 0) > restrictions["sugar_max_g"]:
                    feedback.append(
                        f"⚠️ {condition.value.replace('_', ' ').title()}: "
                        f"Sugar ({nutrients.get('sugar', 0):.0f}g) exceeds recommended max "
                        f"({restrictions['sugar_max_g']}g)"
                    )
            
            if "sodium_max_mg" in restrictions:
                if nutrients.get("sodium", 0) > restrictions["sodium_max_mg"]:
                    feedback.append(
                        f"⚠️ {condition.value.replace('_', ' ').title()}: "
                        f"Sodium ({nutrients.get('sodium', 0):.0f}mg) exceeds recommended max "
                        f"({restrictions['sodium_max_mg']}mg)"
                    )
            
            if "carbs_max_g" in restrictions:
                carbs = nutrients.get("carbs", 0) or nutrients.get("carbohydrates", 0)
                if carbs > restrictions["carbs_max_g"]:
                    feedback.append(
                        f"⚠️ {condition.value.replace('_', ' ').title()}: "
                        f"Carbs ({carbs:.0f}g) exceeds recommended max "
                        f"({restrictions['carbs_max_g']}g)"
                    )
            
            # Check avoided foods
            if "avoid_foods" in restrictions:
                detected_foods = [f.name.lower() for f in meal_state.detected_foods]
                for food in detected_foods:
                    for avoid in restrictions["avoid_foods"]:
                        if avoid in food:
                            feedback.append(
                                f"🚫 {condition.value.replace('_', ' ').title()}: "
                                f"'{food}' may not be suitable - contains {avoid}"
                            )
                            break
        
        return feedback
