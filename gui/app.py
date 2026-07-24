
"""
GUI Backend
-----------
Thin Flask wrapper around the four existing agents. It does NOT
reimplement any agent logic — it imports and calls the exact same
functions used by each `main.py`, so the GUI and the terminal runs are
always identical in behavior.
 
Project data (Project A / Project B) is supplied dynamically by the
person from the "Enter Project Data" screen in the GUI, instead of being
read from data/projects.json.
 
The GUI form uses short, human-friendly field names (delay, hasPenalty,
penaltyAmount, hasAlt, rentalCost). The agents expect the field names
used in data/projects.json (delay_without_equipment_days,
has_penalty_clause, penalty_amount, rental_alternative_available,
rental_cost_per_day). `normalize_project()` below converts one to the
other, so nothing in the agent code has to change.
 
Two different mechanisms are used to actually get that data into each
agent, because the four agents don't all fetch project data the same
way:
 
- reactive:      `decision()` takes project_a/project_b as direct
                  arguments, so we just pass the submitted data in.
- routing,
  constrained:    `run_routing_agent()` / `run_constrained_react_agent()`
                  take no arguments; both do
                  `from utils.load_data import load_projects` at the top
                  of their `main.py` and call it internally. We
                  temporarily monkey-patch the `load_projects` name
                  inside each of those two modules (for the duration of
                  one request only) so it returns the submitted data,
                  then restore it right after.
- unconstrained:  `unconstrained_llm/main.py` does NOT use
                  utils/load_data.py at all — it has its own local
                  `load_projects()` and loads the result ONCE into a
                  module-level `PROJECTS` dict when the module is first
                  imported. Its tools (get_project_data,
                  calculate_cost_of_denial, check_rental_alternative)
                  read from that `PROJECTS` global directly. So instead
                  of patching a function, we temporarily replace the
                  `PROJECTS` dict itself on that module for the
                  duration of the request, then restore it.
 
Expected folder structure (gui/ is a sibling of the four agent folders):
 
ai-agents-project/
    reactive/
    unconstrained_llm/
    routing/
    constrained_react/
    utils/
    data/
    gui/              <- this file lives in gui/app.py
        app.py
        templates/index.html
        static/style.css
        static/script.js
 
Run from the gui/ folder:
    pip install -r requirements.txt
    python app.py
Then open http://127.0.0.1:5000 in the browser.
"""
 
import contextlib
import io
import json
import os
import sys
from contextlib import contextmanager
 
# Make the repo root importable (one level up from gui/)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
 
from flask import Flask, jsonify, render_template, request
 
from utils.load_data import load_projects
from reactive.main import decision as reactive_decision
from routing.main import run_routing_agent
from constrained_react.main import run_constrained_react_agent
from unconstrained_llm.main import run_agent as run_unconstrained_agent
 
import routing.main as routing_main_module
import constrained_react.main as constrained_main_module
import unconstrained_llm.main as unconstrained_main_module
 
 
app = Flask(__name__)
 
# Front-end field name -> field name actually used by the agents
# (matches data/projects.json / utils/load_data.py).
FIELD_MAP = {
    "delay": "delay_without_equipment_days",
    "hasPenalty": "has_penalty_clause",
    "penaltyAmount": "penalty_amount",
    "hasAlt": "rental_alternative_available",
    "rentalCost": "rental_cost_per_day",
}
 
 
def normalize_project(raw: dict) -> dict:
    """Convert the GUI form's field names into the names the agents expect."""
    normalized = {}
    for front_key, backend_key in FIELD_MAP.items():
        if front_key in raw:
            normalized[backend_key] = raw[front_key]
        elif backend_key in raw:
            # Already using backend field names (e.g. a direct API call) — keep as-is.
            normalized[backend_key] = raw[backend_key]
    return normalized
 
 
