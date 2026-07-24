"""
Constrained ReAct Agent - Main Entry Point
--------------------------------------------------

Pipeline:

1. Load the equipment allocation request (two competing projects).
2. Run the Constrained ReAct loop (Thought -> Action -> Observation...).
3. Display the final decision or escalation, plus the full trace.
"""

from utils.load_data import load_projects
from constrained_react.agent import run_constrained_react


def run_constrained_react_agent():

    projects = load_projects()

    project_a = projects["projectA"]
    project_b = projects["projectB"]

    result = run_constrained_react(project_a, project_b)

    print("\n" + "=" * 60)
    print("     CONSTRAINED REACT AGENT RESULT")
    print("=" * 60)

    print(f"\nStatus       : {result['status']}")
    print(f"Steps Used   : {result['steps_used']}")

    if result["status"] == "final_answer":
        print(f"Recommended  : {result['recommended_project']}")
        print("\nReasons:")
        for reason in result["reasons"]:
            print(f" • {reason}")
    else:
        print(f"Escalation Reason: {result['reason']}")

    print("\n--- Full Trace ---")
    for entry in result["trace"]:
        print(f"\nStep {entry['step']}: {entry['thought']}")
        if "action" in entry:
            print(f"  → Called: {entry['action']}")
            print(f"  → Observation: {entry['observation']}")
        if "final_answer" in entry:
            print(f"  → Final Answer: {entry['final_answer']}")
        if "escalate" in entry:
            print(f"  → Escalated: {entry['escalate']}")

    print("\n" + "=" * 60)

    return result


if __name__ == "__main__":
    run_constrained_react_agent()