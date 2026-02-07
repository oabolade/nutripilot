"""
NutriPilot AI - In-Memory Storage

Simple storage layer for user profiles and meal history.
Can be replaced with a database (PostgreSQL, MongoDB) for production.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from collections import defaultdict

from app.core.user_goals import UserProfile, MealLogEntry, DashboardData

logger = logging.getLogger(__name__)


class InMemoryStorage:
    """
    Thread-safe in-memory storage for user data.
    
    For demo purposes - replace with database for production.
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern to ensure single storage instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._profiles: dict[str, UserProfile] = {}
            cls._instance._meal_logs: dict[str, list[MealLogEntry]] = defaultdict(list)
            cls._instance._initialized = True
            logger.info("InMemoryStorage initialized")
        return cls._instance
    
    # === Profile Management ===
    
    def save_profile(self, profile: UserProfile) -> UserProfile:
        """Save or update a user profile."""
        profile.updated_at = datetime.utcnow()
        self._profiles[profile.user_id] = profile
        logger.info(f"Saved profile for user {profile.user_id}")
        return profile
    
    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get a user profile by ID."""
        return self._profiles.get(user_id)
    
    def delete_profile(self, user_id: str) -> bool:
        """Delete a user profile and all associated meal history (full reset)."""
        deleted = False
        
        if user_id in self._profiles:
            del self._profiles[user_id]
            deleted = True
            logger.info(f"Deleted profile for user {user_id}")
        
        if user_id in self._meal_logs:
            meal_count = len(self._meal_logs[user_id])
            del self._meal_logs[user_id]
            logger.info(f"Deleted {meal_count} meals for user {user_id}")
            deleted = True
        
        return deleted
    
    def profile_exists(self, user_id: str) -> bool:
        """Check if a profile exists."""
        return user_id in self._profiles
    
    # === Meal Logging ===
    
    def log_meal(self, entry: MealLogEntry) -> MealLogEntry:
        """Log a meal entry for a user."""
        self._meal_logs[entry.user_id].append(entry)
        logger.info(f"Logged meal for user {entry.user_id}: {entry.entry_id}")
        return entry
    
    def get_meal_history(
        self, 
        user_id: str, 
        days: int = 30,
        limit: int = 50
    ) -> list[MealLogEntry]:
        """Get meal history for a user within the specified time range."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        meals = [
            meal for meal in self._meal_logs[user_id]
            if meal.timestamp >= cutoff
        ]
        
        # Sort by timestamp descending (newest first)
        meals.sort(key=lambda m: m.timestamp, reverse=True)
        
        return meals[:limit]
    
    def get_meals_today(self, user_id: str) -> list[MealLogEntry]:
        """Get all meals logged today."""
        today = datetime.utcnow().date()
        return [
            meal for meal in self._meal_logs[user_id]
            if meal.timestamp.date() == today
        ]
    
    def get_total_meals(self, user_id: str) -> int:
        """Get total number of meals logged."""
        return len(self._meal_logs[user_id])
    
    # === Dashboard Data ===
    
    def get_dashboard_data(self, user_id: str) -> DashboardData:
        """Generate dashboard data for a user."""
        profile = self.get_profile(user_id)
        meals = self._meal_logs[user_id]
        
        # NOTE: Mock data auto-populate disabled to allow proper testing of reset flow
        # To re-enable demo data, uncomment the following:
        # if user_id == "demo_user" and not meals and profile:
        #     self._populate_mock_data(user_id)
        #     meals = self._meal_logs[user_id]
        
        if not meals:
            return DashboardData(
                user_id=user_id,
                profile=profile,
                days_active=0,
                meals_logged=0,
                average_meal_score=0,
                average_goal_alignment=0,
                goal_progress={},
                nutrient_trends={},
                recent_meals=[]
            )
        
        # Calculate metrics
        days_active = 0
        if profile:
            days_active = (datetime.utcnow() - profile.start_date).days
        
        avg_meal_score = sum(m.meal_score for m in meals) / len(meals)
        avg_goal_alignment = sum(m.goal_alignment_score for m in meals) / len(meals)
        
        # Calculate goal progress (simplified - based on average alignment)
        goal_progress = {}
        if profile and profile.goals:
            for goal in profile.goals:
                # Progress is a function of days active and meal quality
                progress = min(100, (days_active / 7) * 10 + avg_goal_alignment * 0.5)
                goal_progress[goal.value] = round(progress, 1)
        
        # Calculate nutrient trends (last 7 days)
        nutrient_trends = self._calculate_nutrient_trends(user_id, profile, days=7)
        
        # Get recent meals
        recent_meals = sorted(meals, key=lambda m: m.timestamp, reverse=True)[:10]
        
        return DashboardData(
            user_id=user_id,
            profile=profile,
            days_active=days_active,
            meals_logged=len(meals),
            average_meal_score=round(avg_meal_score, 1),
            average_goal_alignment=round(avg_goal_alignment, 1),
            goal_progress=goal_progress,
            nutrient_trends=nutrient_trends,
            recent_meals=recent_meals
        )
    
    def _populate_mock_data(self, user_id: str):
        """Populate realistic mock meal data for demo purposes."""
        import random
        from uuid import uuid4
        
        logger.info(f"Populating mock data for user {user_id}")
        
        # Update profile start date to 3 weeks ago
        profile = self.get_profile(user_id)
        if profile:
            profile.start_date = datetime.utcnow() - timedelta(days=21)
            self.save_profile(profile)
        
        # Sample meals with varying quality - showing improvement over time
        # Week 1: Learning phase (lower scores)
        # Week 2: Improving (medium scores)
        # Week 3: Getting better (higher scores)
        
        meal_templates = [
            # Breakfast options
            {
                "foods": ["oatmeal", "blueberries", "almonds"],
                "meal_type": "breakfast",
                "base_score": 85,
                "calories": 380, "protein": 12, "carbs": 58, "fat": 14, "fiber": 8, "sodium": 120
            },
            {
                "foods": ["scrambled eggs", "whole wheat toast", "avocado"],
                "meal_type": "breakfast",
                "base_score": 82,
                "calories": 420, "protein": 18, "carbs": 32, "fat": 26, "fiber": 9, "sodium": 450
            },
            {
                "foods": ["greek yogurt", "granola", "honey"],
                "meal_type": "breakfast",
                "base_score": 75,
                "calories": 350, "protein": 20, "carbs": 48, "fat": 8, "fiber": 3, "sodium": 100
            },
            {
                "foods": ["pancakes", "syrup", "bacon"],
                "meal_type": "breakfast",
                "base_score": 45,
                "calories": 680, "protein": 15, "carbs": 85, "fat": 32, "fiber": 2, "sodium": 980
            },
            # Lunch options
            {
                "foods": ["grilled chicken salad", "olive oil dressing", "cherry tomatoes"],
                "meal_type": "lunch",
                "base_score": 92,
                "calories": 420, "protein": 38, "carbs": 18, "fat": 22, "fiber": 6, "sodium": 580
            },
            {
                "foods": ["turkey sandwich", "whole grain bread", "side salad"],
                "meal_type": "lunch",
                "base_score": 78,
                "calories": 520, "protein": 32, "carbs": 48, "fat": 18, "fiber": 7, "sodium": 890
            },
            {
                "foods": ["pizza slice", "soda"],
                "meal_type": "lunch",
                "base_score": 35,
                "calories": 650, "protein": 18, "carbs": 78, "fat": 28, "fiber": 3, "sodium": 1450
            },
            {
                "foods": ["quinoa bowl", "grilled vegetables", "chickpeas"],
                "meal_type": "lunch",
                "base_score": 88,
                "calories": 480, "protein": 18, "carbs": 62, "fat": 16, "fiber": 12, "sodium": 420
            },
            # Dinner options
            {
                "foods": ["grilled salmon", "brown rice", "steamed broccoli"],
                "meal_type": "dinner",
                "base_score": 95,
                "calories": 580, "protein": 42, "carbs": 45, "fat": 22, "fiber": 8, "sodium": 380
            },
            {
                "foods": ["chicken stir-fry", "white rice", "vegetables"],
                "meal_type": "dinner",
                "base_score": 75,
                "calories": 620, "protein": 35, "carbs": 68, "fat": 18, "fiber": 5, "sodium": 1100
            },
            {
                "foods": ["pasta carbonara", "garlic bread"],
                "meal_type": "dinner",
                "base_score": 42,
                "calories": 920, "protein": 28, "carbs": 98, "fat": 45, "fiber": 4, "sodium": 1680
            },
            {
                "foods": ["baked chicken breast", "sweet potato", "green beans"],
                "meal_type": "dinner",
                "base_score": 90,
                "calories": 520, "protein": 45, "carbs": 42, "fat": 12, "fiber": 9, "sodium": 320
            },
            # Snacks
            {
                "foods": ["apple", "peanut butter"],
                "meal_type": "snack",
                "base_score": 80,
                "calories": 280, "protein": 8, "carbs": 32, "fat": 16, "fiber": 5, "sodium": 150
            },
            {
                "foods": ["chips", "cookies"],
                "meal_type": "snack",
                "base_score": 25,
                "calories": 420, "protein": 4, "carbs": 58, "fat": 22, "fiber": 2, "sodium": 580
            },
        ]
        
        # Generate meals for the past 21 days (3 weeks)
        for day_offset in range(21, 0, -1):
            meal_date = datetime.utcnow() - timedelta(days=day_offset)
            
            # Determine week for score adjustment (improvement over time)
            week = (21 - day_offset) // 7 + 1
            score_bonus = (week - 1) * 8  # Week 1: +0, Week 2: +8, Week 3: +16
            
            # Generate 2-4 meals per day
            num_meals = random.randint(2, 4)
            
            # Ensure variety - pick different meal types
            used_types = set()
            for _ in range(num_meals):
                # Filter templates to avoid duplicate meal types
                available = [t for t in meal_templates if t["meal_type"] not in used_types or len(used_types) >= 3]
                if not available:
                    available = meal_templates
                
                template = random.choice(available)
                used_types.add(template["meal_type"])
                
                # Add some randomization to the base values
                score_variance = random.randint(-10, 10)
                
                # Better food choices in later weeks
                if week >= 2 and template["base_score"] < 50:
                    # Skip unhealthy choices more often in later weeks
                    if random.random() < 0.6:
                        template = random.choice([t for t in available if t["base_score"] >= 70])
                
                meal_score = min(100, max(20, template["base_score"] + score_bonus + score_variance))
                goal_alignment = min(100, max(15, meal_score + random.randint(-15, 10)))
                
                # Create the meal entry
                meal_time = meal_date.replace(
                    hour={"breakfast": 8, "lunch": 12, "dinner": 19, "snack": 15}[template["meal_type"]] + random.randint(0, 2),
                    minute=random.randint(0, 59)
                )
                
                entry = MealLogEntry(
                    entry_id=str(uuid4()),
                    user_id=user_id,
                    timestamp=meal_time,
                    meal_type=template["meal_type"],
                    food_names=template["foods"],
                    total_calories=template["calories"] * random.uniform(0.9, 1.1),
                    total_protein=template["protein"] * random.uniform(0.9, 1.1),
                    total_carbs=template["carbs"] * random.uniform(0.9, 1.1),
                    total_fat=template["fat"] * random.uniform(0.9, 1.1),
                    total_fiber=template["fiber"] * random.uniform(0.9, 1.1),
                    total_sodium=template["sodium"] * random.uniform(0.9, 1.1),
                    meal_score=meal_score,
                    goal_alignment_score=goal_alignment,
                    goal_feedback=self._generate_mock_feedback(template, goal_alignment)
                )
                
                self._meal_logs[user_id].append(entry)
        
        logger.info(f"Generated {len(self._meal_logs[user_id])} mock meals for user {user_id}")
    
    def _generate_mock_feedback(self, template: dict, alignment: float) -> list[str]:
        """Generate mock goal feedback based on meal quality."""
        feedback = []
        if alignment >= 80:
            feedback.append("✅ Great job! This meal aligns well with your goals!")
        elif alignment >= 60:
            if template.get("fiber", 0) < 5:
                feedback.append("📊 Consider adding more fiber-rich foods")
            if template.get("sodium", 0) > 800:
                feedback.append("⚠️ Watch sodium intake for heart health")
        else:
            if template.get("calories", 0) > 600:
                feedback.append("⚠️ High calorie meal - consider smaller portions")
            if template.get("carbs", 0) > 60:
                feedback.append("📊 Glycemic Control: Carbs are above target")
        return feedback

    def _calculate_nutrient_trends(
        self, 
        user_id: str, 
        profile: Optional[UserProfile],
        days: int = 7
    ) -> dict[str, dict]:
        """Calculate average daily nutrient intake vs targets."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent_meals = [
            m for m in self._meal_logs[user_id]
            if m.timestamp >= cutoff
        ]
        
        if not recent_meals:
            return {}
        
        # Group by date and sum nutrients
        daily_totals: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for meal in recent_meals:
            date_key = meal.timestamp.strftime("%Y-%m-%d")
            daily_totals[date_key]["calories"] += meal.total_calories
            daily_totals[date_key]["protein"] += meal.total_protein
            daily_totals[date_key]["carbs"] += meal.total_carbs
            daily_totals[date_key]["fat"] += meal.total_fat
            daily_totals[date_key]["fiber"] += meal.total_fiber
            daily_totals[date_key]["sodium"] += meal.total_sodium
        
        # Calculate averages
        num_days = len(daily_totals) or 1
        avg_nutrients = {
            "calories": sum(d["calories"] for d in daily_totals.values()) / num_days,
            "protein": sum(d["protein"] for d in daily_totals.values()) / num_days,
            "carbs": sum(d["carbs"] for d in daily_totals.values()) / num_days,
            "fat": sum(d["fat"] for d in daily_totals.values()) / num_days,
            "fiber": sum(d["fiber"] for d in daily_totals.values()) / num_days,
            "sodium": sum(d["sodium"] for d in daily_totals.values()) / num_days,
        }
        
        # Compare to targets if profile exists
        targets = {}
        if profile:
            targets = {
                "calories": profile.daily_targets.calories,
                "protein": profile.daily_targets.protein_g,
                "carbs": profile.daily_targets.carbs_g,
                "fat": profile.daily_targets.fat_g,
                "fiber": profile.daily_targets.fiber_g,
                "sodium": profile.daily_targets.sodium_mg,
            }
        
        return {
            nutrient: {
                "average": round(avg_nutrients[nutrient], 1),
                "target": targets.get(nutrient, 0),
                "percent": round(
                    (avg_nutrients[nutrient] / targets[nutrient] * 100) 
                    if targets.get(nutrient) else 0, 
                    1
                )
            }
            for nutrient in avg_nutrients
        }
    
    # === Utility ===
    
    def clear_all(self):
        """Clear all data (for testing)."""
        self._profiles.clear()
        self._meal_logs.clear()
        logger.warning("All storage data cleared")


# Singleton instance
storage = InMemoryStorage()

