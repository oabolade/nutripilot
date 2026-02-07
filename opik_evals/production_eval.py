"""
NutriPilot AI - Production Evaluation Pipeline

This script runs batch evaluation on real Opik traces using both
Goal Adherence and Actionability LLM-judge metrics.

Usage:
    # Create a dataset from recent traces and run evaluation
    python production_eval.py --mode=batch --limit=20
    
    # Evaluate existing dataset
    python production_eval.py --mode=eval --dataset=goal_evaluator_test_cases
    
    # View trace statistics
    python production_eval.py --mode=stats
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# Load environment variables
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())

# Map API key for LiteLLM
if os.getenv("GOOGLE_GENERATIVE_AI_API_KEY") and not os.getenv("GEMINI_API_KEY"):
    os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_GENERATIVE_AI_API_KEY"]

import opik
from opik import Opik
from opik.evaluation import evaluate

from goal_adherence_metric import GoalAdherenceMetric
from actionability_metric import ActionabilityMetric


# Default project name
PROJECT_NAME = "nutripilot"


def get_client() -> Opik:
    """Get configured Opik client."""
    opik.configure()
    return Opik()


def create_dataset_from_traces(
    client: Opik,
    dataset_name: str,
    limit: int = 50,
    days_back: int = 7,
) -> opik.Dataset:
    """
    Create/update a dataset from recent Opik traces.
    
    Extracts relevant data from traces for evaluation:
    - user_profile: Goals, conditions, timeline
    - detected_food: Foods identified in the meal
    - agent_output: Feedback and recommendations from agents
    - user_goal: Primary goal for actionability
    - timeline: User's timeline in weeks
    
    Args:
        client: Opik client
        dataset_name: Name for the dataset
        limit: Maximum traces to include
        days_back: Look back N days for traces
        
    Returns:
        Created/updated dataset
    """
    print(f"\n📊 Creating dataset '{dataset_name}' from recent traces...")
    
    # Get or create the dataset
    dataset = client.get_or_create_dataset(
        name=dataset_name,
        description=f"Production traces for LLM judge evaluation (created {datetime.now().isoformat()})"
    )
    
    # Get recent traces from the project
    # NOTE: Opik's trace API may vary - this is a conceptual implementation
    # You may need to adjust based on Opik's actual API
    try:
        # Try to get traces via the Opik API
        traces = client.get_traces(
            project_name=PROJECT_NAME,
            limit=limit,
            # start_time=datetime.now() - timedelta(days=days_back),
        )
        print(f"  Found {len(traces)} traces in '{PROJECT_NAME}' project")
        
    except AttributeError:
        # If get_traces isn't available, create sample data
        print("  ⚠️ Trace retrieval not available - using sample data")
        traces = create_sample_traces(limit)
    
    # Transform traces into dataset items
    items_added = 0
    for trace in traces:
        try:
            item = transform_trace_to_dataset_item(trace)
            if item:
                dataset.insert([item])
                items_added += 1
        except Exception as e:
            print(f"  ⚠️ Failed to transform trace: {e}")
    
    print(f"  ✅ Added {items_added} items to dataset")
    return dataset


def transform_trace_to_dataset_item(trace) -> Optional[dict]:
    """
    Transform an Opik trace into a dataset item for evaluation.
    
    Maps trace data to the inputs expected by our metrics:
    - Goal Adherence: user_profile, detected_food, agent_output
    - Actionability: user_goal, timeline, agent_output
    """
    # Handle dict format (sample data) or Trace object
    if isinstance(trace, dict):
        return trace
    
    # Extract from Trace object
    # This is a conceptual implementation - adjust based on actual trace structure
    try:
        # Get input/output from trace
        trace_input = trace.input or {}
        trace_output = trace.output or {}
        
        # Extract user profile data
        user_profile = trace_input.get("user_profile", {})
        goals = user_profile.get("goals", ["general_wellness"])
        conditions = user_profile.get("conditions", [])
        timeline_weeks = user_profile.get("timeline_weeks", 12)
        
        # Extract detected foods
        detected_foods = trace_output.get("detected_foods", [])
        food_names = [f.get("name", f) if isinstance(f, dict) else str(f) for f in detected_foods]
        
        # Extract agent output (feedback + recommendations)
        goal_evaluation = trace_output.get("goal_evaluation", {})
        feedback = goal_evaluation.get("feedback", [])
        recommendations = goal_evaluation.get("recommendations", [])
        summary = trace_output.get("summary", "")
        
        # Build the dataset item
        # Both metrics use agent_output, plus their specific fields
        agent_output_text = f"{summary}\n\nFeedback: {' '.join(feedback)}\n\nRecommendations: {' '.join(recommendations)}"
        
        return {
            # Shared by both metrics
            "agent_output": agent_output_text,
            
            # For Goal Adherence metric: user_profile, detected_food, agent_output
            "user_profile": f"Goals: {', '.join(goals)}. Conditions: {', '.join(conditions) if conditions else 'None'}. Timeline: {timeline_weeks} weeks.",
            "detected_food": ", ".join(food_names) if food_names else "Unknown meal",
            
            # For Actionability metric: user_goal, timeline, agent_output
            "user_goal": goals[0] if goals else "general_wellness",
            "timeline": f"{timeline_weeks} weeks",
            
            # Metadata
            "trace_id": getattr(trace, "id", "unknown"),
            "timestamp": str(getattr(trace, "created_at", datetime.now())),
        }
        
    except Exception as e:
        print(f"  Transform error: {e}")
        return None


def create_sample_traces(limit: int = 10) -> list:
    """
    Create sample traces for testing when real traces aren't available.
    
    These simulate various user scenarios and agent responses.
    """
    samples = [
        {
            "user_profile": "Goals: weight_loss. Conditions: type_2_diabetes. Timeline: 8 weeks.",
            "detected_food": "Grilled chicken breast, white rice, steamed broccoli",
            "agent_output": """
                This meal scores 72/100. Good protein from chicken, but the white rice 
                may spike blood sugar. Consider swapping for brown rice or cauliflower rice.
                Your 8-week weight loss goal needs a 500 cal/day deficit - this meal fits well.
            """,
            "user_goal": "weight_loss",
            "timeline": "8 weeks",
        },
        {
            "user_profile": "Goals: muscle_building. Conditions: None. Timeline: 16 weeks.",
            "detected_food": "Triple cheeseburger with bacon, large fries, milkshake",
            "agent_output": """
                Great protein content at 58g! This high-calorie meal supports your bulking phase.
                Consider adding vegetables for fiber. The sodium is quite high at 2100mg.
            """,
            "user_goal": "muscle_building",
            "timeline": "16 weeks",
        },
        {
            "user_profile": "Goals: glycemic_control. Conditions: type_2_diabetes, hypertension. Timeline: 4 weeks.",
            "detected_food": "Pizza, garlic bread, soda",
            "agent_output": """
                Looks tasty! Remember to log your meal.
                Pizza has good cheese for calcium.
            """,
            "user_goal": "glycemic_control",
            "timeline": "4 weeks",
            # ADVERSARIAL: Bad advice that should score low
        },
        {
            "user_profile": "Goals: heart_health. Conditions: hypertension. Timeline: 12 weeks.",
            "detected_food": "Grilled salmon, quinoa, roasted vegetables, olive oil",
            "agent_output": """
                Excellent heart-healthy meal! Score: 92/100
                
                ✅ Omega-3s from salmon support heart health
                ✅ Low sodium (estimated 380mg)
                ✅ High fiber from vegetables and quinoa
                
                This aligns perfectly with your 12-week heart health goals.
                Keep choosing meals like this 5x per week for optimal results.
            """,
            "user_goal": "heart_health",
            "timeline": "12 weeks",
        },
        {
            "user_profile": "Goals: weight_loss. Conditions: None. Timeline: 4 weeks.",
            "detected_food": "Caesar salad with croutons, fried chicken strips",
            "agent_output": """
                Healthy choice with the salad!
            """,
            "user_goal": "weight_loss",
            "timeline": "4 weeks",
            # GENERIC: Too vague for aggressive 4-week timeline
        },
    ]
    
    return samples[:limit]


def run_batch_evaluation(
    client: Opik,
    dataset_name: str,
    experiment_name: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """
    Run batch evaluation with both metrics on a dataset.
    
    Args:
        client: Opik client
        dataset_name: Name of dataset to evaluate
        experiment_name: Custom experiment name (optional)
        limit: Max traces to include if creating new dataset
        
    Returns:
        Evaluation results summary
    """
    print("\n🚀 Starting Batch Evaluation")
    print("=" * 60)
    
    # Create/get dataset
    dataset = create_dataset_from_traces(client, dataset_name, limit=limit)
    
    # Initialize both metrics
    goal_metric = GoalAdherenceMetric()
    action_metric = ActionabilityMetric()
    
    # Define the task function
    # This passes through the dataset item as the "agent output" to evaluate
    def evaluation_task(item: dict) -> dict:
        """Pass through dataset item for scoring."""
        return {
            # Shared: Both metrics use agent_output
            "agent_output": item.get("agent_output", ""),
            
            # Goal Adherence inputs: user_profile, detected_food, agent_output
            "user_profile": item.get("user_profile", ""),
            "detected_food": item.get("detected_food", ""),
            
            # Actionability inputs: user_goal, timeline, agent_output
            "user_goal": item.get("user_goal", ""),
            "timeline": item.get("timeline", "12 weeks"),
            
            # Original output (for Opik display)
            "output": item.get("agent_output", ""),
        }
    
    # Generate experiment name
    if not experiment_name:
        experiment_name = f"production_eval_{datetime.now().strftime('%Y%m%d_%H%M')}"
    
    print(f"\n📈 Running experiment: {experiment_name}")
    print(f"  Dataset: {dataset_name}")
    print(f"  Metrics: Goal Adherence, Actionability")
    
    # Run evaluation
    results = evaluate(
        dataset=dataset,
        task=evaluation_task,
        scoring_metrics=[goal_metric, action_metric],
        experiment_name=experiment_name,
    )
    
    print("\n" + "=" * 60)
    print("✅ EVALUATION COMPLETE")
    print("=" * 60)
    print(f"\nView results in Opik: https://www.comet.com/opik")
    print(f"Project: {PROJECT_NAME}")
    print(f"Experiment: {experiment_name}")
    
    return results


def show_trace_stats(client: Opik):
    """Display statistics about traces in the project."""
    print("\n📊 Trace Statistics")
    print("=" * 60)
    
    try:
        traces = client.get_traces(project_name=PROJECT_NAME, limit=100)
        print(f"Total traces (last 100): {len(traces)}")
        
        # Group by date
        by_date = {}
        for trace in traces:
            date = getattr(trace, "created_at", datetime.now()).date()
            by_date[date] = by_date.get(date, 0) + 1
        
        print("\nTraces by date:")
        for date in sorted(by_date.keys(), reverse=True)[:7]:
            print(f"  {date}: {by_date[date]} traces")
            
    except Exception as e:
        print(f"Could not retrieve trace stats: {e}")
        print("This may be due to Opik API limitations.")


def main():
    parser = argparse.ArgumentParser(description="Production Evaluation Pipeline")
    parser.add_argument(
        "--mode",
        choices=["batch", "eval", "stats", "sample"],
        default="sample",
        help="Evaluation mode"
    )
    parser.add_argument(
        "--dataset",
        default="production_eval_dataset",
        help="Dataset name"
    )
    parser.add_argument(
        "--experiment",
        default=None,
        help="Experiment name (auto-generated if not provided)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Max traces to evaluate"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("NutriPilot Production Evaluation Pipeline")
    print("=" * 60)
    
    client = get_client()
    
    if args.mode == "batch":
        run_batch_evaluation(
            client,
            dataset_name=args.dataset,
            experiment_name=args.experiment,
            limit=args.limit,
        )
    
    elif args.mode == "eval":
        # Evaluate existing dataset without creating new one
        print(f"\n📈 Evaluating existing dataset: {args.dataset}")
        dataset = client.get_or_create_dataset(name=args.dataset)
        
        goal_metric = GoalAdherenceMetric()
        action_metric = ActionabilityMetric()
        
        def evaluation_task(item: dict) -> dict:
            return {
                "user_profile": item.get("user_profile", ""),
                "detected_food": item.get("detected_food", ""),
                "agent_output": item.get("agent_output", ""),
                "user_goal": item.get("user_goal", ""),
                "timeline": item.get("timeline", "12 weeks"),
                "output": item.get("agent_output", ""),
            }
        
        exp_name = args.experiment or f"eval_{datetime.now().strftime('%Y%m%d_%H%M')}"
        
        results = evaluate(
            dataset=dataset,
            task=evaluation_task,
            scoring_metrics=[goal_metric, action_metric],
            experiment_name=exp_name,
        )
        
        print(f"\n✅ Evaluation complete! View in Opik dashboard.")
    
    elif args.mode == "stats":
        show_trace_stats(client)
    
    elif args.mode == "sample":
        # Run on sample data for testing
        print("\n🧪 Running evaluation on sample data...")
        
        dataset = client.get_or_create_dataset(
            name="sample_production_eval",
            description="Sample data for testing production evaluation"
        )
        
        # Add sample traces
        samples = create_sample_traces(5)
        for sample in samples:
            dataset.insert([sample])
        
        print(f"  Created dataset with {len(samples)} sample items")
        
        goal_metric = GoalAdherenceMetric()
        action_metric = ActionabilityMetric()
        
        def evaluation_task(item: dict) -> dict:
            return {
                "user_profile": item.get("user_profile", ""),
                "detected_food": item.get("detected_food", ""),
                "agent_output": item.get("agent_output", ""),
                "user_goal": item.get("user_goal", ""),
                "timeline": item.get("timeline", "12 weeks"),
                "output": item.get("agent_output", ""),
            }
        
        results = evaluate(
            dataset=dataset,
            task=evaluation_task,
            scoring_metrics=[goal_metric, action_metric],
            experiment_name=f"sample_eval_{datetime.now().strftime('%H%M')}",
        )
        
        print("\n✅ Sample evaluation complete! View in Opik dashboard.")
        print("URL: https://www.comet.com/opik")


if __name__ == "__main__":
    main()