def json_safe(value):
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)
 
 
def get_submitted_projects():
    """Read {projectA, projectB} from the POST body sent by the GUI form,
    converted to the field names the agents expect. Falls back to the
    on-disk data file if the request has no body, so hitting the API
    directly (e.g. via curl) still works."""
    body = request.get_json(silent=True) or {}
    project_a = body.get("projectA")
    project_b = body.get("projectB")
    if project_a and project_b:
        return {
            "projectA": normalize_project(project_a),
            "projectB": normalize_project(project_b),
        }
    return load_projects()
 
 
@contextmanager
def patched_project_data(projects):
    """Temporarily make routing/main.py and constrained_react/main.py load
    the person's submitted data instead of data/projects.json."""
 
    def patched():
        return projects
 
    originals = []
    for mod in (routing_main_module, constrained_main_module):
        if hasattr(mod, "load_projects"):
            originals.append((mod, mod.load_projects))
            mod.load_projects = patched
 
    try:
        yield
    finally:
        for mod, original in originals:
            mod.load_projects = original
 
 
@contextmanager
def patched_unconstrained_data(projects):
    """unconstrained_llm/main.py loads its own PROJECTS dict once at import
    time and its tools read straight from that global, so we swap the dict
    itself for the duration of the request instead of patching a function."""
    original = unconstrained_main_module.PROJECTS
    unconstrained_main_module.PROJECTS = projects
    try:
        yield
    finally:
        unconstrained_main_module.PROJECTS = original
 
 
@app.route("/")
def index():
    return render_template("index.html")
 
 
@app.route("/api/run/reactive", methods=["POST"])
def api_run_reactive():
    try:
        projects = get_submitted_projects()
        result = reactive_decision(projects["projectA"], projects["projectB"])
 
        return jsonify({
            "agent": "reactive",
            "recommended": result["recommended"],
            "trace": [{
                "step": 1,
                "label": result["rule_fired"],
                "detail": result["reason"],
            }],
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
 
 
@app.route("/api/run/routing", methods=["POST"])
def api_run_routing():
    try:
        projects = get_submitted_projects()
        with patched_project_data(projects):
            result = run_routing_agent()
 
        return jsonify({
            "agent": "routing",
            "recommended": result["recommended"],
            "trace": [{
                "step": 1,
                "label": result["category"],
                "detail": "; ".join(result["reasons"]),
            }],
            "other_project": result["other_project"],
            "other_project_action": result["other_project_action"],
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
 
 
@app.route("/api/run/constrained", methods=["POST"])
def api_run_constrained():
    try:
        projects = get_submitted_projects()
        with patched_project_data(projects):
            result = run_constrained_react_agent()
 
        trace = []
        for entry in result["trace"]:
            if "action" in entry:
                trace.append({
                    "step": entry["step"],
                    "label": entry["action"],
                    "detail": json_safe(entry["observation"]),
                })
            elif "final_answer" in entry:
                trace.append({
                    "step": entry["step"],
                    "label": "final_answer",
                    "detail": entry["thought"],
                })
            elif "escalate" in entry:
                trace.append({
                    "step": entry["step"],
                    "label": "escalate",
                    "detail": entry["escalate"],
                })
 
        recommended = result.get("recommended_project") or "Escalated"
 
        return jsonify({
            "agent": "constrained",
            "recommended": recommended,
            "status": result["status"],
            "trace": trace,
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
 
 
@app.route("/api/run/unconstrained", methods=["POST"])
def api_run_unconstrained():
    try:
        projects = get_submitted_projects()
        # This agent only prints as it goes and returns the final text, so we
        # capture stdout too, giving the GUI the full raw step-by-step log.
        buffer = io.StringIO()
        with patched_unconstrained_data(projects):
            with contextlib.redirect_stdout(buffer):
                final_text = run_unconstrained_agent(
                    "The crane is requested right now by both projectA and projectB. "
                    "Which one should get it, and what should the other project do "
                    "instead? Investigate whatever you need to before deciding."
                )
 
        return jsonify({
            "agent": "unconstrained",
            "final_answer": final_text,
            "raw_log": buffer.getvalue(),
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
 
 
if __name__ == "__main__":
    app.run(debug=True, port=5000)