"""
Deterministic Routing Agent - Classifier
--------------------------------------------------
This is the ONLY place this agent calls the LLM.

Its responsibility is to classify an equipment-allocation request
(two projects competing for the same equipment) into one predefined
review category.

All evaluation happens later inside routing/workflows.py
using deterministic Python logic only.
"""

import json

from utils.mistral_client import ask_mistral


VALID_CATEGORIES = {
    "DELAY_REVIEW",
    "PENALTY_REVIEW",
    "ALTERNATIVE_REVIEW",
    "EXECUTIVE_REVIEW",
}


SYSTEM_PROMPT = """
You are a routing classifier for a construction company's equipment
allocation system. Two projects need the same piece of equipment
(e.g. a crane) at the same time, and only one project can have it.

You will receive ONLY pre-calculated differences between the two
projects (delay impact, penalty exposure, alternative availability).
Base your decision strictly on these numbers.

Your ONLY task is to choose ONE review category.

Valid categories:

DELAY_REVIEW
Choose DELAY_REVIEW when delay_diff_pct is at least 15 percentage
points larger than penalty_diff_pct, AND alternative_mismatch is false.

PENALTY_REVIEW
Choose PENALTY_REVIEW when penalty_diff_pct is at least 15 percentage
points larger than delay_diff_pct, OR when penalty_mismatch is true,
AND alternative_mismatch is false.

ALTERNATIVE_REVIEW
Choose ALTERNATIVE_REVIEW when alternative_mismatch is true (only one
project has a rental alternative available). A project with NO backup
option is at real risk of a full stop, so this factor takes priority
over delay and penalty unless one of them is overwhelmingly larger
(more than 40 percentage points bigger).

EXECUTIVE_REVIEW
Choose EXECUTIVE_REVIEW only when:
- No factor is clearly dominant, OR
- Two or more factors matter together and are close in size.
Do NOT choose EXECUTIVE_REVIEW when exactly one factor is clearly dominant.

Rules:
- Return ONLY one category.
- No explanation.
- No punctuation.
- No extra text.
"""


def _compute_diffs(project_a: dict, project_b: dict) -> dict:
    """
    Pre-computes the actual numeric differences in plain Python so the
    model classifies on verified facts instead of estimating them itself.
    """

    def pct_diff(a, b):
        total = a + b
        if total == 0:
            return 0.0
        return round(abs(a - b) / total * 100, 1)

    return {
        "delay_diff_pct": pct_diff(
            project_a["delay_without_equipment_days"],
            project_b["delay_without_equipment_days"]
        ),
        "penalty_diff_pct": pct_diff(
            project_a["penalty_amount"],
            project_b["penalty_amount"]
        ),
        "penalty_mismatch": project_a["has_penalty_clause"] != project_b["has_penalty_clause"],
        "alternative_mismatch": (
            project_a["rental_alternative_available"] != project_b["rental_alternative_available"]
        ),
    }


def classify_scenario(project_a: dict, project_b: dict) -> str:
    """
    Uses the LLM once to classify the request into a routing category.

    Only the pre-calculated diffs are sent to the model - NOT the raw
    project data - so it applies the threshold rules strictly instead
    of reasoning qualitatively about the raw numbers.
    """

    diffs = _compute_diffs(project_a, project_b)

    prompt = (
        "Classify this equipment allocation request using ONLY these "
        "pre-calculated differences:\n\n"
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