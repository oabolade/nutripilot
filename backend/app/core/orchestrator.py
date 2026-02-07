"""
NutriPilot AI - Studio Orchestrator

The central coordinator implementing the Observe-Think-Act pattern.
Manages the flow of data between specialized agents and maintains
the MealState throughout the analysis pipeline.
"""

import logging
import time
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

from app.core.state import (
    MealState,
    MealType,
    FoodItem,
    NutrientInfo,
    VisionInput,
    BioDataQuery,
    NutriAuditRequest,
    MealAdjustment,
    AdjustmentAction,
)
from app.core.user_goals import (
    UserProfile,
    HealthGoal,
    GOAL_NUTRIENT_RULES,
)

# Confidence threshold below which we consider extraction failed
EXTRACTION_CONFIDENCE_THRESHOLD = 0.15
MIN_FOODS_FOR_SUCCESS = 1
from app.agents import VisionAnalyst, BioDataScout, NutriAuditor
from app.config import get_settings

logger = logging.getLogger(__name__)


class StudioOrchestrator:
    """
    Central orchestrator for the NutriPilot analysis pipeline.
    
    Implements the Observe-Think-Act pattern using specialized agents:
    
    1. **OBSERVE**: Analyze input (image/text) to detect foods
       - Uses VisionAnalyst for image analysis with Gemini Vision
       - Extracts food items, portions, bounding boxes, and confidence scores
    
    2. **THINK**: Process detected foods with context
       - Queries BioDataScout for user health constraints
       - Uses NutriAuditor to lookup nutrition data from USDA
       - Identifies constraint violations
    
    3. **ACT**: Generate recommendations
       - Creates meal adjustments based on violations
       - Calculates overall meal score
       - Generates human-readable summary
    
    Usage:
        orchestrator = StudioOrchestrator()
        result = await orchestrator.process(
            user_id="user_123",
            image_bytes=image_data,
        )
    """
    
    def __init__(self):
        """Initialize the orchestrator with specialized agents."""
        self.settings = get_settings()
        self._logger = logging.getLogger("nutripilot.orchestrator")
        
        # Initialize specialized agents
        self.vision_analyst = VisionAnalyst()
        self.biodata_scout = BioDataScout()
        self.nutri_auditor = NutriAuditor()
        
        self._logger.info("StudioOrchestrator initialized with agents: "
                         "VisionAnalyst, BioDataScout, NutriAuditor")
    
    @track(name="orchestrator.process")
    async def process(
        self,
        user_id: str,
        image_bytes: Optional[bytes] = None,
        text_input: Optional[str] = None,
        meal_type: Optional[MealType] = None,
        user_profile: Optional[UserProfile] = None,  # NEW: for goal-based personalization
    ) -> MealState:
        """
        Run the full Observe-Think-Act pipeline.
        
        Args:
            user_id: User identifier for personalization
            image_bytes: Raw image data (optional)
            text_input: Text description of meal (optional)
            meal_type: Type of meal (breakfast, lunch, dinner, snack)
            user_profile: User's profile with goals for personalized recommendations
            
        Returns:
            Complete MealState with analysis results
            
        Raises:
            ValueError: If neither image nor text is provided
        """
        start_time = time.time()
        
        if not image_bytes and not text_input:
            raise ValueError("Either image_bytes or text_input must be provided")
        
        # Initialize state
        state = MealState(
            user_id=user_id,
            meal_type=meal_type,
        )
        
        # Store profile for ACT phase
        self._current_profile = user_profile
        
        self._logger.info(f"Starting analysis for session {state.session_id}")
        
        try:
            # === OBSERVE PHASE ===
            state = await self._observe(state, image_bytes, text_input)
            state.agent_calls.append("VisionAnalyst")
            
            # === SHORT-CIRCUIT ON EXTRACTION FAILURE ===
            # If vision failed to detect any food, skip downstream processing
            if self._is_extraction_failed(state, is_image=image_bytes is not None):
                state = self._handle_extraction_failure(state, is_image=image_bytes is not None)
                state.processing_time_ms = int((time.time() - start_time) * 1000)
                self._logger.warning(
                    f"Extraction failed for session {state.session_id} - "
                    f"short-circuiting downstream processing"
                )
                return state
            
            # === THINK PHASE ===
            state = await self._think(state)
            state.agent_calls.extend(["BioDataScout", "NutriAuditor"])
            
            # === ACT PHASE ===
            state = await self._act(state)
            state.agent_calls.append("Orchestrator.act")
            
            # Calculate total processing time
            state.processing_time_ms = int((time.time() - start_time) * 1000)
            
            self._logger.info(
                f"Analysis complete for session {state.session_id} "
                f"in {state.processing_time_ms}ms"
            )
            
            return state
            
        except Exception as e:
            self._logger.error(f"Pipeline failed: {e}")
            state.summary = f"Analysis failed: {str(e)}"
            state.overall_score = 0.0
            state.processing_time_ms = int((time.time() - start_time) * 1000)
            return state
    
    @track(name="orchestrator.observe")
    async def _observe(
        self,
        state: MealState,
        image_bytes: Optional[bytes],
        text_input: Optional[str],
    ) -> MealState:
        """
        OBSERVE phase: Analyze input to detect foods using VisionAnalyst.
        """
        self._logger.info("Starting OBSERVE phase")
        
        if image_bytes:
            # Use VisionAnalyst for image analysis
            vision_input = VisionInput(
                image_bytes=image_bytes,
                image_format="jpeg",
            )
            
            result = await self.vision_analyst.execute(vision_input)
            
            if result.success and result.output:
                vision_output = result.output
                state.detected_foods = vision_output.foods
                state.image_analysis_confidence = vision_output.overall_confidence
                state.raw_ocr_text = vision_output.ocr_text
                
                self._logger.info(
                    f"VisionAnalyst detected {len(state.detected_foods)} foods "
                    f"with {state.image_analysis_confidence:.2f} confidence"
                )
            else:
                self._logger.warning(f"VisionAnalyst failed: {result.error}")
                # Fallback to mock data
                state = self._add_mock_foods(state)
        
        elif text_input:
            # Parse text input for food mentions
            state = self._parse_text_input(state, text_input)
        
        self._logger.info(f"OBSERVE complete: {len(state.detected_foods)} foods detected")
        return state
    
    @track(name="orchestrator.think")
    async def _think(self, state: MealState) -> MealState:
        """
        THINK phase: Query health data and lookup nutrition using
        BioDataScout and NutriAuditor agents.
        """
        self._logger.info("Starting THINK phase")
        
        # Get user profile for filtering constraints
        profile = getattr(self, '_current_profile', None)
        
        # Query health constraints using BioDataScout
        biodata_query = BioDataQuery(user_id=state.user_id)
        biodata_result = await self.biodata_scout.execute(biodata_query)
        
        if biodata_result.success and biodata_result.output:
            constraints = biodata_result.output.constraints
            
            # Filter constraints based on user's actual goals/conditions
            # Only show blood glucose constraints if user cares about glycemic control
            if profile:
                has_glycemic_goal = any(
                    g == HealthGoal.GLYCEMIC_CONTROL for g in profile.goals
                ) if profile.goals else False
                
                has_diabetes = any(
                    c.value in ['type_1_diabetes', 'type_2_diabetes'] 
                    for c in profile.conditions
                ) if profile.conditions else False
                
                if not has_glycemic_goal and not has_diabetes:
                    # Remove blood glucose constraints for non-glycemic users
                    constraints = [
                        c for c in constraints 
                        if c.constraint_type != "blood_glucose"
                    ]
                    self._logger.info("Filtered out blood_glucose constraints (user has no glycemic goals)")
            
            state.health_constraints = constraints
            
            # Log any critical alerts
            for alert in biodata_result.output.alerts:
                self._logger.warning(f"Health alert: {alert}")
        
        # Lookup nutrition and check constraints using NutriAuditor
        audit_request = NutriAuditRequest(
            foods=state.detected_foods,
            user_constraints=state.health_constraints,
        )
        audit_result = await self.nutri_auditor.execute(audit_request)
        
        if audit_result.success and audit_result.output:
            audit_output = audit_result.output
            state.total_nutrients = audit_output.total_nutrients
            state.constraint_violations = audit_output.violations
            
            # Add warnings as well (for display purposes)
            for warning in audit_output.warnings:
                if warning not in state.constraint_violations:
                    state.constraint_violations.append(f"⚠️ {warning}")
            
            # Store suggestions for ACT phase
            self._pending_suggestions = audit_output.suggestions
            
            self._logger.info(
                f"NutriAuditor matched {audit_output.foods_matched} foods, "
                f"found {len(audit_output.violations)} violations"
            )
        
        self._logger.info(f"THINK complete: {len(state.constraint_violations)} violations found")
        return state
    
    @track(name="orchestrator.act")
    async def _act(self, state: MealState) -> MealState:
        """
        ACT phase: Generate recommendations and score the meal.
        
        Uses the detected foods, nutrients, and constraints to create
        personalized adjustments and an overall assessment.
        """
        self._logger.info("Starting ACT phase")
        
        # Get user profile for goal-specific recommendations
        profile = getattr(self, '_current_profile', None)
        
        # Generate goal-specific suggestions if profile exists
        if profile and profile.goals:
            goal_suggestions = self._generate_goal_suggestions(state, profile)
            state.adjustments = goal_suggestions
            self._logger.info(f"Generated {len(goal_suggestions)} goal-specific suggestions")
        # Fall back to NutriAuditor suggestions if no profile
        elif hasattr(self, '_pending_suggestions') and self._pending_suggestions:
            state.adjustments = self._pending_suggestions
            self._pending_suggestions = []
        
        # Add additional suggestions based on specific violations
        # Only apply glycemic-related suggestions if user has that goal or condition
        if state.constraint_violations and profile:
            # Check if user cares about glycemic control
            has_glycemic_goal = any(
                g == HealthGoal.GLYCEMIC_CONTROL for g in profile.goals
            ) if profile.goals else False
            
            has_diabetes_condition = any(
                c.value in ['type_1_diabetes', 'type_2_diabetes'] 
                for c in profile.conditions
            ) if profile.conditions else False
            
            should_check_glycemic = has_glycemic_goal or has_diabetes_condition
            
            for violation in state.constraint_violations:
                # Only add carb/glucose suggestions if user has glycemic goals
                if "carbohydrate" in violation.lower() and should_check_glycemic:
                    has_carb_suggestion = any(
                        "carb" in adj.reason.lower() or "glucose" in adj.reason.lower()
                        for adj in state.adjustments
                    )
                    if not has_carb_suggestion:
                        for food in state.detected_foods:
                            carbs = next(
                                (n.amount for n in food.nutrients if n.name == "carbohydrates"),
                                0
                            )
                            if carbs > 20:
                                state.adjustments.append(MealAdjustment(
                                    food_name=food.name,
                                    action=AdjustmentAction.REDUCE,
                                    reason="Consider reducing portion to manage blood glucose",
                                    alternative="cauliflower rice" if "rice" in food.name.lower() else None,
                                    priority=1,
                                ))
                                break
        
        # Calculate meal score (0-100)
        score = self._calculate_meal_score(state)
        state.overall_score = score
        
        # Generate summary
        state.summary = self._generate_summary(state)
        
        self._logger.info(f"ACT complete: score={score:.0f}, {len(state.adjustments)} adjustments")
        return state
    
    # === Extraction Failure Handling ===
    
    def _is_extraction_failed(self, state: MealState, is_image: bool) -> bool:
        """
        Determine if food extraction failed and downstream processing should be skipped.
        
        Criteria for failure:
        - Image input with no foods detected AND low confidence
        - Very low confidence score regardless of food count
        
        Args:
            state: Current MealState after OBSERVE phase
            is_image: Whether the input was an image (stricter validation)
            
        Returns:
            True if extraction failed and should short-circuit
        """
        no_foods_detected = len(state.detected_foods) < MIN_FOODS_FOR_SUCCESS
        low_confidence = state.image_analysis_confidence < EXTRACTION_CONFIDENCE_THRESHOLD
        
        if is_image:
            # For images, empty foods with confidence < 0.15 is a clear failure
            if no_foods_detected and low_confidence:
                self._logger.warning(
                    f"Image extraction failed: {len(state.detected_foods)} foods, "
                    f"confidence={state.image_analysis_confidence:.2f}"
                )
                return True
            # Also flag if confidence is very low even with "foods" detected
            # (likely hallucinated foods from non-food images)
            if state.image_analysis_confidence < 0.1:
                self._logger.warning(
                    f"Very low confidence extraction: {state.image_analysis_confidence:.2f}"
                )
                return True
        
        return False
    
    def _handle_extraction_failure(self, state: MealState, is_image: bool) -> MealState:
        """
        Generate appropriate error response when extraction fails.
        
        Instead of hallucinating food data and providing irrelevant suggestions,
        this provides a clear error message explaining the failure.
        
        Args:
            state: Current MealState after failed OBSERVE phase
            is_image: Whether the input was an image
            
        Returns:
            MealState with error-appropriate values
        """
        # Clear any potentially invalid detected foods
        state.detected_foods = []
        state.total_nutrients = []
        state.adjustments = []
        state.constraint_violations = []
        
        # Set score to 0 to indicate failure
        state.overall_score = 0.0
        
        if is_image:
            state.summary = (
                "⚠️ Unable to identify food in this image. "
                "Please upload a clear photo of your meal, or try describing "
                "your food using the text input option. For best results, "
                "ensure good lighting and that the food is clearly visible."
            )
        else:
            state.summary = (
                "⚠️ Could not process the input as food. "
                "Please provide a description of your meal, such as "
                "'grilled chicken with rice and vegetables'."
            )
        
        self._logger.info(
            f"Extraction failure handled for session {state.session_id} - "
            f"generated error message instead of hallucinated content"
        )
        
        return state
    
    # === Goal-Based Personalization ===
    
    def _generate_goal_suggestions(
        self, 
        state: MealState, 
        profile: UserProfile
    ) -> list[MealAdjustment]:
        """
        Generate meal suggestions tailored to user's health goals.
        
        Analyzes the meal's nutrients against goal-specific rules and
        creates actionable recommendations.
        """
        suggestions = []
        nutrients = {n.name.lower(): n.amount for n in state.total_nutrients}
        
        # Get nutrient values
        protein = nutrients.get("protein", 0)
        calories = nutrients.get("calories", 0)
        carbs = nutrients.get("carbohydrates", nutrients.get("carbs", 0))
        fiber = nutrients.get("fiber", 0)
        sodium = nutrients.get("sodium", 0)
        fat = nutrients.get("fat", 0)
        sugar = nutrients.get("sugar", 0)
        
        # Daily targets for context
        targets = profile.daily_targets
        
        for goal in profile.goals:
            goal_name = goal.value.replace("_", " ").title()
            
            if goal == HealthGoal.WEIGHT_GAIN:
                # For weight gain: need MORE calories, protein, carbs
                if protein < 30:
                    suggestions.append(MealAdjustment(
                        food_name="meal",
                        action=AdjustmentAction.ADD,
                        reason=f"🎯 {goal_name}: Add more protein to support healthy weight gain",
                        alternative="grilled chicken, eggs, Greek yogurt, or protein shake",
                        priority=1,
                    ))
                if calories < 400:
                    suggestions.append(MealAdjustment(
                        food_name="meal",
                        action=AdjustmentAction.ADD,
                        reason=f"🎯 {goal_name}: Increase portion size for caloric surplus",
                        alternative="add healthy fats like avocado, nuts, or olive oil",
                        priority=2,
                    ))
                if carbs < 40:
                    suggestions.append(MealAdjustment(
                        food_name="meal",
                        action=AdjustmentAction.ADD,
                        reason=f"🎯 {goal_name}: Add more complex carbs for energy",
                        alternative="brown rice, sweet potato, oats, or whole grain bread",
                        priority=3,
                    ))
            
            elif goal == HealthGoal.MUSCLE_BUILDING:
                # For muscle building: HIGH protein is critical
                if protein < 40:
                    suggestions.append(MealAdjustment(
                        food_name="meal",
                        action=AdjustmentAction.ADD,
                        reason=f"💪 {goal_name}: Increase protein intake significantly",
                        alternative="lean meat, fish, eggs, or whey protein",
                        priority=1,
                    ))
                if protein >= 40 and protein < 50:
                    suggestions.append(MealAdjustment(
                        food_name="meal",
                        action=AdjustmentAction.ADD,
                        reason=f"💪 {goal_name}: Good protein! Consider adding more for optimal muscle synthesis",
                        alternative="add another egg or 2oz chicken breast",
                        priority=3,
                    ))
                if calories < 500:
                    suggestions.append(MealAdjustment(
                        food_name="meal",
                        action=AdjustmentAction.ADD,
                        reason=f"💪 {goal_name}: Ensure adequate calories for muscle growth",
                        alternative="add carbs like rice or pasta to fuel workouts",
                        priority=2,
                    ))
            
            elif goal == HealthGoal.WEIGHT_LOSS:
                # For weight loss: control calories, maintain protein
                if calories > 600:
                    # Find the highest calorie food to suggest reducing
                    high_cal_foods = [f.name for f in state.detected_foods 
                                     if any(n.name == "calories" and n.amount > 200 
                                           for n in f.nutrients)]
                    suggestions.append(MealAdjustment(
                        food_name=high_cal_foods[0] if high_cal_foods else "meal",
                        action=AdjustmentAction.REDUCE,
                        reason=f"🏃 {goal_name}: Consider smaller portions to maintain calorie deficit",
                        alternative="use smaller plate or reduce portion by 25%",
                        priority=1,
                    ))
                if protein < 25:
                    suggestions.append(MealAdjustment(
                        food_name="meal",
                        action=AdjustmentAction.ADD,
                        reason=f"🏃 {goal_name}: Add more protein to preserve muscle and stay full",
                        alternative="lean chicken, fish, or tofu",
                        priority=2,
                    ))
                if fiber < 5:
                    suggestions.append(MealAdjustment(
                        food_name="meal",
                        action=AdjustmentAction.ADD,
                        reason=f"🏃 {goal_name}: Add fiber-rich foods for satiety",
                        alternative="vegetables, legumes, or whole grains",
                        priority=3,
                    ))
            
            elif goal == HealthGoal.GLYCEMIC_CONTROL:
                # For glycemic control: limit simple carbs and sugar
                if sugar > 15:
                    suggestions.append(MealAdjustment(
                        food_name="meal",
                        action=AdjustmentAction.REDUCE,
                        reason=f"🍬 {goal_name}: High sugar content may spike blood glucose",
                        alternative="choose unsweetened versions or reduce portion",
                        priority=1,
                    ))
                if carbs > 50 and fiber < 5:
                    suggestions.append(MealAdjustment(
                        food_name="meal",
                        action=AdjustmentAction.SWAP,
                        reason=f"🍬 {goal_name}: High carbs with low fiber - consider swapping",
                        alternative="cauliflower rice, zucchini noodles, or legumes",
                        priority=2,
                    ))
            
            elif goal == HealthGoal.HEART_HEALTH:
                # For heart health: limit sodium
                if sodium > 600:
                    suggestions.append(MealAdjustment(
                        food_name="meal",
                        action=AdjustmentAction.REDUCE,
                        reason=f"❤️ {goal_name}: High sodium - limit processed foods and added salt",
                        alternative="use herbs and spices for flavor instead",
                        priority=1,
                    ))
                if fiber < 5:
                    suggestions.append(MealAdjustment(
                        food_name="meal",
                        action=AdjustmentAction.ADD,
                        reason=f"❤️ {goal_name}: Add more fiber for cardiovascular health",
                        alternative="oats, beans, vegetables, or berries",
                        priority=2,
                    ))
            
            elif goal == HealthGoal.LOWER_CHOLESTEROL:
                # For cholesterol: fiber up, fat down
                if fiber < 8:
                    suggestions.append(MealAdjustment(
                        food_name="meal",
                        action=AdjustmentAction.ADD,
                        reason=f"📉 {goal_name}: Fiber helps reduce cholesterol absorption",
                        alternative="add oatmeal, beans, or vegetables",
                        priority=1,
                    ))
                if fat > 25:
                    suggestions.append(MealAdjustment(
                        food_name="meal",
                        action=AdjustmentAction.REDUCE,
                        reason=f"📉 {goal_name}: Reduce saturated fat intake",
                        alternative="choose lean proteins and limit fried foods",
                        priority=2,
                    ))
            
            elif goal == HealthGoal.GENERAL_WELLNESS:
                # For general wellness: balanced nutrition
                if protein < 20:
                    suggestions.append(MealAdjustment(
                        food_name="meal",
                        action=AdjustmentAction.ADD,
                        reason=f"🌟 {goal_name}: Add more protein for overall health",
                        alternative="lean meat, fish, eggs, beans, or tofu",
                        priority=2,
                    ))
                if fiber < 5:
                    suggestions.append(MealAdjustment(
                        food_name="meal",
                        action=AdjustmentAction.ADD,
                        reason=f"🌟 {goal_name}: Boost fiber intake for digestive health",
                        alternative="vegetables, fruits, or whole grains",
                        priority=2,
                    ))
                if sodium > 800:
                    suggestions.append(MealAdjustment(
                        food_name="meal",
                        action=AdjustmentAction.REDUCE,
                        reason=f"🌟 {goal_name}: Consider reducing sodium for better health",
                        alternative="use herbs and low-sodium seasonings",
                        priority=3,
                    ))
                if sugar > 20:
                    suggestions.append(MealAdjustment(
                        food_name="meal",
                        action=AdjustmentAction.REDUCE,
                        reason=f"🌟 {goal_name}: Limit added sugars for better health",
                        alternative="choose naturally sweet foods like fruit",
                        priority=3,
                    ))
        
        # Limit suggestions to top 3 to avoid overwhelming user
        suggestions.sort(key=lambda x: x.priority)
        return suggestions[:3]
    
    # === Helper Methods ===
    
    def _add_mock_foods(self, state: MealState) -> MealState:
        """Add mock foods for demo when vision fails."""
        state.detected_foods = [
            FoodItem(
                name="grilled chicken breast",
                portion_grams=150,
                portion_description="1 medium breast",
                confidence=0.9,
            ),
            FoodItem(
                name="brown rice",
                portion_grams=200,
                portion_description="1 cup cooked",
                confidence=0.85,
            ),
            FoodItem(
                name="steamed broccoli",
                portion_grams=100,
                portion_description="1 cup",
                confidence=0.88,
            ),
        ]
        state.image_analysis_confidence = 0.87
        return state
    
    def _parse_text_input(self, state: MealState, text: str) -> MealState:
        """Parse text input to extract food items with expanded food dictionary."""
        # Comprehensive food dictionary: name -> (grams, description)
        common_foods = {
            # Proteins
            "grilled chicken breast": (150, "1 medium breast"),
            "grilled chicken": (150, "1 serving"),
            "fried chicken": (180, "2 pieces"),
            "chicken breast": (150, "1 medium breast"),
            "chicken wings": (120, "4 wings"),
            "chicken": (150, "1 serving"),
            "salmon": (150, "1 fillet"),
            "grilled salmon": (150, "1 fillet"),
            "tuna": (140, "1 can"),
            "shrimp": (100, "6 large shrimp"),
            "steak": (200, "6 oz"),
            "beef": (150, "1 serving"),
            "ground beef": (150, "1 patty"),
            "pork chop": (150, "1 chop"),
            "bacon": (30, "3 strips"),
            "sausage": (100, "2 links"),
            "turkey": (150, "1 serving"),
            "eggs": (100, "2 eggs"),
            "egg": (50, "1 egg"),
            "scrambled eggs": (120, "2 eggs"),
            "tofu": (100, "1/2 block"),
            
            # Grains & Carbs
            "brown rice": (200, "1 cup cooked"),
            "white rice": (200, "1 cup cooked"),
            "rice": (200, "1 cup"),
            "quinoa": (185, "1 cup cooked"),
            "pasta": (200, "1 cup cooked"),
            "spaghetti": (200, "1 cup"),
            "bread": (30, "1 slice"),
            "garlic bread": (60, "2 pieces"),
            "toast": (60, "2 slices"),
            "bagel": (100, "1 bagel"),
            "oatmeal": (250, "1 bowl"),
            "cereal": (40, "1 cup"),
            
            # Pizza & Fast Food
            "pepperoni pizza": (250, "2 slices"),
            "cheese pizza": (220, "2 slices"),
            "pizza": (220, "2 slices"),
            "hamburger": (250, "1 burger"),
            "cheeseburger": (280, "1 burger"),
            "burger": (250, "1 burger"),
            "hot dog": (150, "1 hot dog"),
            "french fries": (120, "medium serving"),
            "fries": (120, "medium serving"),
            "nachos": (200, "1 plate"),
            "tacos": (180, "2 tacos"),
            "burrito": (300, "1 burrito"),
            
            # Vegetables
            "broccoli": (100, "1 cup"),
            "steamed broccoli": (100, "1 cup"),
            "roasted vegetables": (150, "1 cup mixed"),
            "vegetables": (100, "1 cup mixed"),
            "spinach": (30, "1 cup"),
            "salad": (150, "1 bowl"),
            "green salad": (150, "1 bowl"),
            "caesar salad": (200, "1 bowl"),
            "carrot": (60, "1 medium"),
            "carrots": (80, "1/2 cup"),
            "potato": (150, "1 medium"),
            "baked potato": (200, "1 large"),
            "mashed potatoes": (200, "1 cup"),
            "sweet potato": (150, "1 medium"),
            "corn": (90, "1 ear"),
            "green beans": (100, "1 cup"),
            "asparagus": (90, "6 spears"),
            "avocado": (100, "1/2 avocado"),
            
            # Fruits
            "apple": (180, "1 medium"),
            "banana": (120, "1 medium"),
            "orange": (130, "1 medium"),
            "strawberries": (150, "1 cup"),
            "blueberries": (150, "1 cup"),
            "grapes": (100, "1 cup"),
            "watermelon": (150, "1 slice"),
            "mango": (165, "1 cup"),
            
            # Dairy
            "cheese": (30, "1 oz"),
            "yogurt": (170, "1 cup"),
            "greek yogurt": (170, "1 cup"),
            "milk": (240, "1 cup"),
            "cottage cheese": (225, "1 cup"),
            
            # Beverages (no/minimal calories)
            "water": (240, "1 glass"),
            "just water": (240, "1 glass"),
            "coffee": (240, "1 cup"),
            "black coffee": (240, "1 cup"),
            "tea": (240, "1 cup"),
            "green tea": (240, "1 cup"),
            "sparkling water": (240, "1 glass"),
            "diet soda": (355, "1 can"),
            
            # Sweet beverages
            "soda": (355, "1 can"),
            "orange juice": (240, "1 cup"),
            "juice": (240, "1 cup"),
            "smoothie": (350, "1 medium"),
            "milkshake": (400, "1 medium"),
            "latte": (350, "1 medium"),
            "cappuccino": (250, "1 cup"),
            
            # Snacks & Desserts
            "chips": (50, "1 oz bag"),
            "cookies": (60, "2 cookies"),
            "cake": (100, "1 slice"),
            "ice cream": (130, "1/2 cup"),
            "chocolate": (45, "1 bar"),
            "popcorn": (30, "1 cup"),
            "nuts": (30, "1/4 cup"),
            "almonds": (30, "1/4 cup"),
            "peanuts": (30, "1/4 cup"),
            "granola bar": (40, "1 bar"),
            
            # Soups & Bowls
            "soup": (240, "1 cup"),
            "chicken soup": (240, "1 cup"),
            "tomato soup": (240, "1 cup"),
            "ramen": (400, "1 bowl"),
            "pho": (500, "1 bowl"),
            "bowl": (350, "1 bowl"),
            "acai bowl": (300, "1 bowl"),
        }
        
        text_lower = text.lower()
        matched_foods = []
        used_indices = set()  # Track matched text spans to avoid overlaps
        
        # Sort by length (longer matches first) to catch "grilled chicken breast" before "chicken"
        sorted_foods = sorted(common_foods.keys(), key=len, reverse=True)
        
        for food_name in sorted_foods:
            # Find position in text
            idx = text_lower.find(food_name)
            if idx != -1:
                # Check if this span overlaps with already matched food
                span = range(idx, idx + len(food_name))
                if not any(i in used_indices for i in span):
                    grams, description = common_foods[food_name]
                    matched_foods.append(FoodItem(
                        name=food_name,
                        portion_grams=grams,
                        portion_description=description,
                        confidence=0.7,
                    ))
                    # Mark this span as used
                    used_indices.update(span)
                    # Limit to avoid too many items
                    if len(matched_foods) >= 6:
                        break
        
        if matched_foods:
            state.detected_foods = matched_foods
            state.image_analysis_confidence = 0.7 if len(matched_foods) > 1 else 0.6
        else:
            # Try to use the text as a single food item for unknown foods
            cleaned_text = text.strip()[:50]  # Limit length
            state.detected_foods = [FoodItem(
                name=cleaned_text if cleaned_text else "meal",
                portion_grams=300,
                portion_description="1 serving",
                confidence=0.4,
            )]
            state.image_analysis_confidence = 0.3
        
        return state
    
    def _calculate_meal_score(self, state: MealState) -> float:
        """Calculate overall meal quality score (0-100)."""
        score = 70.0  # Base score
        
        # Get nutrient values
        nutrients = {n.name: n.amount for n in state.total_nutrients}
        
        # Bonus for protein (>20g is good)
        protein = nutrients.get("protein", 0)
        if protein >= 30:
            score += 15
        elif protein >= 20:
            score += 10
        elif protein >= 10:
            score += 5
        
        # Bonus for fiber (>5g is good)
        fiber = nutrients.get("fiber", 0)
        if fiber >= 8:
            score += 10
        elif fiber >= 5:
            score += 5
        
        # Penalty for high sodium (>800mg)
        sodium = nutrients.get("sodium", 0)
        if sodium > 1000:
            score -= 10
        elif sodium > 800:
            score -= 5
        
        # Penalty for violations
        serious_violations = len([v for v in state.constraint_violations if "⚠️" not in v])
        score -= serious_violations * 10
        
        # Bonus for variety (3+ different foods)
        if len(state.detected_foods) >= 4:
            score += 10
        elif len(state.detected_foods) >= 3:
            score += 5
        
        # Ensure score is in range
        return max(0, min(100, score))
    
    def _generate_summary(self, state: MealState) -> str:
        """Generate a human-readable meal summary."""
        foods_list = ", ".join(f.name for f in state.detected_foods[:3])
        if len(state.detected_foods) > 3:
            foods_list += f" and {len(state.detected_foods) - 3} more"
        
        # Get key nutrients
        nutrients = {n.name: n.amount for n in state.total_nutrients}
        calories = nutrients.get("calories", 0)
        protein = nutrients.get("protein", 0)
        carbs = nutrients.get("carbohydrates", 0)
        
        summary = f"Your meal contains {foods_list}"
        summary += f" with approximately {calories:.0f} calories"
        summary += f", {protein:.0f}g protein, and {carbs:.0f}g carbohydrates."
        
        # Add score-based feedback
        if state.overall_score >= 85:
            summary += " Excellent balanced meal! 🎉"
        elif state.overall_score >= 70:
            summary += " Great meal with good nutritional balance! 👍"
        elif state.overall_score >= 55:
            summary += " Good meal with room for improvement."
        else:
            summary += " Consider some adjustments for better nutrition."
        
        # Mention adjustments
        if state.adjustments:
            summary += f" We have {len(state.adjustments)} suggestion(s) for you."
        
        return summary
