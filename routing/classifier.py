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

You will receive two projects as JSON.

Your ONLY task is to choose ONE review category.

Valid categories:

FINANCIAL_REVIEW
- Profit or budget is the main deciding factor.

RISK_REVIEW
- Risk difference is the main deciding factor.

RESOURCE_REVIEW
- Team or equipment availability is the main deciding factor.

EXECUTIVE_REVIEW
- Multiple factors are important and require a complete evaluation.

Rules:
- Return ONLY one category.
- No explanation.
- No punctuation.
- No extra text.
"""


def classify_scenario(project_a: dict, project_b: dict) -> str:
    """
    Uses the LLM once to classify the comparison into a routing category.
    """

    payload = {
        "Project A": project_a,
        "Project B": project_b,
    }

    prompt = (
        "Classify the following projects:\n\n"
        f"{json.dumps(payload, indent=2)}"
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
    )

    if category not in VALID_CATEGORIES:
        return "EXECUTIVE_REVIEW"

    return category