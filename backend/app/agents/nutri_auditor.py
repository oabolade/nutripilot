"""
NutriPilot AI - NutriAuditor Agent

Validates and enriches detected foods with nutrition data from the 
USDA FoodData Central API. Calculates totals and checks against 
user health constraints.

This agent supports the THINK phase of the pipeline.
"""

import logging
import time
from typing import Optional
from functools import lru_cache

import httpx

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
from app.core.state import (
    NutriAuditRequest,
    NutriAuditReport,
    FoodItem,
    NutrientInfo,
    HealthConstraint,
    ConstraintStatus,
    MealAdjustment,
    AdjustmentAction,
)
from app.config import get_settings

logger = logging.getLogger(__name__)

# USDA FoodData Central API
USDA_API_BASE = "https://api.nal.usda.gov/fdc/v1"

# Nutrient IDs in USDA API
NUTRIENT_IDS = {
    "calories": 1008,    # Energy (kcal)
    "protein": 1003,     # Protein (g)
    "fat": 1004,         # Total lipid (fat) (g)
    "carbohydrates": 1005,  # Carbohydrate, by difference (g)
    "fiber": 1079,       # Fiber, total dietary (g)
    "sugar": 2000,       # Sugars, total (g)
    "sodium": 1093,      # Sodium, Na (mg)
    "vitamin_c": 1162,   # Vitamin C (mg)
    "calcium": 1087,     # Calcium, Ca (mg)
    "iron": 1089,        # Iron, Fe (mg)
}

# Daily recommended values for % DV calculations
DAILY_VALUES = {
    "calories": 2000,
    "protein": 50,
    "fat": 78,
    "carbohydrates": 275,
    "fiber": 28,
    "sugar": 50,
    "sodium": 2300,
    "vitamin_c": 90,
    "calcium": 1300,
    "iron": 18,
}

# Units for each nutrient
NUTRIENT_UNITS = {
    "calories": "kcal",
    "protein": "g",
    "fat": "g",
    "carbohydrates": "g",
    "fiber": "g",
    "sugar": "g",
    "sodium": "mg",
    "vitamin_c": "mg",
    "calcium": "mg",
    "iron": "mg",
}

# Local cache for nutrition data (to avoid repeated API calls)
NUTRITION_CACHE: dict[str, dict] = {}

