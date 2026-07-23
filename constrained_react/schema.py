"""
Constrained ReAct Agent - Schema
---------------------------------------------------
Defines the strict structure every step of the agent's reasoning loop
must follow.

If the model's output doesn't match this schema exactly, the step is
rejected and retried (see agent.py). This is what makes the loop
"constrained" instead of free-form.
"""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field, model_validator


# --------------------------------------------------------------------
# Allow-list: the ONLY tools the agent is permitted to call.
# If the model tries to call anything not in this list, validation
# fails automatically (Pydantic's Literal type enforces this).
# --------------------------------------------------------------------
AllowedTool = Literal[
    "check_delay_impact",
    "check_penalty_clause",
    "check_alternative_availability",
]


class ToolCall(BaseModel):
    """
    One action the agent wants to take. No tool_input needed: every
    tool always compares the SAME two projects (loaded once from
    data/projects.json), so the model only needs to say WHICH tool it
    wants, not what to pass into it.
    """
    tool_name: AllowedTool


class FinalAnswer(BaseModel):
    """The agent's final decision. Reaching this ends the loop."""
    recommended_project: Literal["Project A", "Project B"]
    reasons: List[str] = Field(min_length=1)


class AgentStep(BaseModel):
    """
    One step in the ReAct loop: Thought -> (Action | FinalAnswer | Escalate)

    Exactly ONE of action / final_answer / escalate must be present.
    Never zero, never two at once.
    """
    thought: str
    action: Optional[ToolCall] = None
    final_answer: Optional[FinalAnswer] = None
    escalate: Optional[str] = None

    @model_validator(mode="after")
    def exactly_one_decision(self):
        filled = [
            self.action is not None,
            self.final_answer is not None,
            self.escalate is not None,
        ]
        if sum(filled) != 1:
            raise ValueError(
                "Each step must contain exactly ONE of: "
                "action, final_answer, or escalate — never zero, never more than one."
            )
        return self