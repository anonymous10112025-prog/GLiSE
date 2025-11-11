# This script was created to run on Windows 10
import json
import os
import random
from typing import List, Tuple, Any
from github_repository_models_training import run_models_training_testing_pipeline_github_repos
from github_issues_models_training import run_models_training_testing_pipeline_github_issues
from google_models_training import run_models_training_testing_pipeline_google_cse
from stackoverflow_models_training import run_models_training_testing_pipeline_stackoverflow

def open_json(path_to_raw_fil):
    with open(path_to_raw_fil, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    return raw_data

def create_json(path_n_name, content):
    with open(path_n_name, "w", encoding="utf-8") as f:
        json.dump(content, f, indent=2, ensure_ascii=False)


def filtrate_dataset(raw_data):
    filtrated_data = []

    for elem in raw_data:

        rated_min = elem.get("rated")
        if rated_min is not None:
            rated = rated_min
        else:
            rated = elem.get("Rated")

        grade_min = elem.get("grade")
        if grade_min is not None:
            grade = grade_min
        else:
            grade = elem.get("Grade")

        if rated and (grade in [1, 2, 3, 4]):
            filtrated_data.append(elem)

    return filtrated_data

def split_dataset(
    data: List[Any],
    ratio: float = 0.5,
    seed: int = 42
) -> Tuple[List[Any], List[Any]]:
    """
    Shuffle and split a list into two parts.

    Args:
        data: list of items
        ratio: fraction of data in the first split (0-1)
        seed: random seed for reproducibility

    Returns:
        (first_split, second_split)
    """

    rng = random.Random(seed)
    data_copy = data[:]
    rng.shuffle(data_copy)

    split_index = int(len(data_copy) * ratio)

    return data_copy[:split_index], data_copy[split_index:]


RAW_REPOS_INFOS_PATH = input("Path to Github Repos Dataset : ")
RAW_ISSUES_INFOS_PATH = input("Path to Github Issues Dataset : ")
RAW_STACKOVERFLOW_INFOS_PATH = input("Path to Stackoverflow Dataset : ")
RAW_GOOGLES_INFOS_PATH = input("Path to Google Dataset : ")


name_of_execution = input("Name the script execution : ").strip()


filtrated_datasets_repo = f"{name_of_execution} - filtrated datasets"

os.makedirs(filtrated_datasets_repo, exist_ok=True)

filtrated_datasets_github_repos = filtrate_dataset(open_json(RAW_REPOS_INFOS_PATH))
create_json(f"{filtrated_datasets_repo}/filtered-github-respos.json", filtrated_datasets_github_repos)

filtrated_datasets_github_issues = filtrate_dataset(open_json(RAW_ISSUES_INFOS_PATH))
create_json(f"{filtrated_datasets_repo}/filtered-github-issues.json", filtrated_datasets_github_issues)

filtrated_datasets_stackoverflows = filtrate_dataset(open_json(RAW_STACKOVERFLOW_INFOS_PATH))
create_json(f"{filtrated_datasets_repo}/filtered-stackoverflows.json", filtrated_datasets_stackoverflows)

filtrated_datasets_googles = filtrate_dataset(open_json(RAW_GOOGLES_INFOS_PATH))
create_json(f"{filtrated_datasets_repo}/filtered-googles.json", filtrated_datasets_googles)

# Train Models:

# Github repos
train_set_repos, test_set_repos = split_dataset(data=filtrated_datasets_github_repos, ratio=0.5, seed=42)
run_models_training_testing_pipeline_github_repos(
    train_dataset=train_set_repos,
    test_dataset=test_set_repos,
    add_to_folder_name=name_of_execution
)

# Github issues
train_set_issues, test_set_issues = split_dataset(data=filtrated_datasets_github_issues, ratio=0.5, seed=42)
run_models_training_testing_pipeline_github_issues(
    train_dataset=train_set_issues,
    test_dataset=test_set_issues,
    add_to_folder_name=name_of_execution
)

# StackOverflow
train_set_stackoverflow, test_set_stackoverflow = split_dataset(data=filtrated_datasets_stackoverflows, ratio=0.5, seed=42)
run_models_training_testing_pipeline_stackoverflow(
    train_dataset=train_set_stackoverflow,
    test_dataset=test_set_stackoverflow,
    add_to_folder_name=name_of_execution
)

# Google
train_set_google, test_set_google = split_dataset(data=filtrated_datasets_googles, ratio=0.5, seed=42)
run_models_training_testing_pipeline_google_cse(
    train_dataset=train_set_google,
    test_dataset=test_set_google,
    add_to_folder_name=name_of_execution
)