# Fallback nutrition data when API is unavailable
FALLBACK_NUTRITION = {
    "chicken": {"calories": 165, "protein": 31, "carbohydrates": 0, "fat": 3.6, "fiber": 0, "sodium": 74},
    "grilled chicken": {"calories": 165, "protein": 31, "carbohydrates": 0, "fat": 3.6, "fiber": 0, "sodium": 74},
    "chicken breast": {"calories": 165, "protein": 31, "carbohydrates": 0, "fat": 3.6, "fiber": 0, "sodium": 74},
    "rice": {"calories": 130, "protein": 2.7, "carbohydrates": 28, "fat": 0.3, "fiber": 0.4, "sodium": 1},
    "brown rice": {"calories": 111, "protein": 2.6, "carbohydrates": 23, "fat": 0.9, "fiber": 1.8, "sodium": 5},
    "white rice": {"calories": 130, "protein": 2.7, "carbohydrates": 28, "fat": 0.3, "fiber": 0.4, "sodium": 1},
    "broccoli": {"calories": 34, "protein": 2.8, "carbohydrates": 7, "fat": 0.4, "fiber": 2.6, "sodium": 33},
    "steamed broccoli": {"calories": 34, "protein": 2.8, "carbohydrates": 7, "fat": 0.4, "fiber": 2.6, "sodium": 33},
    "salmon": {"calories": 208, "protein": 20, "carbohydrates": 0, "fat": 13, "fiber": 0, "sodium": 59},
    "apple": {"calories": 52, "protein": 0.3, "carbohydrates": 14, "fat": 0.2, "fiber": 2.4, "sodium": 1},
    "banana": {"calories": 89, "protein": 1.1, "carbohydrates": 23, "fat": 0.3, "fiber": 2.6, "sodium": 1},
    "eggs": {"calories": 155, "protein": 13, "carbohydrates": 1.1, "fat": 11, "fiber": 0, "sodium": 124},
    "egg": {"calories": 155, "protein": 13, "carbohydrates": 1.1, "fat": 11, "fiber": 0, "sodium": 124},
    "avocado": {"calories": 160, "protein": 2, "carbohydrates": 9, "fat": 15, "fiber": 7, "sodium": 7},
    "spinach": {"calories": 23, "protein": 2.9, "carbohydrates": 3.6, "fat": 0.4, "fiber": 2.2, "sodium": 79},
    "steak": {"calories": 271, "protein": 26, "carbohydrates": 0, "fat": 18, "fiber": 0, "sodium": 66},
    "beef": {"calories": 250, "protein": 26, "carbohydrates": 0, "fat": 15, "fiber": 0, "sodium": 72},
    "potato": {"calories": 77, "protein": 2, "carbohydrates": 17, "fat": 0.1, "fiber": 2.2, "sodium": 6},
    "bread": {"calories": 265, "protein": 9, "carbohydrates": 49, "fat": 3.2, "fiber": 2.7, "sodium": 491},
    "pasta": {"calories": 131, "protein": 5, "carbohydrates": 25, "fat": 1.1, "fiber": 1.8, "sodium": 1},
    "cheese": {"calories": 402, "protein": 25, "carbohydrates": 1.3, "fat": 33, "fiber": 0, "sodium": 621},
    "milk": {"calories": 42, "protein": 3.4, "carbohydrates": 5, "fat": 1, "fiber": 0, "sodium": 44},
    "yogurt": {"calories": 59, "protein": 10, "carbohydrates": 3.6, "fat": 0.7, "fiber": 0, "sodium": 36},
    "orange": {"calories": 47, "protein": 0.9, "carbohydrates": 12, "fat": 0.1, "fiber": 2.4, "sodium": 0},
    "carrot": {"calories": 41, "protein": 0.9, "carbohydrates": 10, "fat": 0.2, "fiber": 2.8, "sodium": 69},
    "tomato": {"calories": 18, "protein": 0.9, "carbohydrates": 3.9, "fat": 0.2, "fiber": 1.2, "sodium": 5},
    "default": {"calories": 100, "protein": 5, "carbohydrates": 15, "fat": 3, "fiber": 1, "sodium": 100},
}


