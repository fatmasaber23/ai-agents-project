"""
Constrained ReAct Agent - Tools
--------------------------------------------------
Allow-listed tools the agent can call. Each is plain, deterministic
Python code - no LLM call happens inside any tool. The model only
decides WHICH tool to call and WHEN; the tool itself just returns facts.
"""


def check_delay_impact(project_a: dict, project_b: dict) -> dict:
    """Compare how many days each project would lose without the equipment."""
    return {
        "project_a_delay_days": project_a["delay_without_equipment_days"],
        "project_b_delay_days": project_b["delay_without_equipment_days"],
        "greater_delay_impact": (
            "Project A"
            if project_a["delay_without_equipment_days"] >= project_b["delay_without_equipment_days"]
            else "Project B"
        ),
    }


def check_penalty_clause(project_a: dict, project_b: dict) -> dict:
    """Compare contractual penalty exposure between the two projects."""
    penalty_a = project_a["penalty_amount"] if project_a["has_penalty_clause"] else 0
    penalty_b = project_b["penalty_amount"] if project_b["has_penalty_clause"] else 0

    if penalty_a > penalty_b:
        higher = "Project A"
    elif penalty_b > penalty_a:
        higher = "Project B"
    else:
        higher = "Equal"

    return {
        "project_a_has_penalty": project_a["has_penalty_clause"],
        "project_a_penalty_amount": penalty_a,
        "project_b_has_penalty": project_b["has_penalty_clause"],
        "project_b_penalty_amount": penalty_b,
        "higher_penalty_exposure": higher,
    }


def check_alternative_availability(project_a: dict, project_b: dict) -> dict:
    """Compare whether each project has a backup rental option."""
    a_has = project_a["rental_alternative_available"]
    b_has = project_b["rental_alternative_available"]

    if not a_has and b_has:
        without_alt = "Project A"
    elif not b_has and a_has:
        without_alt = "Project B"
    else:
        without_alt = "Both or Neither"

    return {
        "project_a_has_alternative": a_has,
        "project_a_rental_cost_per_day": project_a["rental_cost_per_day"],
        "project_b_has_alternative": b_has,
        "project_b_rental_cost_per_day": project_b["rental_cost_per_day"],
        "project_without_alternative": without_alt,
    }


# --------------------------------------------------------------------
# Registry the agent loop uses to actually execute a validated action.
# Validation already restricts tool_name to these three (see schema.py),
# this dict is what turns the name into a real function call.
# --------------------------------------------------------------------
TOOL_REGISTRY = {
    "check_delay_impact": check_delay_impact,
    "check_penalty_clause": check_penalty_clause,
    "check_alternative_availability": check_alternative_availability,
}