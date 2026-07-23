"""
Constrained ReAct Agent - Loop
--------------------------------------------------
The reasoning loop:
Thought -> Action -> Observation -> Thought -> ...

The model NEVER sees the project data directly.
It must gather information only by calling tools.
"""

import json

from pydantic import ValidationError
from tenacity import Retrying, stop_after_attempt, retry_if_exception_type

from constrained_react.schema import AgentStep
from constrained_react.tools import TOOL_REGISTRY
from utils.mistral_client import ask_mistral


MAX_STEPS = 8
MAX_VALIDATION_RETRIES = 2

SYSTEM_PROMPT = """
You are a Constrained ReAct agent for a construction company.

Two projects need the same equipment at the same time.

IMPORTANT:
You DO NOT know any project information.
The ONLY way to obtain information is by calling tools.

Available tools:

- check_delay_impact
- check_penalty_clause
- check_alternative_availability

Rules:

1. Start by calling a tool.
2. After every observation, think again.
3. Call another tool only if you still need more evidence.
4. Never assume information that has not been observed.
5. Do NOT produce a final answer until you have enough evidence.
6. You may stop early if you become confident.
7. Before producing a final answer, evaluate ALL observations together.
8. If most observations clearly support one project, return a final_answer.
9. If different observations support different projects and no project clearly dominates, DO NOT force a recommendation.
10. In balanced or conflicting situations, return an escalate response instead.
11. Escalation is a valid outcome and is preferred over making a weak or arbitrary recommendation.
12. Never invent tool names.

Examples of situations that should be escalated:

- Delay favors Project A, but penalty favors Project B.
- Both projects have similar evidence with no dominant winner.
- Rental alternatives are similar and do not clearly resolve the conflict.
- Overall confidence is low after reviewing all observations.

Return ONLY ONE JSON object.

Action:

{
  "thought":"...",
  "action":{
      "tool_name":"check_delay_impact"
  }
}

Final:

{
  "thought":"...",
  "final_answer":{
      "recommended_project":"Project A",
      "reasons":[
          "...",
          "..."
      ]
  }
}

Escalate:

{
  "thought":"The collected evidence is balanced and no project clearly dominates.",
  "escalate":"Executive review is required because the available evidence is inconclusive."
}

Exactly ONE of:
- action
- final_answer
- escalate
"""

def _parse_step(raw_text: str) -> AgentStep:

    cleaned = raw_text.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]

    data = json.loads(cleaned)
    return AgentStep.model_validate(data)


def _get_valid_step(base_prompt: str) -> AgentStep:

    last_error = None

    for attempt in Retrying(
        stop=stop_after_attempt(MAX_VALIDATION_RETRIES + 1),
        retry=retry_if_exception_type((json.JSONDecodeError, ValidationError)),
        reraise=True,
    ):

        with attempt:

            prompt = base_prompt

            if last_error is not None:

                prompt += (
                    f"\n\nPrevious response was INVALID:\n{last_error}"
                    "\nReturn ONLY valid JSON."
                )

            try:

                raw = ask_mistral(
                    prompt=prompt,
                    system=SYSTEM_PROMPT,
                    temperature=0
                )

                return _parse_step(raw)

            except (json.JSONDecodeError, ValidationError) as exc:

                last_error = str(exc)
                raise

    raise RuntimeError()


def run_constrained_react(project_a, project_b):

    transcript = """
Two construction projects require the same equipment.

You currently know NOTHING about them.

Start by deciding which tool to call first.
"""

    trace = []

    for step_number in range(1, MAX_STEPS + 1):

        try:
            step = _get_valid_step(transcript)

        except (json.JSONDecodeError, ValidationError) as exc:

            return {
                "status": "escalated",
                "reason": str(exc),
                "trace": trace,
                "steps_used": step_number,
            }

        entry = {
            "step": step_number,
            "thought": step.thought,
        }

        if step.action:

            tool_name = step.action.tool_name

            observation = TOOL_REGISTRY[tool_name](
                project_a,
                project_b,
            )

            entry["action"] = tool_name
            entry["observation"] = observation

            trace.append(entry)

            transcript += f"""

Thought:
{step.thought}

Tool:
{tool_name}

Observation:
{json.dumps(observation)}

Think again.
"""

            continue

        if step.final_answer:

            entry["final_answer"] = step.final_answer.model_dump()

            trace.append(entry)

            return {
                "status": "final_answer",
                "recommended_project": step.final_answer.recommended_project,
                "reasons": step.final_answer.reasons,
                "trace": trace,
                "steps_used": step_number,
            }

        entry["escalate"] = step.escalate
        trace.append(entry)

        return {
            "status": "escalated",
            "reason": step.escalate,
            "trace": trace,
            "steps_used": step_number,
        }

    return {
        "status": "escalated",
        "reason": f"MAX_STEPS ({MAX_STEPS}) reached.",
        "trace": trace,
        "steps_used": MAX_STEPS,
    }