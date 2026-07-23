"""
Deterministic Routing Agent - Workflows
---------------------------------------

The Routing Agent selects ONE review category.
After routing, all logic here is deterministic Python code.

Each workflow evaluates the equipment-allocation request from one
perspective only, then recommends which project gets the equipment
and what the other project should do instead.

Categories:
- Delay Review
- Penalty Review
- Alternative Review
- Executive Review
"""

# ============================================================
# Constants
# ============================================================

EXECUTIVE_WEIGHTS = {
    "delay": 0.4,
    "penalty": 0.4,
    "need": 0.2
}


# ============================================================
# Helper Functions
# ============================================================

def delay_score(project: dict) -> float:
    """Higher delay without the equipment = more urgent need."""
    return project["delay_without_equipment_days"]


def penalty_score(project: dict) -> float:
    """Financial exposure if this project does NOT get the equipment."""
    return project["penalty_amount"] if project["has_penalty_clause"] else 0


def need_score(project: dict) -> int:
    """
    1 if the project has NO rental alternative (fully dependent on
    this equipment), 0 if it has a backup option.
    """
    return 0 if project["rental_alternative_available"] else 1


def other_project_action(loser: dict) -> str:
    """What the project that does NOT get the equipment should do."""
    if loser["rental_alternative_available"]:
        return f"Rent alternative equipment at {loser['rental_cost_per_day']} EGP/day"
    return "Wait for the equipment to free up"


def _build_result(category, winner, project_a, project_b, scores, reasons):
    loser_project = project_b if winner == "Project A" else project_a
    loser_name = "Project B" if winner == "Project A" else "Project A"

    return {
        "category": category,
        "recommended": winner,
        "scores": scores,
        "reasons": reasons,
        "other_project": loser_name,
        "other_project_action": other_project_action(loser_project),
    }


# ============================================================
# Delay Review
# ============================================================

def delay_review(project_a: dict, project_b: dict) -> dict:
    """
    Evaluate based on which project loses more time without the equipment.
    """

    score_a = delay_score(project_a)
    score_b = delay_score(project_b)

    winner = "Project A" if score_a >= score_b else "Project B"

    reasons = [f"Greater delay impact without equipment: {winner}"]

    return _build_result(
        "Delay Review", winner, project_a, project_b,
        {"Project A": score_a, "Project B": score_b},
        reasons
    )


# ============================================================
# Penalty Review
# ============================================================

def penalty_review(project_a: dict, project_b: dict) -> dict:
    """
    Evaluate based on contractual penalty exposure.
    """

    score_a = penalty_score(project_a)
    score_b = penalty_score(project_b)

    if score_a > score_b:
        winner = "Project A"
    elif score_b > score_a:
        winner = "Project B"
    else:
        # Equal penalty exposure -> fall back to delay impact
        winner = delay_review(project_a, project_b)["recommended"]

    reasons = [f"Higher penalty exposure: {winner}"]

    return _build_result(
        "Penalty Review", winner, project_a, project_b,
        {"Project A": score_a, "Project B": score_b},
        reasons
    )


# ============================================================
# Alternative Review
# ============================================================

def alternative_review(project_a: dict, project_b: dict) -> dict:
    """
    Evaluate based on which project has NO backup option.
    The project fully dependent on this equipment gets priority.
    """

    score_a = need_score(project_a)
    score_b = need_score(project_b)

    if score_a > score_b:
        winner = "Project A"
    elif score_b > score_a:
        winner = "Project B"
    else:
        # Both (or neither) have alternatives -> fall back to delay impact
        winner = delay_review(project_a, project_b)["recommended"]

    if score_a != score_b:
        reasons = [f"No rental alternative available, fully dependent on this equipment: {winner}"]
    else:
        reasons = [f"Equal alternative availability, decided by delay impact: {winner}"]

    return _build_result(
        "Alternative Review", winner, project_a, project_b,
        {"Project A": score_a, "Project B": score_b},
        reasons
    )


# ============================================================
# Executive Review
# ============================================================

def executive_review(project_a: dict, project_b: dict) -> dict:
    """
    Comprehensive review combining delay, penalty and dependency factors.
    """

    def normalize(a, b):
        total = a + b
        if total == 0:
            return 0.5, 0.5
        return a / total, b / total

    delay_a, delay_b = normalize(delay_score(project_a), delay_score(project_b))
    penalty_a, penalty_b = normalize(penalty_score(project_a), penalty_score(project_b))
    need_a, need_b = normalize(need_score(project_a), need_score(project_b))

    final_a = (
        delay_a * EXECUTIVE_WEIGHTS["delay"]
        + penalty_a * EXECUTIVE_WEIGHTS["penalty"]
        + need_a * EXECUTIVE_WEIGHTS["need"]
    )

    final_b = (
        delay_b * EXECUTIVE_WEIGHTS["delay"]
        + penalty_b * EXECUTIVE_WEIGHTS["penalty"]
        + need_b * EXECUTIVE_WEIGHTS["need"]
    )

    winner = "Project A" if final_a >= final_b else "Project B"

    reasons = []

    if delay_a != delay_b:
        reasons.append(f"Greater delay impact: {'Project A' if delay_a > delay_b else 'Project B'}")

    if penalty_a != penalty_b:
        reasons.append(f"Higher penalty exposure: {'Project A' if penalty_a > penalty_b else 'Project B'}")

    if need_a != need_b:
        reasons.append(f"No backup alternative: {'Project A' if need_a > need_b else 'Project B'}")

    return _build_result(
        "Executive Review", winner, project_a, project_b,
        {"Project A": round(final_a, 3), "Project B": round(final_b, 3)},
        reasons
    )