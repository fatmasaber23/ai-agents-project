import json


def load_projects():

    with open(
        "data/projects.json",
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)