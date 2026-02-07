"""
NutriPilot AI - BioDataScout Agent

Queries user health data to provide personalized meal constraints.
For MVP, this uses mock HealthKit-style data. In production, this would
integrate with Apple HealthKit, Google Fit, or wearable APIs.

This agent supports the THINK phase of the pipeline.
"""

import logging
import random
import time
from datetime import datetime, timedelta
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
from app.core.state import (
    BioDataQuery, 
    BioDataReport, 
    HealthConstraint, 
    ConstraintStatus
)
from app.config import get_settings

logger = logging.getLogger(__name__)


# Mock user health profiles
MOCK_USER_PROFILES = {
    "demo_user": {
        "name": "Demo User",
        "age": 35,
        "weight_kg": 75,
        "height_cm": 175,
        "conditions": ["pre_diabetic"],
        "allergies": [],
        "dietary_restrictions": [],
    },
    "diabetic_user": {
        "name": "Diabetic User",
        "age": 52,
        "weight_kg": 82,
        "height_cm": 170,
        "conditions": ["type_2_diabetes", "hypertension"],
        "allergies": ["peanuts"],
        "dietary_restrictions": ["low_sodium", "low_sugar"],
    },
    "athlete_user": {
        "name": "Athlete User",
        "age": 28,
        "weight_kg": 70,
        "height_cm": 180,
        "conditions": [],
        "allergies": ["shellfish"],
        "dietary_restrictions": ["high_protein"],
    },
    "default": {
        "name": "Default User",
        "age": 30,
        "weight_kg": 70,
        "height_cm": 170,
        "conditions": [],
        "allergies": [],
        "dietary_restrictions": [],
    }
}


