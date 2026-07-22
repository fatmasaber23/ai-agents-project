"""
Routing Agent - Main Entry Point
--------------------------------------------------

Pipeline:

1. Load project data.
2. Ask the Routing Classifier to choose one review category.
3. Execute the matching deterministic workflow.
4. Display the recommendation.
"""

from utils.load_data import load_projects

from routing.classifier import classify_scenario

from routing.workflows import (
    financial_review,
    risk_review,
    resource_review,
    executive_review,
)


WORKFLOWS = {
    "FINANCIAL_REVIEW": financial_review,
    "RISK_REVIEW": risk_review,
    "RESOURCE_REVIEW": resource_review,
    "EXECUTIVE_REVIEW": executive_review,
}


def run_routing_agent():
    """
    Execute the Routing Agent pipeline.
    """

    # ---------------------------
    # Load Data
    # ---------------------------

    projects = load_projects()

    project_a = projects["projectA"]
    project_b = projects["projectB"]

    # ---------------------------
    # Routing Decision
    # ---------------------------

    category = classify_scenario(
        project_a,
        project_b
    )

    # ---------------------------
    # Execute Workflow
    # ---------------------------

    selected_workflow = WORKFLOWS.get(category)

    if selected_workflow is None:
        raise ValueError(f"Unknown workflow: {category}")

    result = selected_workflow(
        project_a,
        project_b
    )

    # ---------------------------
    # Display Result
    # ---------------------------

    print("\n" + "=" * 60)
    print("         ROUTING AGENT RESULT")
    print("=" * 60)

    print(f"\nSelected Review : {result['category']}")
    print(f"Recommended     : {result['recommended']}")

    print("\nReasons:")

    for reason in result["reasons"]:
        print(f" • {reason}")

    print("\nScores:")

    for project, score in result["scores"].items():
        print(f" {project}: {score}")

    print("\n" + "=" * 60)

    return result


if __name__ == "__main__":
    run_routing_agent()