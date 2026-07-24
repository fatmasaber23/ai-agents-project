"""
Unconstrained LLM-Powered Agent
--------------------------------
Problem: one piece of equipment (a crane) is requested by two projects at
the same time. The agent must decide which project keeps the equipment,
and what the other project should do instead.

The model gets a fixed set of tools and complete freedom:
- No schema validating its steps
- No allow-list restricting which tool it can call next
- No MAX_STEPS budget
- It decides on its own when it has "enough" information to answer

Compare this file's behavior with constrained_react/main.py, which wraps the
exact same reasoning loop in validation, an allow-list, and a step budget.
"""

import json
import os
from mistralai.client import Mistral

# --------------------------------------------------------------------------
# Config: tries config.py first (MISTRAL_API_KEY = "..."), falls back to .env
# --------------------------------------------------------------------------
try:
    from config import MISTRAL_API_KEY
except ImportError:
    from dotenv import load_dotenv
    load_dotenv()
    MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")

if not MISTRAL_API_KEY:
    raise RuntimeError(
        "MISTRAL_API_KEY not found. Set it in config.py or in a .env file."
    )

MODEL_NAME = "mistral-large-latest"
DATA_PATH = "data/projects.json"


# --------------------------------------------------------------------------
# Data access
# --------------------------------------------------------------------------
def load_projects():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


PROJECTS = load_projects()


# --------------------------------------------------------------------------
# Tools the model is free to call, in any order, any number of times
# --------------------------------------------------------------------------
def get_project_data(project_id: str) -> dict:
    """Return the raw stored data for a project's equipment request."""
    if project_id not in PROJECTS:
        return {"error": f"Unknown project_id '{project_id}'"}
    return PROJECTS[project_id]


def calculate_cost_of_denial(project_id: str) -> dict:
    """
    Calculate the direct cost this project incurs if it does NOT get the
    equipment: the contractual penalty, if one applies.
    """
    project = PROJECTS.get(project_id)
    if not project:
        return {"error": f"Unknown project_id '{project_id}'"}

    penalty_cost = project["penalty_amount"] if project["has_penalty_clause"] else 0

    return {
        "project_id": project_id,
        "delay_days_if_denied": project["delay_without_equipment_days"],
        "has_penalty_clause": project["has_penalty_clause"],
        "penalty_cost_egp": penalty_cost,
    }


def check_rental_alternative(project_id: str) -> dict:
    """
    Check whether a rented alternative could cover this project if it
    doesn't get the equipment. Meant to be checked for whichever project
    ends up NOT receiving the equipment, so its penalty/delay cost can be
    weighed against the cost of renting instead.
    """
    project = PROJECTS.get(project_id)
    if not project:
        return {"error": f"Unknown project_id '{project_id}'"}

    available = project["rental_alternative_available"]
    cost_per_day = project["rental_cost_per_day"] if available else None
    delay_days = project["delay_without_equipment_days"]
    estimated_rental_total = (
        round(cost_per_day * delay_days, 2) if available else None
    )

    return {
        "project_id": project_id,
        "rental_alternative_available": available,
        "rental_cost_per_day_egp": cost_per_day,
        "estimated_total_rental_cost_egp": estimated_rental_total,
    }


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_project_data",
            "description": "Get raw stored data for a project's equipment request (delay impact, penalty clause, rental alternative).",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "Either 'projectA' or 'projectB'.",
                    }
                },
                "required": ["project_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_cost_of_denial",
            "description": "Calculate the contractual penalty cost a project incurs if it does not receive the equipment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "Either 'projectA' or 'projectB'.",
                    }
                },
                "required": ["project_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_rental_alternative",
            "description": "Check if a rental alternative is available for a project and estimate its total cost for the delay period.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "Either 'projectA' or 'projectB'.",
                    }
                },
                "required": ["project_id"],
            },
        },
    },
]

TOOL_FUNCTIONS = {
    "get_project_data": get_project_data,
    "calculate_cost_of_denial": calculate_cost_of_denial,
    "check_rental_alternative": check_rental_alternative,
}


# --------------------------------------------------------------------------
# The unconstrained agent loop
# --------------------------------------------------------------------------
SYSTEM_PROMPT = """You are a decision-support agent for a construction company.
One piece of equipment (a crane) has been requested at the same time by two
active projects, projectA and projectB. Only one project can have it right
now.

You have tools available to investigate both projects. You decide freely
which tools to call, in which order, and how many times. There is no fixed
number of steps you must follow and no required sequence — use your own
judgement about what you need to know before deciding.

When you are satisfied you have enough information, stop calling tools and
give your final answer as plain text, clearly stating:
1. Which project should receive the equipment
2. What the other project should do instead (accept the delay, or use a
   rental alternative if one is available and cheaper than the penalty)
3. The reasoning behind the decision, including the numbers you used
"""


def run_agent(user_request: str):
    client = Mistral(api_key=MISTRAL_API_KEY)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_request},
    ]

    step = 0
    while True:
        step += 1
        print(f"\n--- Step {step}: calling model ---")

        response = client.chat.complete(
            model=MODEL_NAME,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        choice = response.choices[0]
        message = choice.message
        messages.append(message)

        tool_calls = getattr(message, "tool_calls", None)

        if not tool_calls:
            # Model decided it's done. No one forced this stopping point.
            print("\n=== FINAL ANSWER ===")
            print(message.content)
            return message.content

        # Model freely chose one or more tools to call this step.
        for call in tool_calls:
            fn_name = call.function.name
            fn_args = json.loads(call.function.arguments)

            print(f"Model called tool: {fn_name}({fn_args})")

            fn = TOOL_FUNCTIONS.get(fn_name)
            if fn is None:
                result = {"error": f"Unknown tool '{fn_name}'"}
            else:
                result = fn(**fn_args)

            print(f"Tool result: {result}")

            messages.append(
                {
                    "role": "tool",
                    "name": fn_name,
                    "tool_call_id": call.id,
                    "content": json.dumps(result),
                }
            )

        # NOTE: intentionally no MAX_STEPS check here — that constraint is
        # what distinguishes constrained_react/ from this agent. A generous
        # safety net only, to avoid a genuinely infinite loop during testing:
        if step >= 25:
            print("\n[safety stop after 25 steps — not a designed business rule]")
            return None


if __name__ == "__main__":
    run_agent(
        "The crane is requested right now by both projectA and projectB. "
        "Which one should get it, and what should the other project do "
        "instead? Investigate whatever you need to before deciding."
    )