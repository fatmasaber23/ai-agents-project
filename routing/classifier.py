"""
Deterministic Routing Agent - Classifier
--------------------------------------------------
This is the ONLY place this agent calls the LLM.

Its responsibility is to classify two projects into one
predefined review category.

All evaluation happens later inside routing/workflows.py
using deterministic Python logic only.
"""

import json

from utils.mistral_client import ask_mistral


VALID_CATEGORIES = {
    "FINANCIAL_REVIEW",
    "RISK_REVIEW",
    "RESOURCE_REVIEW",
    "EXECUTIVE_REVIEW",
}


SYSTEM_PROMPT = """
You are a routing classifier for a construction company's project selection system.

You will receive ONLY the pre-calculated percentage differences between two
projects (profit, budget, risk, team_availability, equipment_availability).
Base your decision strictly on these numbers.

Your ONLY task is to choose ONE review category.

Valid categories:

FINANCIAL_REVIEW
Choose FINANCIAL_REVIEW when profit_diff_pct or budget_diff_pct is at least
15 percentage points larger than every other diff.

RISK_REVIEW
Choose RISK_REVIEW when risk_diff is greater than 0 and the percentage
differences in profit, budget, team availability, and equipment availability
are all below 15%.
If risk_diff equals 2 (High vs Low), always prioritize RISK_REVIEW unless
another single factor exceeds the 15% threshold by a large margin.

RESOURCE_REVIEW
Choose RESOURCE_REVIEW when team_diff_pct or equipment_diff_pct is at least
15 percentage points larger than every other diff.

EXECUTIVE_REVIEW
Choose EXECUTIVE_REVIEW only when:
- No factor exceeds the routing threshold, OR
- Two or more factors are similarly important.
Do NOT choose EXECUTIVE_REVIEW when exactly one factor is clearly dominant.

Rules:
- Return ONLY one category.
- No explanation.
- No punctuation.
- No extra text.
"""


def _compute_diffs(project_a: dict, project_b: dict) -> dict:
    """
    Pre-computes the actual numeric differences in plain Python so the model
    classifies on verified facts instead of estimating them itself.
    """
    risk_scores = {"low": 1, "medium": 2, "high": 3}

    def pct_diff(a, b):
        total = a + b
        if total == 0:
            return 0.0
        return round(abs(a - b) / total * 100, 1)

    return {
        "profit_diff_pct": pct_diff(project_a["profit"], project_b["profit"]),
        "budget_diff_pct": pct_diff(project_a["budget"], project_b["budget"]),
        "risk_diff": abs(
            risk_scores.get(project_a["risk"].lower(), 2)
            - risk_scores.get(project_b["risk"].lower(), 2)
        ),
        "team_diff_pct": pct_diff(project_a["team_availability"], project_b["team_availability"]),
        "equipment_diff_pct": pct_diff(project_a["equipment_availability"], project_b["equipment_availability"]),
    }


def classify_scenario(project_a: dict, project_b: dict) -> str:
    """
    Uses the LLM once to classify the comparison into a routing category.

    Only the pre-calculated diffs are sent to the model - NOT the raw
    project data. Sending raw numbers alongside the diffs was distracting
    the model into reasoning qualitatively ("these look kind of different")
    instead of strictly applying the 15%-threshold rule.
    """

    diffs = _compute_diffs(project_a, project_b)

    prompt = (
        "Classify this comparison using ONLY these pre-calculated "
        "percentage differences:\n\n"
        f"{json.dumps(diffs, indent=2)}"
    )

    category = ask_mistral(
        prompt=prompt,
        system=SYSTEM_PROMPT,
        temperature=0,
    )

    category = (
        category.strip()
        .upper()
        .replace(" ", "_")
        .strip(".!,;:")
    )

    if category not in VALID_CATEGORIES:
        return "EXECUTIVE_REVIEW"

    return category