"""
Deterministic Routing Agent - Workflows
---------------------------------------

The Routing Agent selects ONE review category.
After routing, all logic here is deterministic Python code.

Each workflow evaluates projects from one perspective only.

Categories:
- Financial Review
- Risk Review
- Resource Review
- Executive Review
"""

# ============================================================
# Constants
# ============================================================

RISK_SCORES = {
    "low": 3,
    "medium": 2,
    "high": 1
}

RESOURCE_WEIGHTS = {
    "team": 0.7,
    "equipment": 0.3
}

EXECUTIVE_WEIGHTS = {
    "profit": 0.25,
    "risk": 0.25,
    "duration": 0.15,
    "resources": 0.35
}


# ============================================================
# Helper Functions
# ============================================================

def compare_budget(project_a: dict, project_b: dict) -> str:
    """Return the project with the lower budget."""
    return "Project A" if project_a["budget"] < project_b["budget"] else "Project B"


def compare_duration(project_a: dict, project_b: dict) -> str:
    """Return the project with the shorter duration."""
    return "Project A" if project_a["duration"] < project_b["duration"] else "Project B"


def risk_score(project: dict) -> int:
    """Convert risk level into a comparable numeric score."""
    return RISK_SCORES.get(project["risk"].lower(), 1)


def financial_score(project: dict) -> float:
    """
    ROI Proxy.
    Higher profit with lower budget receives a higher score.
    """
    if project["budget"] == 0:
        return 0

    return project["profit"] / project["budget"]


def team_score(project: dict) -> float:
    return project["team_availability"]


def equipment_score(project: dict) -> float:
    return project["equipment_availability"]


def resource_score(project: dict) -> float:
    """
    Team availability is considered more important
    than equipment availability.
    """

    return (
        project["team_availability"] * RESOURCE_WEIGHTS["team"]
        +
        project["equipment_availability"] * RESOURCE_WEIGHTS["equipment"]
    )


# ============================================================
# Financial Review
# ============================================================

def financial_review(project_a: dict, project_b: dict) -> dict:
    """
    Evaluate projects based on financial efficiency.
    """

    score_a = financial_score(project_a)
    score_b = financial_score(project_b)

    if score_a > score_b:
        winner = "Project A"
    elif score_b > score_a:
        winner = "Project B"
    else:
        winner = compare_budget(project_a, project_b)

    reasons = [
        f"Higher ROI (profit/budget): {winner}",
        f"Lower Budget: {compare_budget(project_a, project_b)}"
    ]

    return {
        "category": "Financial Review",
        "recommended": winner,
        "scores": {
            "Project A": round(score_a, 3),
            "Project B": round(score_b, 3)
        },
        "reasons": reasons
    }


# ============================================================
# Risk Review
# ============================================================

def risk_review(project_a: dict, project_b: dict) -> dict:
    """
    Evaluate projects based on risk level.
    """

    score_a = risk_score(project_a)
    score_b = risk_score(project_b)

    if score_a > score_b:
        winner = "Project A"
    elif score_b > score_a:
        winner = "Project B"
    else:
        winner = compare_duration(project_a, project_b)

    reasons = [
        f"Safer Project: {winner}"
    ]

    if score_a == score_b:
        reasons.append(
            f"Equal risk. Shorter duration selected: {winner}"
        )

    return {
        "category": "Risk Review",
        "recommended": winner,
        "scores": {
            "Project A": score_a,
            "Project B": score_b
        },
        "reasons": reasons
    }


# ============================================================
# Resource Review
# ============================================================

def resource_review(project_a: dict, project_b: dict) -> dict:
    """
    Evaluate projects according to available resources.
    """

    score_a = resource_score(project_a)
    score_b = resource_score(project_b)

    if score_a > score_b:
        winner = "Project A"
    elif score_b > score_a:
        winner = "Project B"
    else:
        winner = compare_budget(project_a, project_b)

    reasons = [
        f"Better Team Availability: {'Project A' if team_score(project_a) > team_score(project_b) else 'Project B'}",
        f"Better Equipment Availability: {'Project A' if equipment_score(project_a) > equipment_score(project_b) else 'Project B'}"
    ]

    return {
        "category": "Resource Review",
        "recommended": winner,
        "scores": {
            "Project A": round(score_a, 2),
            "Project B": round(score_b, 2)
        },
        "reasons": reasons
    }


# ============================================================
# Executive Review
# ============================================================

def executive_review(project_a: dict, project_b: dict) -> dict:
    """
    Comprehensive review combining all project factors.
    """

    def normalize(a, b, higher_is_better=True):

        total = a + b

        if total == 0:
            return 0.5, 0.5

        a_norm = a / total
        b_norm = b / total

        if not higher_is_better:
            a_norm = 1 - a_norm
            b_norm = 1 - b_norm

        return a_norm, b_norm

    profit_a, profit_b = normalize(
        project_a["profit"],
        project_b["profit"]
    )

    risk_a, risk_b = normalize(
        risk_score(project_a),
        risk_score(project_b)
    )

    duration_a, duration_b = normalize(
        project_a["duration"],
        project_b["duration"],
        higher_is_better=False
    )

    resource_a, resource_b = normalize(
        resource_score(project_a),
        resource_score(project_b)
    )

    final_a = (
        profit_a * EXECUTIVE_WEIGHTS["profit"]
        + risk_a * EXECUTIVE_WEIGHTS["risk"]
        + duration_a * EXECUTIVE_WEIGHTS["duration"]
        + resource_a * EXECUTIVE_WEIGHTS["resources"]
    )

    final_b = (
        profit_b * EXECUTIVE_WEIGHTS["profit"]
        + risk_b * EXECUTIVE_WEIGHTS["risk"]
        + duration_b * EXECUTIVE_WEIGHTS["duration"]
        + resource_b * EXECUTIVE_WEIGHTS["resources"]
    )

    winner = "Project A" if final_a >= final_b else "Project B"

    reasons = []

    if profit_a != profit_b:
        reasons.append(
            f"Higher Profit: {'Project A' if profit_a > profit_b else 'Project B'}"
        )

    if risk_a != risk_b:
        reasons.append(
            f"Lower Risk: {'Project A' if risk_a > risk_b else 'Project B'}"
        )

    if duration_a != duration_b:
        reasons.append(
            f"Shorter Duration: {'Project A' if duration_a > duration_b else 'Project B'}"
        )

    if resource_a != resource_b:
        reasons.append(
            f"Better Resources: {'Project A' if resource_a > resource_b else 'Project B'}"
        )

    return {
        "category": "Executive Review",
        "recommended": winner,
        "scores": {
            "Project A": round(final_a, 3),
            "Project B": round(final_b, 3)
        },
        "reasons": reasons
    }