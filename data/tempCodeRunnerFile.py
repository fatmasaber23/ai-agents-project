import json


# -------------------- Validation Functions --------------------

def get_days(message):
    while True:
        try:
            value = float(input(message))

            if value >= 0:
                return value

            print("Value must be 0 or greater.")

        except ValueError:
            print("Please enter a valid number.")


def get_money(message):
    while True:
        try:
            value = float(input(message))

            if value >= 0:
                return value

            print("Value must be 0 or greater.")

        except ValueError:
            print("Please enter a valid number.")


def get_yes_no(message):
    while True:
        answer = input(f"{message} (y/n): ").strip().lower()

        if answer in ("y", "yes"):
            return True

        if answer in ("n", "no"):
            return False

        print("Please answer y or n.")


# -------------------- Project Input --------------------

def get_project(project_name):

    print(f"\n========== {project_name} ==========\n")

    project = {}

    project["delay_without_equipment_days"] = get_days(
        f"{project_name} - Delay if equipment is NOT assigned (days): "
    )

    project["has_penalty_clause"] = get_yes_no(
        f"{project_name} - Does the contract have a delay penalty clause?"
    )

    if project["has_penalty_clause"]:
        project["penalty_amount"] = get_money(
            f"{project_name} - Penalty amount (EGP): "
        )
    else:
        project["penalty_amount"] = 0

    project["rental_alternative_available"] = get_yes_no(
        f"{project_name} - Is a rental alternative available nearby?"
    )

    if project["rental_alternative_available"]:
        project["rental_cost_per_day"] = get_money(
            f"{project_name} - Rental cost per day (EGP): "
        )
    else:
        project["rental_cost_per_day"] = 0

    return project


# -------------------- Collect Data --------------------

projectA = get_project("Project A")
projectB = get_project("Project B")


# -------------------- Summary --------------------

print("\n================ REQUEST SUMMARY ================\n")

for name, project in (("Project A", projectA), ("Project B", projectB)):
    print(name)
    print(f"Delay Without Equipment : {project['delay_without_equipment_days']} days")
    print(f"Penalty Clause          : {'Yes' if project['has_penalty_clause'] else 'No'}")
    print(f"Penalty Amount          : {project['penalty_amount']} EGP")
    print(f"Rental Alternative      : {'Available' if project['rental_alternative_available'] else 'Not Available'}")
    print(f"Rental Cost / Day       : {project['rental_cost_per_day']} EGP")
    print()


projects = {
    "projectA": projectA,
    "projectB": projectB
}


with open("data/projects.json", "w", encoding="utf-8") as file:
    json.dump(projects, file, indent=4, ensure_ascii=False)


print("Requests saved successfully")