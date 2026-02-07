"""
NutriPilot AI - Actionability LLM-as-a-Judge Metric

Evaluates whether agent advice is appropriately calibrated to the user's
goal timeline (effort tolerance) and provides actionable, accountable guidance.

Key insight: Timeline is a proxy for effort tolerance:
- Short timeline (4-8 weeks) → Aggressive, quantified advice expected
- Moderate timeline (8-16 weeks) → Balanced approach
- Long timeline (16+ weeks) → Sustainable habits, flexible advice

Usage:
    from actionability_metric import ActionabilityMetric
    
    metric = ActionabilityMetric()
    result = metric.score(
        user_goal="Lose 15 lbs",
        timeline="6 weeks",
        agent_output="Consider eating less carbs..."
    )
"""

import json
import os
from typing import Any, List
from pydantic import BaseModel, Field

from opik.evaluation.metrics import base_metric, score_result
from opik.evaluation import models


class ActionabilityJudgment(BaseModel):
    """Structured response from the LLM judge."""
    reasoning: str = Field(description="Step-by-step analysis of the agent's advice")
    timeline_calibration_score: int = Field(ge=1, le=5, description="Does intensity match timeline?")
    specificity_score: int = Field(ge=1, le=5, description="How concrete are the suggestions?")
    accountability_score: int = Field(ge=1, le=5, description="Does it hold user accountable?")
    goal_linkage_score: int = Field(ge=1, le=5, description="Are recommendations tied to the goal?")
    overall_score: int = Field(ge=1, le=5, description="Overall actionability score")
    improvement_suggestion: str = Field(description="How could the advice be more actionable?")