class NutriAuditor(BaseAgent[NutriAuditRequest, NutriAuditReport]):
    """
    Specialized agent for nutrition data lookup and validation.
    
    Uses the USDA FoodData Central API to:
    - Search for food items and find best matches
    - Retrieve detailed nutrition data
    - Calculate total meal nutrients
    - Identify constraint violations
    - Suggest meal adjustments
    
    Includes local caching to minimize API calls and fallback
    data when the API is unavailable.
    
    Example:
        auditor = NutriAuditor()
        result = await auditor.execute(NutriAuditRequest(
            foods=[...],
            user_constraints=[...]
        ))
    """
    
    def __init__(self):
        """Initialize NutriAuditor with USDA API client."""
        super().__init__(max_retries=2, retry_delay=0.5)
        self.settings = get_settings()
        self.api_key = self.settings.usda_api_key
        
        if not self.api_key:
            logger.warning("USDA API key not configured - using fallback nutrition data")
    
    @property
    def name(self) -> str:
        return "NutriAuditor"
    
    @track(name="nutri_auditor.process")
    async def process(self, input: NutriAuditRequest) -> NutriAuditReport:
        """
        Audit foods for nutrition data and constraint violations.
        
        Args:
            input: NutriAuditRequest with foods and optional constraints
            
        Returns:
            NutriAuditReport with totals, violations, and suggestions
        """
        start_time = time.time()
        
        # Track matching stats
        foods_matched = 0
        foods_unmatched = []
        
        # Lookup nutrition for each food
        enriched_foods = []
        for food in input.foods:
            nutrients = await self._get_nutrition(food.name, food.portion_grams)
            
            if nutrients:
                food.nutrients = nutrients
                foods_matched += 1
            else:
                foods_unmatched.append(food.name)
            
            enriched_foods.append(food)
        
        # Calculate totals
        total_nutrients = self._calculate_totals(enriched_foods)
        
        # Check for violations
        violations, warnings = self._check_constraints(
            total_nutrients, 
            input.user_constraints
        )
        
        # Generate suggestions
        suggestions = self._generate_suggestions(
            enriched_foods,
            violations,
            input.user_constraints
        )
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        logger.info(
            f"NutriAuditor matched {foods_matched}/{len(input.foods)} foods "
            f"with {len(violations)} violations in {latency_ms}ms"
        )
        
        return NutriAuditReport(
            total_nutrients=total_nutrients,
            violations=violations,
            warnings=warnings,
            suggestions=suggestions,
            foods_matched=foods_matched,
            foods_unmatched=foods_unmatched,
        )
    
    async def _get_nutrition(
        self, 
        food_name: str, 
        portion_grams: float
    ) -> list[NutrientInfo]:
        """Get nutrition data for a food, scaled by portion size."""
        
        # Check cache first
        cache_key = food_name.lower().strip()
        if cache_key in NUTRITION_CACHE:
            nutrients_per_100g = NUTRITION_CACHE[cache_key]
        elif self.api_key:
            # Try USDA API
            nutrients_per_100g = await self._fetch_from_usda(food_name)
            if nutrients_per_100g:
                NUTRITION_CACHE[cache_key] = nutrients_per_100g
        else:
            nutrients_per_100g = None
        
        # Fallback to local data
        if not nutrients_per_100g:
            nutrients_per_100g = self._get_fallback_nutrition(food_name)
            NUTRITION_CACHE[cache_key] = nutrients_per_100g
        
        # Scale by portion size
        scale = portion_grams / 100.0
        
        result = []
        for name, value in nutrients_per_100g.items():
            if name in NUTRIENT_UNITS:
                scaled_value = value * scale
                percent_daily = None
                
                if name in DAILY_VALUES:
                    percent_daily = (scaled_value / DAILY_VALUES[name]) * 100
                
                result.append(NutrientInfo(
                    name=name,
                    amount=round(scaled_value, 1),
                    unit=NUTRIENT_UNITS[name],
                    percent_daily=round(percent_daily, 1) if percent_daily else None,
                ))
        
        return result
    
    async def _fetch_from_usda(self, food_name: str) -> Optional[dict]:
        """Fetch nutrition data from USDA FoodData Central API."""
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Search for food
                search_url = f"{USDA_API_BASE}/foods/search"
                search_params = {
                    "api_key": self.api_key,
                    "query": food_name,
                    "pageSize": 5,
                    "dataType": ["Survey (FNDDS)", "Foundation", "SR Legacy"],
                }
                
                response = await client.get(search_url, params=search_params)
                response.raise_for_status()
                
                data = response.json()
                foods = data.get("foods", [])
                
                if not foods:
                    logger.debug(f"No USDA results for: {food_name}")
                    return None
                
                # Use first result
                food = foods[0]
                fdc_id = food.get("fdcId")
                
                # Parse nutrients from search result (to avoid second API call)
                nutrients = {}
                for nutrient in food.get("foodNutrients", []):
                    nutrient_id = nutrient.get("nutrientId")
                    value = nutrient.get("value", 0)
                    
                    # Map USDA nutrient IDs to our names
                    for our_name, usda_id in NUTRIENT_IDS.items():
                        if nutrient_id == usda_id:
                            nutrients[our_name] = value
                            break
                
                if nutrients:
                    logger.debug(f"USDA match for '{food_name}': {food.get('description')}")
                    return nutrients
                
                return None
                
        except Exception as e:
            logger.warning(f"USDA API error for '{food_name}': {e}")
            return None
    
    def _get_fallback_nutrition(self, food_name: str) -> dict:
        """Get nutrition from local fallback data."""
        
        food_lower = food_name.lower()
        
        # Try exact match first
        if food_lower in FALLBACK_NUTRITION:
            return FALLBACK_NUTRITION[food_lower]
        
        # Try partial match
        for key, values in FALLBACK_NUTRITION.items():
            if key in food_lower or food_lower in key:
                return values
        
        # Return default
        return FALLBACK_NUTRITION["default"]
    
    def _calculate_totals(self, foods: list[FoodItem]) -> list[NutrientInfo]:
        """Calculate total nutrients across all foods."""
        
        totals: dict[str, float] = {}
        
        for food in foods:
            for nutrient in food.nutrients:
                if nutrient.name not in totals:
                    totals[nutrient.name] = 0
                totals[nutrient.name] += nutrient.amount
        
        result = []
        for name, amount in totals.items():
            percent_daily = None
            if name in DAILY_VALUES:
                percent_daily = (amount / DAILY_VALUES[name]) * 100
            
            result.append(NutrientInfo(
                name=name,
                amount=round(amount, 1),
                unit=NUTRIENT_UNITS.get(name, "g"),
                percent_daily=round(percent_daily, 1) if percent_daily else None,
            ))
        
        return result
    
    def _check_constraints(
        self,
        total_nutrients: list[NutrientInfo],
        constraints: list[HealthConstraint]
    ) -> tuple[list[str], list[str]]:
        """Check nutrients against user health constraints."""
        
        violations = []
        warnings = []
        
        # Get nutrient values as dict for easy lookup
        nutrient_values = {n.name: n.amount for n in total_nutrients}
        
        for constraint in constraints:
            if constraint.constraint_type == "blood_glucose":
                carbs = nutrient_values.get("carbohydrates", 0)
                sugar = nutrient_values.get("sugar", 0)
                
                if constraint.status == ConstraintStatus.WARNING:
                    if carbs > 45:
                        violations.append(
                            f"High carbohydrates ({carbs:.0f}g) may spike blood glucose"
                        )
                    elif sugar > 15:
                        warnings.append(
                            f"Moderate sugar ({sugar:.0f}g) - monitor blood glucose"
                        )
                elif constraint.status == ConstraintStatus.CRITICAL:
                    if carbs > 30:
                        violations.append(
                            f"Meal carbohydrates ({carbs:.0f}g) too high for current glucose level"
                        )
            
            elif "low_sodium" in constraint.constraint_type or \
                 constraint.constraint_type == "daily_sodium":
                sodium = nutrient_values.get("sodium", 0)
                
                if sodium > 800:
                    violations.append(
                        f"High sodium meal ({sodium:.0f}mg) - limit of 600mg recommended"
                    )
                elif sodium > 500:
                    warnings.append(
                        f"Moderate sodium ({sodium:.0f}mg) in this meal"
                    )
            
            elif constraint.constraint_type.startswith("allergy_"):
                allergen = constraint.constraint_type.replace("allergy_", "")
                violations.append(
                    f"⚠️ Check all items for {allergen} content"
                )
        
        return violations, warnings
    
    def _generate_suggestions(
        self,
        foods: list[FoodItem],
        violations: list[str],
        constraints: list[HealthConstraint]
    ) -> list[MealAdjustment]:
        """Generate meal adjustment suggestions based on violations."""
        
        suggestions = []
        
        for violation in violations:
            if "carbohydrate" in violation.lower() or "carbs" in violation.lower():
                # Find high-carb foods
                for food in foods:
                    carbs = next(
                        (n.amount for n in food.nutrients if n.name == "carbohydrates"),
                        0
                    )
                    if carbs > 20:
                        suggestions.append(MealAdjustment(
                            food_name=food.name,
                            action=AdjustmentAction.REDUCE,
                            reason="Reduce portion to lower carbohydrate intake",
                            alternative="cauliflower rice" if "rice" in food.name.lower() else None,
                            priority=1,
                        ))
                        break
            
            elif "sodium" in violation.lower():
                # Find high-sodium foods
                for food in foods:
                    sodium = next(
                        (n.amount for n in food.nutrients if n.name == "sodium"),
                        0
                    )
                    if sodium > 200:
                        suggestions.append(MealAdjustment(
                            food_name=food.name,
                            action=AdjustmentAction.REPLACE,
                            reason="High sodium content",
                            alternative="unseasoned version or fresh alternative",
                            priority=2,
                        ))
                        break
        
        # General suggestions for improvement
        total_fiber = sum(
            n.amount for f in foods for n in f.nutrients if n.name == "fiber"
        )
        if total_fiber < 5:
            suggestions.append(MealAdjustment(
                food_name="meal",
                action=AdjustmentAction.ADD,
                reason="Low fiber meal - consider adding vegetables",
                alternative="leafy greens, broccoli, or beans",
                priority=3,
            ))
        
        return suggestions
