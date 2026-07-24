# Agent Design Lab — Construction Company Equipment Allocation
 
## The Company & The Problem
 
We work at a mid-sized construction company that runs several active job
sites at once. Heavy equipment — cranes, in particular — is expensive and
limited in number, so it's shared across projects rather than owned per
site.
 
The problem: **two active projects need the same crane at the same time.**
Whoever doesn't get it faces a delay. Right now, this decision is made
informally — a site manager calls another site manager, they argue about
whose project is more urgent, and whoever escalates loudest usually wins,
regardless of which project actually stands to lose more.
 
That's a problem because:
- Some contracts carry financial penalty clauses for delay, and those get
  missed in an informal phone-call negotiation
- Some projects have a rental alternative available nearby (at a real but
  usually small cost), while others don't and would simply stop
- The decision changes depending on the specific combination of these
  factors for the two projects involved that week — it isn't the same
  answer every time
**Why this needs an agent and not a simple fixed script:** the right
decision depends on weighing multiple factors together (delay impact,
penalty exposure, whether a backup exists) whose relative importance shifts
from one pair of competing projects to the next. A hard-coded rule that
works for this week's two projects breaks the moment the numbers shift even
slightly — which is exactly what we set out to test by building the same
decision four different ways.
 
### The request each agent receives
 
Two competing projects, each described by:
 
| Field | Meaning |
|---|---|
| `delay_without_equipment_days` | Days this project is delayed if it does NOT get the equipment |
| `has_penalty_clause` | Whether the contract has a financial penalty for delay |
| `penalty_amount` | Penalty cost (EGP) if `has_penalty_clause` is true |
| `rental_alternative_available` | Whether a rental replacement exists nearby |
| `rental_cost_per_day` | Cost (EGP/day) of that rental, if available |
 
Each agent receives (or investigates) the same two projects and must decide:
**which project keeps the equipment, and what should the other project do
instead.**
 
---
 
## The Four Architectures
 
### `reactive/`
Pure if/then rule chain, no model call at all. Checks, in order: (1) does
only one project lack a rental alternative, (2) does only one project have
a penalty clause, (3) is the delay gap bigger than 4 days, (4) otherwise,
fall back to whichever penalty amount is higher. Stops at the first rule
that fires — never weighs more than one factor at a time.
 
**Model/provider:** none — plain Python.
 
**How to run:**
```
python -m reactive.main
```
 
### `unconstrained_llm/`
Free-form agent with 3 tools (`get_project_data`, `calculate_cost_of_denial`,
`check_rental_alternative`) and no schema, allow-list, or step limit. The
model decides which tools to call, in what order, and when to stop.
 
**Model/provider:** Mistral (`mistral-large-latest`) via direct REST calls.
 
**How to run:**
```
pip install requests python-dotenv
python -m unconstrained_llm.main
```
Requires `MISTRAL_API_KEY` in `config.py` or a `.env` file.
 
### `routing/`
A single classification call sorts the request into one of four review
categories (`DELAY_REVIEW`, `PENALTY_REVIEW`, `ALTERNATIVE_REVIEW`,
`EXECUTIVE_REVIEW`) based on pre-calculated percentage differences — the
model never sees raw project data, only the diffs. Everything after that
is fixed, testable Python (`routing/workflows.py`).
 
**Model/provider:** Mistral, one call per request, via `utils/mistral_client.py`.
 
**How to run:**
```
python -m routing.main
```
 
### `constrained_react/`
Same Thought → Action → Observation loop as the unconstrained agent, but
every step is validated against a Pydantic schema (`schema.py`), tool
calls are restricted to a 3-tool allow-list (`tools.py`), `MAX_STEPS = 8`
is enforced, and the agent must end in either a `final_answer` or an
explicit `escalate` — it is not allowed to force a weak recommendation
when the evidence is balanced.
 
**Model/provider:** Mistral, up to `MAX_STEPS` sequential calls, via
`utils/mistral_client.py`.
 
**How to run:**
```
python -m constrained_react.main
```
 
### GUI (optional, all four agents in one place)
A small Flask app (`gui/`) wraps all four `main.py` entry points behind
"Run" buttons in a single dashboard, so all four can be triggered without
touching the terminal. See `gui/app.py` for setup.
 
---
 
## Comparison Table
 
Test input used for the table below (the "tricky" case): two projects with
very close numbers across every factor — Project A: 15-day delay, 25,000
EGP penalty, rental at 10,000 EGP/day. Project B: 14-day delay, 26,000 EGP
penalty, rental at 9,500 EGP/day. Nothing dominates clearly on any single
factor, which is exactly the situation the guardrails asked us to design
for.
 
| Agent | LLM calls per request | Approx. cost / tokens | Latency | What happened with the tricky input |
|---|---|---|---|---|
| Reactive | 0 | — (no API cost) | Instant (pure Python) | Fell through to the last fallback rule (`default_penalty_amount`) and returned **Project B** confidently, with no indication that every earlier rule was a near-tie |
| Deterministic Routing | 1 | Small — one short prompt (just the pre-computed diffs, not raw data) + a single-word category reply | Fast — one round trip | Correctly routed to `EXECUTIVE_REVIEW` (recognized the conflict), but the weighted score resolved to **Project A** by a razor-thin margin (0.503 vs 0.497) and presented it as a normal, confident recommendation |
| Unconstrained ReAct | 3 | Higher — growing conversation history sent back on every call as more tool results accumulate | Slowest of the two LLM-based ReAct agents (3 sequential round trips) | Investigated both projects and both cost angles, but its own written reasoning became internally inconsistent (at one point arguing for opposite conclusions in the same paragraph) before still landing on a confident-sounding **Project B** |
| Constrained ReAct | 4 (equal to `MAX_STEPS` in this run) | Similar to unconstrained per call, plus schema validation overhead | Slowest overall (4 forced sequential steps, one tool per step) | Investigated delay → penalty → alternatives one at a time, correctly recognized the evidence was balanced across all three factors, and **escalated instead of forcing a pick** — the only agent that did this |
 
---
 
## Guardrails Followed
 
- Same `data/projects.json` input used across all four agents for a fair
  comparison
- No API key committed; `MISTRAL_API_KEY` loaded from `.env` / `config.py`,
  both excluded via `.gitignore`
- The decision genuinely depends on multi-step evidence gathering (delay →
  penalty → alternative), not a single classification pass — this is what
  the Constrained ReAct agent's schema in `constrained_react/schema.py`
  enforces step by step, and it's also why this same close-numbers input
  produced four different behaviors instead of four copies of the same
  answer