class ActionabilityMetric(base_metric.BaseMetric):
    """
    LLM-as-a-Judge metric for evaluating agent advice actionability.
    
    Evaluates whether advice is appropriately calibrated to timeline and provides
    concrete, accountable guidance that ties back to user goals.
    
    Timeline Interpretation:
    - Aggressive (4-8 weeks): User wants fast results, willing to sacrifice
    - Moderate (8-16 weeks): Balanced approach, reasonable effort
    - Gradual (16+ weeks): Sustainable changes, flexible lifestyle
    
    Scoring Rubric (1-5):
    - 1: Vague - Generic advice with no timeline awareness ("eat healthy")
    - 2: Weak - Some specifics but doesn't match timeline intensity
    - 3: Adequate - Reasonable advice but missing accountability elements
    - 4: Strong - Well-calibrated with clear actions and goal linkage
    - 5: Excellent - Perfect timeline match, highly specific, accountable
    
    Example:
        metric = ActionabilityMetric()
        result = metric.score(
            user_goal="Lose 20 lbs",
            timeline="4 weeks",  # Aggressive!
            agent_output="The meal looks good, try to eat less."  # Too vague!
        )
    """
    
    def __init__(
        self, 
        name: str = "Actionability",
        model_name: str = "gemini/gemini-2.0-flash"
    ):
        super().__init__(name=name)
        self.model_name = model_name
        self.llm_client = models.LiteLLMChatModel(model_name=model_name)
        
        self.prompt_template = """# ROLE
You are an expert Behavioral Nutritionist and Accountability Coach. Your task is to evaluate whether an AI nutrition agent's advice is appropriately calibrated to the user's goal timeline and provides actionable, accountable guidance.

# KEY INSIGHT: TIMELINE AS EFFORT PROXY
The user's timeline indicates their willingness to make sacrifices:
- **Aggressive (4-8 weeks):** User wants fast results, expects strict/specific advice
- **Moderate (8-16 weeks):** Balanced approach, reasonable effort expected
- **Gradual (16+ weeks):** Sustainable lifestyle changes, flexible approach

# INPUT DATA
- **User Goal:** {user_goal}
  (What the user is trying to achieve)
- **Timeline:** {timeline}
  (How long the user has given themselves - indicates effort tolerance)
- **Agent Output:** {agent_output}
  (The nutritional advice/recommendation provided)

# EVALUATION DIMENSIONS

## 1. Timeline Calibration (1-5)
Does the advice intensity match the user's timeline?
- For aggressive timelines: Is advice strict, quantified, urgent?
- For moderate timelines: Is it balanced with clear but flexible guidance?
- For gradual timelines: Is it sustainable, habit-focused, not overwhelming?

## 2. Specificity (1-5)
How concrete are the suggestions?
- 5: Exact portions, specific swaps, precise macros ("Replace the 200g rice with 150g cauliflower rice")
- 3: General guidance with some specifics ("Consider reducing carbs")
- 1: Vague platitudes ("Eat healthier", "Watch your portions")

## 3. Accountability Framing (1-5)
Does the advice hold the user accountable with clear actions?
- 5: Clear "do this" actions, trackable behaviors, no wiggle room
- 3: Suggestions but allows too much interpretation
- 1: Information-only, no call to action

## 4. Goal Linkage (1-5)
Does each recommendation explicitly tie back to the stated goal?
- 5: Every suggestion references how it helps achieve the specific goal
- 3: Some recommendations linked, others disconnected
- 1: Generic advice that could apply to anyone

# SCORING RUBRIC (Overall 1-5)
- **1 (Vague):** Generic advice with no timeline awareness. "Eat healthy and exercise."
- **2 (Weak):** Some specifics but doesn't match timeline intensity or lacks accountability.
- **3 (Adequate):** Reasonable advice but missing key elements (timeline calibration or specificity).
- **4 (Strong):** Well-calibrated intensity, clear actions, good goal linkage.
- **5 (Excellent):** Perfect timeline match, highly specific, accountable, every recommendation tied to goal.

# EXAMPLES

**Example 1: Aggressive Timeline, Vague Advice = Score 1**
Goal: "Lose 15 lbs", Timeline: "4 weeks", Advice: "This meal is okay. Try to make healthier choices."
→ Score 1: User has 4 weeks and needs urgency. This advice is useless.

**Example 2: Gradual Timeline, Aggressive Advice = Score 2**
Goal: "Improve overall health", Timeline: "6 months", Advice: "You MUST cut all carbs immediately and only eat 1200 calories!"
→ Score 2: Timeline suggests gradual change, but advice is unsustainably aggressive.

**Example 3: Matched Timeline, Good Specificity = Score 5**
Goal: "Lose 10 lbs", Timeline: "8 weeks", Advice: "This 600 cal meal fits your 1500/day target. Swap the white rice (40g carbs) for cauliflower rice (5g carbs) to accelerate fat loss while keeping you satisfied. That's 1 lb/week pace - right on track for your 8-week goal."
→ Score 5: Quantified, timeline-aware, specific swap, goal-linked.

# OUTPUT FORMAT
Return ONLY a JSON object with this exact structure (no markdown, no backticks):
{{
  "reasoning": "Your step-by-step analysis of how well the advice matches the timeline, specificity, accountability, and goal linkage.",
  "timeline_calibration_score": <1-5>,
  "specificity_score": <1-5>,
  "accountability_score": <1-5>,
  "goal_linkage_score": <1-5>,
  "overall_score": <1-5>,
  "improvement_suggestion": "One sentence on how the advice could be more actionable for this user's timeline."
}}"""

    def score(
        self, 
        user_goal: str,
        timeline: str,
        agent_output: str,
        **ignored_kwargs: Any
    ) -> List[score_result.ScoreResult]:
        """
        Score the agent's advice for actionability.
        
        Args:
            user_goal: What the user is trying to achieve
            timeline: User's timeline (e.g., "4 weeks", "3 months")
            agent_output: The agent's advice to evaluate
            **ignored_kwargs: Additional kwargs for compatibility
            
        Returns:
            List of ScoreResult with actionability scores
        """
        prompt = self.prompt_template.format(
            user_goal=user_goal,
            timeline=timeline,
            agent_output=agent_output
        )
        
        try:
            response = self.llm_client.generate_string(input=prompt)
        except Exception as e:
            return [
                score_result.ScoreResult(
                    name=self.name,
                    value=0,
                    reason=f"LLM call failed: {str(e)}"
                )
            ]
        
        try:
            clean_response = response.strip()
            if clean_response.startswith("```"):
                lines = clean_response.split("\n")
                clean_response = "\n".join(lines[1:-1])
            
            response_dict = json.loads(clean_response)
            
            # Extract scores (clamp to 1-5)
            timeline_score = max(1, min(5, int(response_dict.get("timeline_calibration_score", 3))))
            specificity_score = max(1, min(5, int(response_dict.get("specificity_score", 3))))
            accountability_score = max(1, min(5, int(response_dict.get("accountability_score", 3))))
            goal_linkage_score = max(1, min(5, int(response_dict.get("goal_linkage_score", 3))))
            overall_score = max(1, min(5, int(response_dict.get("overall_score", 3))))
            
            reasoning = response_dict.get("reasoning", "No reasoning provided")
            improvement = response_dict.get("improvement_suggestion", "")
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            return [
                score_result.ScoreResult(
                    name=self.name,
                    value=0.5,
                    reason=f"Could not parse LLM response: {str(e)}"
                )
            ]
        
        # Normalize overall score to 0-1 range
        normalized_score = (overall_score - 1) / 4.0
        
        return [
            score_result.ScoreResult(
                name=self.name,
                value=normalized_score,
                reason=reasoning
            ),
            score_result.ScoreResult(
                name=f"{self.name} - Overall Raw",
                value=overall_score,
                reason=f"Overall actionability: {overall_score}/5"
            ),
            score_result.ScoreResult(
                name=f"{self.name} - Timeline Calibration",
                value=timeline_score,
                reason=f"Timeline match: {timeline_score}/5"
            ),
            score_result.ScoreResult(
                name=f"{self.name} - Specificity",
                value=specificity_score,
                reason=f"Specificity: {specificity_score}/5"
            ),
            score_result.ScoreResult(
                name=f"{self.name} - Accountability",
                value=accountability_score,
                reason=f"Accountability framing: {accountability_score}/5"
            ),
            score_result.ScoreResult(
                name=f"{self.name} - Goal Linkage",
                value=goal_linkage_score,
                reason=f"Goal linkage: {goal_linkage_score}/5 - {improvement}"
            ),
        ]

    async def ascore(
        self,
        user_goal: str,
        timeline: str,
        agent_output: str,
        **ignored_kwargs: Any
    ) -> List[score_result.ScoreResult]:
        """Async version of score method."""
        return self.score(
            user_goal=user_goal,
            timeline=timeline,
            agent_output=agent_output,
            **ignored_kwargs
        )


