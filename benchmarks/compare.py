import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def compare() -> None:
    baseline_file = Path("benchmarks/baseline_results.json")
    agent_file = Path("benchmarks/agent_results.json")
    
    if not baseline_file.exists() or not agent_file.exists():
        logger.error("Missing result files. Run run_baseline.py and run_agent.py first.")
        return

    baseline_data = json.loads(baseline_file.read_text())
    agent_data = json.loads(agent_file.read_text())

    # Map by task id
    baseline_map = {item["task_id"]: item for item in baseline_data}
    agent_map = {item["task_id"]: item for item in agent_data}

    print("========================================")
    print("      BENCHMARK COMPARISON REPORT       ")
    print("========================================")
    print(f"{'Task ID':<20} | {'Baseline':<10} | {'Agent':<10} | {'Delta':<10}")
    print("-" * 55)

    total_baseline_score = 0
    total_agent_score = 0
    tasks_compared = 0

    for task_id, baseline in baseline_map.items():
        if task_id in agent_map:
            tasks_compared += 1
            agent = agent_map[task_id]
            b_score = baseline.get("score", 0)
            a_score = agent.get("score", 0)
            
            total_baseline_score += b_score
            total_agent_score += a_score
            
            delta = a_score - b_score
            delta_str = f"+{delta}" if delta > 0 else str(delta)
            
            print(f"{task_id:<20} | {b_score:<10} | {a_score:<10} | {delta_str:<10}")

    print("-" * 55)
    print(f"Tasks Compared: {tasks_compared}")
    
    avg_baseline = total_baseline_score / max(1, tasks_compared)
    avg_agent = total_agent_score / max(1, tasks_compared)
    
    print(f"Avg Baseline Score: {avg_baseline:.2f}")
    print(f"Avg Agent Score:    {avg_agent:.2f}")
    
    delta = avg_agent - avg_baseline
    delta_str = f"+{delta:.2f}" if delta > 0 else f"{delta:.2f}"
    print(f"Overall Delta:      {delta_str}")
    print("========================================")

if __name__ == "__main__":
    compare()