class BioDataScout(BaseAgent[BioDataQuery, BioDataReport]):
    """
    Specialized agent for querying user health data and constraints.
    
    Simulates HealthKit/wearable data including:
    - Blood glucose levels (from CGM or manual entry)
    - Sleep quality and duration
    - Activity level and step count
    - Heart rate and HRV
    - Known allergies and dietary restrictions
    
    The data varies realistically based on time of day and random factors
    to simulate real health fluctuations.
    
    Example:
        scout = BioDataScout()
        result = await scout.execute(BioDataQuery(user_id="demo_user"))
    """
    
    def __init__(self):
        """Initialize BioDataScout."""
        super().__init__(max_retries=2, retry_delay=0.5)
        self.settings = get_settings()
    
    @property
    def name(self) -> str:
        return "BioDataScout"
    
    @track(name="biodata_scout.process")
    async def process(self, input: BioDataQuery) -> BioDataReport:
        """
        Query health data for a user and return active constraints.
        
        Args:
            input: BioDataQuery with user_id and optional constraint types
            
        Returns:
            BioDataReport with health constraints and any critical alerts
        """
        start_time = time.time()
        
        # Get user profile (or default)
        profile = MOCK_USER_PROFILES.get(
            input.user_id, 
            MOCK_USER_PROFILES["default"]
        )
        
        # Generate current health metrics
        constraints = []
        alerts = []
        
        # Check which constraint types to query
        query_types = input.constraint_types or [
            "blood_glucose", 
            "sleep_quality", 
            "activity_level",
            "sodium_intake",
            "allergens"
        ]
        
        for constraint_type in query_types:
            constraint = self._generate_constraint(constraint_type, profile)
            if constraint:
                constraints.append(constraint)
                
                # Check for critical alerts
                if constraint.status == ConstraintStatus.CRITICAL:
                    alerts.append(
                        f"⚠️ CRITICAL: {constraint.constraint_type} at "
                        f"{constraint.value} {constraint.unit}"
                    )
        
        # Add allergy constraints
        for allergy in profile.get("allergies", []):
            constraints.append(HealthConstraint(
                constraint_type=f"allergy_{allergy}",
                value=1.0,  # Presence indicator
                unit="boolean",
                status=ConstraintStatus.CRITICAL,
                recommendation=f"Avoid all {allergy} and {allergy}-containing products",
            ))
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        logger.info(
            f"BioDataScout queried {len(constraints)} constraints for user "
            f"{input.user_id} in {latency_ms}ms"
        )
        
        return BioDataReport(
            user_id=input.user_id,
            constraints=constraints,
            alerts=alerts,
            last_updated=datetime.utcnow(),
        )
    
    def _generate_constraint(
        self, 
        constraint_type: str, 
        profile: dict
    ) -> Optional[HealthConstraint]:
        """Generate a realistic health constraint based on type and profile."""
        
        # Time-based factors
        hour = datetime.now().hour
        is_morning = 6 <= hour < 12
        is_post_meal = hour in [8, 9, 13, 14, 19, 20]  # Typical meal times
        
        if constraint_type == "blood_glucose":
            return self._generate_glucose_constraint(profile, is_morning, is_post_meal)
        
        elif constraint_type == "sleep_quality":
            return self._generate_sleep_constraint(profile)
        
        elif constraint_type == "activity_level":
            return self._generate_activity_constraint(profile, hour)
        
        elif constraint_type == "sodium_intake":
            return self._generate_sodium_constraint(profile)
        
        elif constraint_type == "heart_rate":
            return self._generate_heart_rate_constraint(profile)
        
        return None
    
    def _generate_glucose_constraint(
        self, 
        profile: dict, 
        is_morning: bool,
        is_post_meal: bool
    ) -> HealthConstraint:
        """Generate blood glucose reading with realistic variation."""
        
        # Base glucose depends on conditions
        has_diabetes = any(
            c in ["type_2_diabetes", "pre_diabetic"] 
            for c in profile.get("conditions", [])
        )
        
        if has_diabetes:
            base_glucose = random.uniform(100, 130)
        else:
            base_glucose = random.uniform(75, 95)
        
        # Morning fasting glucose is typically lower
        if is_morning:
            base_glucose -= random.uniform(5, 15)
        
        # Post-meal glucose spikes
        if is_post_meal:
            base_glucose += random.uniform(20, 45)
        
        # Add daily variation
        base_glucose += random.uniform(-10, 10)
        
        # Clamp to realistic range
        glucose = max(60, min(200, base_glucose))
        
        # Determine status
        if glucose < 70:
            status = ConstraintStatus.CRITICAL
            recommendation = "Low blood sugar! Consider a small snack with quick carbs."
        elif glucose > 140:
            status = ConstraintStatus.WARNING
            recommendation = "Elevated glucose. Consider low-glycemic foods."
        elif glucose > 100:
            status = ConstraintStatus.WARNING
            recommendation = "Slightly elevated. Consider reducing simple carbs."
        else:
            status = ConstraintStatus.NORMAL
            recommendation = None
        
        return HealthConstraint(
            constraint_type="blood_glucose",
            value=round(glucose, 1),
            unit="mg/dL",
            status=status,
            threshold_low=70.0,
            threshold_high=100.0,  # Fasting normal
            recommendation=recommendation,
        )
    
    def _generate_sleep_constraint(self, profile: dict) -> HealthConstraint:
        """Generate sleep quality metric."""
        
        # Random sleep quality with some variation
        sleep_hours = random.uniform(5.5, 8.5)
        sleep_quality = random.uniform(0.5, 0.95)
        
        # Calculate combined score
        sleep_score = (sleep_hours / 8.0) * 0.5 + sleep_quality * 0.5
        sleep_score = min(1.0, sleep_score)
        
        if sleep_score < 0.5:
            status = ConstraintStatus.WARNING
            recommendation = "Poor sleep may affect glucose regulation. Consider lighter meals."
        elif sleep_score < 0.7:
            status = ConstraintStatus.NORMAL
            recommendation = "Adequate sleep, but improvement possible."
        else:
            status = ConstraintStatus.NORMAL
            recommendation = None
        
        return HealthConstraint(
            constraint_type="sleep_quality",
            value=round(sleep_score, 2),
            unit="score",
            status=status,
            threshold_low=0.5,
            threshold_high=1.0,
            recommendation=recommendation,
        )
    
    def _generate_activity_constraint(
        self, 
        profile: dict, 
        hour: int
    ) -> HealthConstraint:
        """Generate daily activity level."""
        
        # Steps accumulate throughout day
        max_steps = random.uniform(8000, 15000)
        current_steps = int(max_steps * (hour / 24))
        
        # Activity level categories
        if current_steps < 3000:
            level = "sedentary"
            status = ConstraintStatus.NORMAL
        elif current_steps < 7000:
            level = "lightly_active"
            status = ConstraintStatus.NORMAL
        elif current_steps < 10000:
            level = "moderately_active"
            status = ConstraintStatus.NORMAL
        else:
            level = "very_active"
            status = ConstraintStatus.NORMAL
        
        recommendation = None
        if level == "sedentary" and hour > 14:
            recommendation = "Low activity today. A post-meal walk could help glucose control."
        
        return HealthConstraint(
            constraint_type="activity_level",
            value=float(current_steps),
            unit="steps",
            status=status,
            recommendation=recommendation,
        )
    
    def _generate_sodium_constraint(self, profile: dict) -> HealthConstraint:
        """Generate estimated daily sodium intake."""
        
        has_hypertension = "hypertension" in profile.get("conditions", [])
        has_low_sodium_diet = "low_sodium" in profile.get("dietary_restrictions", [])
        
        # Accumulated sodium throughout day
        hour = datetime.now().hour
        meals_eaten = min(3, hour // 6)  # Rough meal estimation
        
        # Average sodium per meal with variation
        sodium_per_meal = random.uniform(600, 1200)
        daily_sodium = meals_eaten * sodium_per_meal + random.uniform(0, 300)
        
        # Threshold depends on conditions
        threshold = 1500 if (has_hypertension or has_low_sodium_diet) else 2300
        
        if daily_sodium > threshold:
            status = ConstraintStatus.WARNING
            recommendation = f"Sodium intake high ({daily_sodium:.0f}mg). Choose low-sodium options."
        else:
            status = ConstraintStatus.NORMAL
            recommendation = None
        
        return HealthConstraint(
            constraint_type="daily_sodium",
            value=round(daily_sodium, 0),
            unit="mg",
            status=status,
            threshold_high=float(threshold),
            recommendation=recommendation,
        )
    
    def _generate_heart_rate_constraint(self, profile: dict) -> HealthConstraint:
        """Generate current heart rate."""
        
        # Base heart rate with age adjustment
        age = profile.get("age", 30)
        base_hr = 70 - (age - 30) * 0.2  # Older = slightly higher resting HR
        
        # Random variation
        hr = base_hr + random.uniform(-10, 20)
        hr = max(50, min(100, hr))
        
        status = ConstraintStatus.NORMAL
        recommendation = None
        
        if hr > 90:
            status = ConstraintStatus.WARNING
            recommendation = "Elevated heart rate. Consider a calming meal environment."
        
        return HealthConstraint(
            constraint_type="heart_rate",
            value=round(hr, 0),
            unit="bpm",
            status=status,
            threshold_low=50.0,
            threshold_high=100.0,
            recommendation=recommendation,
        )