def evaluate_actionability(
    user_goal: str,
    timeline: str,
    agent_output: str,
    model_name: str = "gemini/gemini-2.0-flash"
) -> dict:
    """
    Quick evaluation helper function.
    
    Returns dict with all dimension scores and reasoning.
    """
    metric = ActionabilityMetric(model_name=model_name)
    results = metric.score(
        user_goal=user_goal,
        timeline=timeline,
        agent_output=agent_output
    )
    
    if len(results) == 1:
        return {
            "overall_score": 0,
            "error": results[0].reason,
        }
    
    return {
        "normalized_score": results[0].value,
        "overall_score": results[1].value,
        "timeline_calibration": results[2].value,
        "specificity": results[3].value,
        "accountability": results[4].value,
        "goal_linkage": results[5].value,
        "reasoning": results[0].reason,
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__.rsplit("/", 1)[0]))
    
    # Load env
    from pathlib import Path
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())
    
    if os.getenv("GOOGLE_GENERATIVE_AI_API_KEY") and not os.getenv("GEMINI_API_KEY"):
        os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_GENERATIVE_AI_API_KEY"]
    
    print("Testing Actionability Metric...")
    print("=" * 60)
    
    # Test Case 1: Aggressive timeline, vague advice (should score low)
    print("\n[Test 1] Aggressive Timeline + Vague Advice")
    result1 = evaluate_actionability(
        user_goal="Lose 15 lbs",
        timeline="4 weeks",
        agent_output="This meal looks okay. Try to eat healthier and watch your portions."
    )
    print(f"  Overall: {result1['overall_score']}/5 (expected: 1-2)")
    print(f"  Timeline Calibration: {result1['timeline_calibration']}/5")
    print(f"  Specificity: {result1['specificity']}/5")
    
    # Test Case 2: Matched timeline with specific advice (should score high)
    print("\n[Test 2] Moderate Timeline + Specific Advice")
    result2 = evaluate_actionability(
        user_goal="Lose 10 lbs for summer",
        timeline="8 weeks",
        agent_output="""
        This grilled chicken with rice meal is 650 calories - good for your 1600/day target.
        
        🎯 For your 8-week goal (1.25 lbs/week needed):
        - SWAP: Replace white rice (50g carbs) → cauliflower rice (6g carbs). Saves 180 cal.
        - ADD: Double the broccoli portion for fiber + satiety. Only 30 cal more.
        - TRACK: Log this as "Protein + Veg Plate" - aim for 5x this week.
        
        This puts you at 500 cal deficit today. On track for 10 lbs in 8 weeks! ✅
        """
    )
    print(f"  Overall: {result2['overall_score']}/5 (expected: 4-5)")
    print(f"  Timeline Calibration: {result2['timeline_calibration']}/5")
    print(f"  Specificity: {result2['specificity']}/5")
    
    # Test Case 3: Gradual timeline but overly aggressive advice (mismatch)
    print("\n[Test 3] Gradual Timeline + Overly Aggressive Advice")
    result3 = evaluate_actionability(
        user_goal="Improve overall health",
        timeline="6 months",
        agent_output="""
        ⚠️ URGENT: You MUST eliminate ALL carbs immediately!
        This meal is TERRIBLE. Only eat 1000 calories per day.
        No exceptions. No cheat days. Start fasting 20 hours daily.
        """
    )
    print(f"  Overall: {result3['overall_score']}/5 (expected: 1-2, timeline mismatch)")
    print(f"  Timeline Calibration: {result3['timeline_calibration']}/5")
    
    print("\n" + "=" * 60)
    print("Testing complete!")
