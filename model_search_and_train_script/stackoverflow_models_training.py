from collections import defaultdict
from dotenv import load_dotenv
import os
import json

import joblib
from openai import OpenAI

import tiktoken

import numpy as np

from sklearn.naive_bayes import GaussianNB
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.metrics import make_scorer, balanced_accuracy_score
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score
)
from sklearn.linear_model import LogisticRegression, RidgeClassifier
from sklearn.svm import LinearSVC
from xgboost import XGBClassifier

import time
import requests

from sklearn.model_selection import permutation_test_score

from bs4 import BeautifulSoup

TRUE_TOKEN = "True"
FALSE_TOKEN = "False"

SAFE_MAX_TOKENS_REQ = 290_000
OVERHEAD_PER_INPUT = 150 # https://github.com/timescale/pgai/issues/728 # REEEEEEEEEEEEEEEEEEEEEEEEE

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAIKEY"))

def clean_html_for_embedding(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    # Remove scripts/styles
    for tag in soup(["script", "style"]):
        tag.decompose()
    # Optionally remove other unwanted tags like nav/footer if you know the structure
    # Extract text
    text = soup.get_text(separator=" ", strip=True)
    # Collapse multiple whitespace into single space
    import re
    text = re.sub(r'\s+', ' ', text)
    return text

def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0:
        return 0
    return dot / norm

def cosine_distance(a, b):
    return 1 - cosine_similarity(a, b)

def euclidean_distance(a, b):
    a = np.array(a)
    b = np.array(b)
    return np.linalg.norm(a - b)

def l1_distance(a, b):
    a = np.array(a)
    b = np.array(b)
    return np.sum(np.abs(a - b))

def difference_vector(a, b):
    a = np.array(a)
    b = np.array(b)
    return np.abs(a - b)

# def overlap_min_vector(a, b):
#     a = np.array(a)
#     b = np.array(b)
#     return np.minimum(a, b)

def overlap_product_vector(a, b):
    a = np.array(a)
    b = np.array(b)
    return a * b

def truncate_to_X_tokens(text: str, model: str = "gpt-4o", truncate_limit: int = 8100):
    """
    Count tokens using tiktoken, truncate to <=8100 tokens, and return:
      - truncated or original text
      - number of tokens in returned text
    """

    # Load encoding for the given model
    encoding = tiktoken.encoding_for_model(model)

    # Encode text -> tokens
    tokens = encoding.encode(text)
    original_count = len(tokens)

    # If ≤truncate_limit tokens → return original
    if original_count <= truncate_limit:
        return text, original_count

    # Else → truncate
    # truncated_tokens = tokens[:(truncate_limit-1)]  # keep first 8099
    ellipsis_tokens = encoding.encode("...")
    ellipsis_tokens_nbr = len(ellipsis_tokens)
    truncated_tokens = tokens[:(truncate_limit-ellipsis_tokens_nbr)]

    # Add ellipsis (may be >1 token depending on tokenizer, but that's fine)
    final_tokens = truncated_tokens + ellipsis_tokens

    # Decode back to string
    text_out = encoding.decode(final_tokens)

    # Count returned tokens
    returned_count = len(final_tokens)

    return text_out, returned_count


def text_batches_to_send(texts: list[str], model: str = "gpt-4o"):

    tokens_count = 0
    grouped_texts = []
    text_group = []
    for text in texts:
        adj_text, adj_text_token_count = truncate_to_X_tokens(text=text, model=model)

        if (tokens_count + adj_text_token_count + OVERHEAD_PER_INPUT) > SAFE_MAX_TOKENS_REQ :
            grouped_texts.append(text_group.copy())
            text_group = [adj_text]
            tokens_count = adj_text_token_count + OVERHEAD_PER_INPUT
            
        else:
            text_group.append(adj_text)
            tokens_count += adj_text_token_count + OVERHEAD_PER_INPUT

    if len(text_group) > 0:
        grouped_texts.append(text_group.copy())

    return grouped_texts


def make_call_embeddings(texts: list[str], dimensions: int = 2048, embedding_model: str = "text-embedding-3-small", tokenizer_model: str = "text-embedding-3-small"):

    texts_batches = text_batches_to_send(texts=texts, model=tokenizer_model)

    # load_dotenv()

    # openai_key = os.getenv("OPENAIKEY")

    # client = OpenAI(api_key=openai_key)

    list_embeddings = []

    for texts_batch in texts_batches:
        print(f"Getting the embeddings of {len(texts_batch)} strings")
        response = client.embeddings.create(
            model=embedding_model,
            input=texts_batch,
            encoding_format="float",
            dimensions=dimensions
            # dimensions=1024
        )

        # list_embeddings = list_embeddings + response.data[0].embedding
        list_embeddings.extend([d.embedding for d in response.data])

        time.sleep(1) # adjust for your needs...

    return list_embeddings

def safe_non_empty_string_field_access(field, dictionnary, placeholder = "N/A"):
    val_obtained = dictionnary.get(field, placeholder)
    if not isinstance(val_obtained, str):
        return placeholder

    text = val_obtained.strip()
    if len(text) == 0:
        return placeholder
    return val_obtained


def get_measures_from_embeddings(all_embeddings, binary_flags):
    only_cosine_distances = [] # 3 dimension vectors -> cosine distances

    only_euclidean_distances = [] # 3 dimension vectors -> euclidean distances

    only_l1_distances = [] # 3 dimension vectors -> L1 distances

    cos_and_euclidean_distances = [] # 6 dimension vectors -> Cosine + euclidean distances

    only_distances = [] # 9 dimension vectors -> cosine, euclidean, L1 distances

    difference_vectors = [] # vectors of the difference between the search intent and metadata

    product_overlap_vectors = [] # vectors of the overlap (product) between the search intent and metadata

    all_measures = [] # vectors all between

    index = 0
    for flag in binary_flags:
        search_intent_embedding = all_embeddings[index]
        name_embedding = all_embeddings[index+1]
        snippet_embedding = all_embeddings[index+2]
        url_embedding = all_embeddings[index+3]

        # Cosine Distances
        cos_distances = [
            cosine_distance(search_intent_embedding, name_embedding),
            cosine_distance(search_intent_embedding, snippet_embedding),
            cosine_distance(search_intent_embedding, url_embedding)
        ]

        only_cosine_distances.append(cos_distances)

        # Euclidean Distances
        euclidean_distances = [
            euclidean_distance(search_intent_embedding, name_embedding),
            euclidean_distance(search_intent_embedding, snippet_embedding),
            euclidean_distance(search_intent_embedding, url_embedding)
        ]

        only_euclidean_distances.append(euclidean_distances)

        # Cosine and Euclidean Distances
        cos_and_euclidean_distances.append(cos_distances + euclidean_distances)

        # L1 Distances
        l1_distances = [
            l1_distance(search_intent_embedding, name_embedding),
            l1_distance(search_intent_embedding, snippet_embedding),
            l1_distance(search_intent_embedding, url_embedding)
        ]

        only_l1_distances.append(l1_distances)

        # Distances
        distances = cos_distances + euclidean_distances + l1_distances

        only_distances.append(distances)

        # Differences
        differences = difference_vector(search_intent_embedding, name_embedding).tolist() + difference_vector(search_intent_embedding, snippet_embedding).tolist() + difference_vector(search_intent_embedding, url_embedding).tolist()

        difference_vectors.append(differences)

        # Overlap / Product
        overlap_products = overlap_product_vector(search_intent_embedding, name_embedding).tolist() + overlap_product_vector(search_intent_embedding, snippet_embedding).tolist() + overlap_product_vector(search_intent_embedding, url_embedding).tolist()

        product_overlap_vectors.append(overlap_products)

        # All together
        all_measures.append(distances + differences + overlap_products)

        index += 4

    return {
            "cosine_distances": only_cosine_distances,
            "euclidean_distances": only_euclidean_distances,
            "cosine_and_euclidean_distances": cos_and_euclidean_distances,
            "l1_distances": only_l1_distances,
            "distances": only_distances,
            "differences": difference_vectors,
            "overlap_product": product_overlap_vectors,
            "all": all_measures
        }


def prepare_infos_testing_and_training(the_dataset, dimensions, embedding_model, tokenizer_model):
    train_binary_flags = []

    texts_to_embed = []

    for so_post_infos in the_dataset:
        texts_to_embed.append(safe_non_empty_string_field_access("search_intent", so_post_infos))
        texts_to_embed.append(safe_non_empty_string_field_access("title", so_post_infos))
        texts_to_embed.append(clean_html_for_embedding(safe_non_empty_string_field_access("snippet", so_post_infos)))
        texts_to_embed.append(safe_non_empty_string_field_access("url", so_post_infos))

        relevance_grade = so_post_infos["grade"]

        binary_flag = False
        if relevance_grade >= 3:
            binary_flag = True

        train_binary_flags.append(binary_flag)

    print("Getting Embeddings of the elements of the Dataset ...")

    all_training_embeddings = make_call_embeddings(texts=texts_to_embed, dimensions=dimensions, embedding_model=embedding_model, tokenizer_model=tokenizer_model)

    dict_features_value = get_measures_from_embeddings(
        all_embeddings=all_training_embeddings,
        binary_flags=train_binary_flags
    )

    return train_binary_flags, dict_features_value



def llm_binary_decide(search_intent: str, title: str, snippet: str, url: str, previous_decision: float) -> bool:
    """
    Calls LLM and forces a single-token result: True or False.
    Returns boolean decision
    """

    system_message = f"""
You are a strict binary classifier.
Your only job is to decide whether a StackOverflow Post is relevant
to a given search intent.

You MUST output exactly ONE token:
>>> {TRUE_TOKEN}  OR  {FALSE_TOKEN} <<<

Rules:
- No punctuation.
- No spaces or newline before or after the token.
- No explanation.
- No quotes.
Output format must be exactly one token.
""".strip()

    prompt = f"""
You are a binary classifier.
Determine whether the StackOverflow Post appears relevant to the intent.

You must choose exactly ONE token: {TRUE_TOKEN} or {FALSE_TOKEN}.

search_intent:
{search_intent}

title:
{title}

post:
{snippet}

url:
{url}
"""
    
    small_add_at_end = f"\n\nRespond only with EXACTLY {TRUE_TOKEN} or {FALSE_TOKEN}."

    user_message, _ = truncate_to_X_tokens(prompt, "gpt-4o", 15000)

    user_message = user_message + small_add_at_end

    reply = client.chat.completions.create(
        model="gpt-4o-2024-08-06",
         messages=[
            {"role": "system", "content": system_message},
            {"role": "user",   "content": user_message}
        ],
        max_completion_tokens=1,
        logprobs=True,
        top_logprobs=2,
        temperature=0
    )

    print(reply.choices[0].message)

    if reply.choices[0].logprobs is None or reply.choices[0].logprobs.content is None:
        print(reply)
        print(f"Problem with the logprobs... check the traces...")

        return previous_decision >= 0.5

    top_logprobs_list = reply.choices[0].logprobs.content[0].top_logprobs

    return top_logprobs_list[0].token.strip().lower() == TRUE_TOKEN.lower()



def test_gpt_4o_perf(the_test_dataset, nbr_iter = 5):


    list_BA = []
    list_prec = []
    list_rec = []
    list_f1 = []
    list_time = []

    for _ in range(nbr_iter):

        list_truth = []

        list_decisions = []

        time_LLM_pred_start = time.time()
        for so_post_infos in the_test_dataset:
            list_decisions.append(llm_binary_decide(
                search_intent=safe_non_empty_string_field_access("search_intent", so_post_infos),
                title=safe_non_empty_string_field_access("title", so_post_infos),
                snippet=clean_html_for_embedding(safe_non_empty_string_field_access("snippet", so_post_infos)),
                url=safe_non_empty_string_field_access("url", so_post_infos),
                previous_decision=0.5
            ))
            relevance_grade = so_post_infos["grade"]

            binary_flag = False
            if relevance_grade >= 3:
                binary_flag = True

            list_truth.append(binary_flag)

        time_LLM_pred_end = time.time()

        y_test = np.array(list_truth)

        predictions = np.array(list_decisions)

        list_BA.append(balanced_accuracy_score(y_test, predictions))
        list_prec.append(precision_score(y_test, predictions, zero_division=0))
        list_rec.append(recall_score(y_test, predictions, zero_division=0))
        list_f1.append(f1_score(y_test, predictions, zero_division=0))
        list_time.append(time_LLM_pred_end - time_LLM_pred_start)

    return {
            "Mean BA": np.mean(list_BA),
            "Median BA": np.median(list_BA),
            "Mean Precision": np.mean(list_prec),
            "Median Precision": np.median(list_prec),
            "Mean Recall": np.mean(list_rec),
            "Median Recall": np.median(list_rec),
            "Mean F1": np.mean(list_f1),
            "Median F1": np.median(list_f1),
            "Mean Predict Time": np.mean(list_time),
            "Median Predict Time": np.median(list_time),
            "Number Iterations": nbr_iter
        }

    
# dimensions = 1024

def run_models_training_testing_pipeline_stackoverflow(train_dataset, test_dataset, add_to_folder_name):

    root_folder = f"{str(add_to_folder_name).strip()} - StackOverflow - OpenAI"
    os.makedirs(root_folder, exist_ok=True)

    start_time = time.time()

    # for dimensions in [128, 256, 512, 1024, 2048]:
    # 1536
    # for dimensions in [256, 1024, 2048]:

    for embed_model in ["text-embedding-3-small", "text-embedding-3-large"]:

        start_time_model = time.time()

        for dimensions in [512, 1024, 1536]:

            dimension_time_start = time.time()

            folder_name = f"{root_folder}/{embed_model} - {dimensions} dimensions"
            os.makedirs(folder_name, exist_ok=True)

            train_binary_flags, dict_for_model_train_loop = prepare_infos_testing_and_training(
                the_dataset=train_dataset,
                dimensions=dimensions,
                embedding_model=embed_model,
                tokenizer_model=embed_model
            )

            dict_models = {} # Dictionnary to save the different models

            dict_models_save_infos = {}

            model_folder = f"{folder_name}/models"
            os.makedirs(model_folder, exist_ok=True)

            for features, features_values in dict_for_model_train_loop.items():

                print(f"Training models with the {features} features")

                x_train = np.array(features_values)
                y_train = np.array(train_binary_flags)

                # cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
                cv = StratifiedKFold(n_splits=4, shuffle=True, random_state=42)
                scorer = make_scorer(balanced_accuracy_score)

                # Train GaussianNB
                print(f"Training GaussianNB - {features}")
                gaussianNB_model = GaussianNB()
                gaussianNB_model.fit(
                    X=x_train,
                    y=y_train
                )
                dict_models[f"GaussianNB-{features}"] = {
                    "model": gaussianNB_model,
                    "features": features,
                    "supports_predict_proba": True
                }

                path = f"{model_folder}/GaussianNB-{features}.joblib"
                joblib.dump(gaussianNB_model, path)

                dict_models_save_infos[f"GaussianNB-{features}"] = {
                    "path": path,
                    "features": features
                }

                # Train Logistic Regression (with appropriate grid)
                print(f"Training Logistic Regression - {features}")
                logreg = LogisticRegression(
                    # max_iter=2000,
                    # max_iter=5000,
                    max_iter=10000,
                    random_state=42,
                    penalty="l2",
                )

                logreg_grid = {
                    # "penalty": ["l1", "l2"],
                    # "C": [0.25, 1.0, 4.0],
                    "C": [0.1, 0.25, 1.0, 4.0, 8.0],
                    "class_weight": [None, "balanced"],
                    "solver": ["liblinear", "saga"],   # both support l1 + l2
                }

                logreg_gs = GridSearchCV(
                    estimator=logreg,
                    param_grid=logreg_grid,
                    scoring=scorer,
                    cv=cv,
                    n_jobs=-1,
                    # verbose=0,
                    verbose=1,
                )

                logreg_gs.fit(x_train, y_train)
                dict_models[f"LogReg-{features}"] = {
                    "model": logreg_gs.best_estimator_,
                    "features": features,
                    "supports_predict_proba": True
                }

                path = f"{model_folder}/LogReg-{features}.joblib"
                joblib.dump(logreg_gs.best_estimator_, path)

                dict_models_save_infos[f"LogReg-{features}"] = {
                    "path": path,
                    "features": features
                }
                

                # Train XGBoost (with appropriate grid)
                print(f"Training XGBoost - {features}")
                xgb = XGBClassifier(
                    objective="binary:logistic",
                    eval_metric="logloss",
                    tree_method="hist",
                    random_state=42,
                    n_jobs=-1,
                )

                pos = int(np.sum(y_train))
                neg = int(len(y_train) - pos)
                scale_pos_weight = (neg / pos) if pos > 0 else 1.0

                xgb_grid = {
                    "n_estimators": [25, 50, 75],
                    "max_depth": [2, 3, 5],
                    "learning_rate": [0.05, 0.1],
                    # "subsample": [0.7, 0.9],
                    # "colsample_bytree": [0.7, 1.0],
                    # "reg_lambda": [1.0, 3.0],
                    # "reg_alpha": [0.0, 0.5],
                    "scale_pos_weight": [1.0, scale_pos_weight],
                }

                xgb_gs = GridSearchCV(
                    estimator=xgb,
                    param_grid=xgb_grid,
                    scoring=scorer,      # balanced accuracy
                    cv=cv,               # StratifiedKFold
                    n_jobs=-1,
                    verbose=1,
                )

                xgb_gs.fit(x_train, y_train)

                dict_models[f"XGB-{features}"] = {
                    "model": xgb_gs.best_estimator_,
                    "features": features,
                    "supports_predict_proba": True
                }

                path = f"{model_folder}/XGB-{features}.joblib"
                joblib.dump(xgb_gs.best_estimator_, path)

                dict_models_save_infos[f"XGB-{features}"] = {
                    "path": path,
                    "features": features
                }

                # Train Linear SVM/SVC (with appropriate grid)
                print(f"Training LinearSVM (LinearSVC) - {features}")

                linsvm = LinearSVC(
                    # max_iter=5000,
                    max_iter=10000,
                    random_state=42,
                )

                linsvm_grid = {
                    # "C": [0.5, 1.0, 2.0, 4.0],
                    "C": [0.1, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0],
                    "class_weight": [None, "balanced"],
                }

                linsvm_gs = GridSearchCV(
                    estimator=linsvm,
                    param_grid=linsvm_grid,
                    scoring=scorer,
                    cv=cv,
                    n_jobs=-1,
                    verbose=1,
                )

                linsvm_gs.fit(x_train, y_train)
                dict_models[f"LinearSVM-{features}"] = {
                    "model": linsvm_gs.best_estimator_,
                    "features": features,
                    "supports_predict_proba": False
                }

                path = f"{model_folder}/LinearSVM-{features}.joblib"
                joblib.dump(linsvm_gs.best_estimator_, path)

                dict_models_save_infos[f"LinearSVM-{features}"] = {
                    "path": path,
                    "features": features
                }
                

                # Train Ridge (with appropriate grid)
                print(f"Training Ridge - {features}")

                ridge = RidgeClassifier(
                    random_state=42,
                )

                ridge_grid = {
                    # "alpha": [0.1, 1.0, 10.0],
                    "alpha": [0.01, 0.1, 1.0, 10.0, 50.0],
                    "class_weight": [None, "balanced"],
                }

                ridge_gs = GridSearchCV(
                    estimator=ridge,
                    param_grid=ridge_grid,
                    scoring=scorer,
                    cv=cv,
                    n_jobs=-1,
                    verbose=1,
                )

                ridge_gs.fit(x_train, y_train)
                dict_models[f"Ridge-{features}"] = {
                    "model": ridge_gs.best_estimator_,
                    "features": features,
                    "supports_predict_proba": False
                }

                path = f"{model_folder}/Ridge-{features}.joblib"
                joblib.dump(ridge_gs.best_estimator_, path)

                dict_models_save_infos[f"Ridge-{features}"] = {
                    "path": path,
                    "features": features
                }
                
            with open(f"{folder_name}/models-infos.json", "w", encoding="utf-8") as f:
                json.dump(dict_models_save_infos, f, indent=2, ensure_ascii=False)


            # Testing:
            test_binary_flags, dict_for_model_test_loop = prepare_infos_testing_and_training(
                the_dataset=test_dataset,
                dimensions=dimensions,
                embedding_model=embed_model,
                tokenizer_model=embed_model
            )

            y_test = np.array(test_binary_flags)

            dict_results = {}

            # dict_eval_p_vals = {} # For Permutation test

            for model_name, model_infos in dict_models.items():
                model = model_infos["model"]
                features = model_infos["features"]

                x_test = np.array(dict_for_model_test_loop[features])

                time_start_predict = time.time()
                predictions = model.predict(x_test)
                time_end_predict = time.time()

                time_predict = time_end_predict - time_start_predict

                dict_results[model_name] = {
                    "balanced_accuracy": balanced_accuracy_score(y_test, predictions),
                    "precision": precision_score(y_test, predictions, zero_division=0),
                    "recall": recall_score(y_test, predictions, zero_division=0),
                    "f1": f1_score(y_test, predictions, zero_division=0),
                    "prediction time": time_predict
                }

                # Permutation test
                # score, perm_scores, pvalue = permutation_test_score(
                #     estimator=model,
                #     X=x_test,
                #     y=y_test,
                #     scoring="balanced_accuracy",
                #     # n_permutations=500,
                #     n_permutations=50,
                #     random_state=42
                # )

                # dict_eval_p_vals[model_name] = {
                #     "BA": score,
                #     "p value": pvalue,
                #     "max_perm_ba": float(np.max(perm_scores)),
                #     "min_perm_ba": float(np.min(perm_scores)),
                #     "median_perm_ba": float(np.median(perm_scores)),
                #     "mean_perm_ba": float(np.mean(perm_scores)),
                #     "nbr permutations": 50
                # }

            dict_results_sorted = dict(
                sorted(dict_results.items(), key=lambda x: x[1]["balanced_accuracy"], reverse=True)
            )

            # dict_eval_p_vals_sorted = dict(
            #     sorted(dict_eval_p_vals.items(), key=lambda x: x[1]["BA"], reverse=True)
            # )

            results_folder = f"{folder_name}/results"
            os.makedirs(results_folder, exist_ok=True)

            with open(f"{results_folder}/models-performance.json", "w", encoding="utf-8") as f:
                json.dump(dict_results_sorted, f, indent=2, ensure_ascii=False)

            # with open(f"{results_folder}/models-permutation-test.json", "w", encoding="utf-8") as f:
            #     json.dump(dict_eval_p_vals_sorted, f, indent=2, ensure_ascii=False)

            dimension_time_end = time.time()
            dimension_exec_time = dimension_time_end - dimension_time_start

            best_performer = next(iter(dict_results_sorted))
            best_performer_BA = dict_results_sorted[best_performer]["balanced_accuracy"]

            print(f"Full Execution finished for {dimensions} dimensions with embedding model {embed_model} (took {dimension_exec_time} seconds). Best Performer : {best_performer} ; Balanced Accuracy : {best_performer_BA}")


        end_time_model = time.time()

        exec_time_model = end_time_model -start_time_model

        print(f"Full Execution finished for all dimensions with embedding model {embed_model}. Took {exec_time_model} seconds.")


    print("Testing with the LLM now.")
    pref_LLM = test_gpt_4o_perf(test_dataset)

    folder_name = f"{root_folder}/LLM-Decision"
    os.makedirs(folder_name, exist_ok=True)

    with open(f"{folder_name}/LLM-performance.json", "w", encoding="utf-8") as f:
        json.dump(pref_LLM, f, indent=2, ensure_ascii=False)

    end_time = time.time()

    full_exec_time = end_time - start_time

    print(f"Full Execution finished for all dimensions and models. Took {full_exec_time} seconds.")



if __name__ == "__main__":
    train_dataset_path = input("Train Dataset Path : ")
    test_dataset_path = input("Test Dataset Path: ")

    add_to_folder_name = input("Information to add to folder name : ")

    with open(train_dataset_path, "r", encoding="utf-8") as f:
        train_dataset = json.load(f)

    with open(test_dataset_path, "r", encoding="utf-8") as f:
        test_dataset = json.load(f)