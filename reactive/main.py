"""
Reactive Agent

This agent does not use AI or any language model.
It only uses simple if/else rules.

The agent reads two projects from data/projects.json,
and decides which project should get the shared equipment.

Rules:
1. If only one project cannot rent another machine, choose it.
2. If only one project has a delay penalty, choose it.
3. If one project will be delayed much more than the other
   (more than 4 days), choose that project.
4. If none of the rules work, choose the project with the
   higher penalty amount.
   If both are equal, choose Project A.

Note:
The agent checks one rule at a time.
As soon as one rule is true, it stops.
It does not compare all factors together.
"""

from utils.load_data import load_projects
DELAY_GAP_THRESHOLD = 4
def decision(project_a: dict, project_b: dict) -> dict:
    a_alternative = project_a["rental_alternative_available"]
    b_alternative = project_b["rental_alternative_available"]

# Rule 1
    if a_alternative == False and b_alternative == True:
        return {
            "recommended": "Project A",
            "rule_fired": "no_rental_alternative",
            "reason": "Project A cannot rent another equipment.",
        }
    if b_alternative == False and a_alternative == True:
        return {
            "recommended": "Project B",
            "rule_fired": "no_rental_alternative",
            "reason": "Project B cannot rent another equipment.",
        }

# Rule 2
    a_penalty = project_a["has_penalty_clause"]
    b_penalty = project_b["has_penalty_clause"]

    if a_penalty == True and b_penalty == False:
        return {
            "recommended": "Project A",
            "rule_fired": "penalty_clause",
            "reason": "Project A has a delay penalty.",
        }
    if b_penalty == True and a_penalty == False:
        return {
            "recommended": "Project B",
            "rule_fired": "penalty_clause",
            "reason": "Project B has a delay penalty.",
        }

# Rule 3
    delay_gap = abs(project_a["delay_without_equipment_days"] - project_b["delay_without_equipment_days"])
    if delay_gap > DELAY_GAP_THRESHOLD:
        winner = "Project A" if project_a["delay_without_equipment_days"] > project_b["delay_without_equipment_days"] else "Project B"
        return {
            "recommended": winner,
            "rule_fired": "delay_gap",
            "reason": f"This project will lose more time ({delay_gap} days difference).",
        }

# Rule 4
    winner = "Project A" if project_a["penalty_amount"] > project_b["penalty_amount"] else "Project B"
    return {
        "recommended": winner,
        "rule_fired": "default_penalty_amount",
        "reason": "Used the penalty amount as the final rule.",
    }
def run_reactive_agent():
    projects = load_projects()
    result = decision(projects["projectA"], projects["projectB"])
    print("REACTIVE AGENT RESULT")
    print(f"Rule fired  : {result['rule_fired']}")
    print(f"Equipment to : {result['recommended']}")
    print(f"Reason : {result['reason']}")
    return result

if __name__ == "__main__":
    run_reactive_agent()
