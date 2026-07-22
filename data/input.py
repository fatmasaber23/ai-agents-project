import json

VALID_RISKS = {"low", "medium", "high"}


# -------------------- Validation Functions --------------------

def get_money(message):
    while True:
        try:
            value = float(input(message))

            if value > 0:
                return value

            print("Value must be greater than 0.")

        except ValueError:
            print("Please enter a valid number.")


def get_percentage(message):
    while True:
        try:
            value = int(input(message))

            if 0 <= value <= 100:
                return value

            print("Enter a percentage between 0 and 100.")

        except ValueError:
            print("Please enter a valid integer.")


def get_risk(project_name):
    while True:
        risk = input(
            f"{project_name} Risk (low / medium / high): "
        ).strip().lower()

        if risk in VALID_RISKS:
            return risk

        print("Invalid risk. Allowed values: low, medium or high.")


def get_duration(project_name):
    while True:

        duration = input(
            f"{project_name} Duration (Example: 10d or 6m): "
        ).strip().lower()

        try:

            if duration.endswith("d"):

                days = float(duration[:-1])

                if days <= 0:
                    print("Duration must be greater than 0.")
                    continue

                months = round(days / 30, 2)
                return months, f"{days} Days"

            elif duration.endswith("m"):

                months = float(duration[:-1])

                if months <= 0:
                    print("Duration must be greater than 0.")
                    continue

                return months, f"{months} Months"

            else:
                print("Enter duration like 10d or 6m.")

        except ValueError:
            print("Invalid duration format.")


# -------------------- Project Input --------------------

def get_project(project_name):

    print(f"\n========== {project_name} ==========\n")

    project = {}

    project["profit"] = get_money(
        f"{project_name} Profit (Million): "
    )

    project["risk"] = get_risk(project_name)

    duration_months, duration_display = get_duration(project_name)
    project["duration"] = duration_months
    project["duration_unit"] = "months"

    project["budget"] = get_money(
        f"{project_name} Budget (Million): "
    )

    project["team_availability"] = get_percentage(
        f"{project_name} Team Availability (%): "
    )

    project["equipment_availability"] = get_percentage(
        f"{project_name} Equipment Availability (%): "
    )

    return project, duration_display


# -------------------- Collect Data --------------------

projectA, displayA = get_project("Project A")
projectB, displayB = get_project("Project B")


# -------------------- Summary --------------------

print("\n================ PROJECT SUMMARY ================\n")

print("Project A")
print(f"Profit                 : {projectA['profit']} M")
print(f"Risk                   : {projectA['risk'].title()}")
print(
    f"Duration               : {displayA} ({projectA['duration']} {projectA['duration_unit']})"
)
print(f"Budget                 : {projectA['budget']} M")
print(f"Team Availability      : {projectA['team_availability']}%")
print(f"Equipment Availability : {projectA['equipment_availability']}%")

print("\n------------------------------------------------\n")

print("Project B")
print(f"Profit                 : {projectB['profit']} M")
print(f"Risk                   : {projectB['risk'].title()}")
print(
    f"Duration               : {displayB} ({projectB['duration']} {projectB['duration_unit']})"
)
print(f"Budget                 : {projectB['budget']} M")
print(f"Team Availability      : {projectB['team_availability']}%")
print(f"Equipment Availability : {projectB['equipment_availability']}%")


projects = {
    "projectA": projectA,
    "projectB": projectB
}


with open("data/projects.json", "w", encoding="utf-8") as file:
    json.dump(projects, file, indent=4, ensure_ascii=False)


print("\nProjects saved successfully")