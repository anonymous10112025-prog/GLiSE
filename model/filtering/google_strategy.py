"""
Filtering strategy for Google Search.
"""

import numpy as np
from typing import List, Dict, Tuple
from model.filtering.base_strategy import FilteringStrategy


class GoogleFilteringStrategy(FilteringStrategy):
    """Filtering strategy for Google search results."""
    
    def filter_small(self, results: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Filter using text-embedding-3-small model."""
        dimensions = 512
        embed_model = "text-embedding-3-small"
        ml_model = self.load_model(
            "models-ml/google/text-embedding-3-small/GaussianNB-differences.joblib"
        )
        
        # Prepare texts for embedding
        texts_to_embed = []
        for google_res_infos in results:
            texts_to_embed.append(self.safe_non_empty_string_field_access("search_intent", google_res_infos))
            texts_to_embed.append(self.safe_non_empty_string_field_access("title", google_res_infos))
            texts_to_embed.append(self.safe_non_empty_string_field_access("snippet", google_res_infos))
            texts_to_embed.append(
                self.clean_html_for_embedding(
                    self.safe_non_empty_string_field_access("html_snippet", google_res_infos)
                )
            )
            texts_to_embed.append(self.safe_non_empty_string_field_access("meta_desc", google_res_infos))
            texts_to_embed.append(self.safe_non_empty_string_field_access("schema_desc", google_res_infos))
            texts_to_embed.append(self.safe_non_empty_string_field_access("url", google_res_infos))
        
        # Get embeddings
        all_embeddings = self.make_call_embeddings(
            texts=texts_to_embed,
            dimensions=dimensions,
            embedding_model=embed_model
        )
        
        # Compute features
        ml_inputs = []
        index = 0
        for _ in results:
            search_intent_embedding = all_embeddings[index]
            title_embedding = all_embeddings[index + 1]
            snippet_embedding = all_embeddings[index + 2]
            html_snippet_embedding = all_embeddings[index + 3]
            meta_desc_embedding = all_embeddings[index + 4]
            schema_desc_embedding = all_embeddings[index + 5]
            url_embedding = all_embeddings[index + 6]
            
            # Differences
            differences = (
                self.difference_vector(search_intent_embedding, title_embedding).tolist() +
                self.difference_vector(search_intent_embedding, snippet_embedding).tolist() +
                self.difference_vector(search_intent_embedding, html_snippet_embedding).tolist() +
                self.difference_vector(search_intent_embedding, meta_desc_embedding).tolist() +
                self.difference_vector(search_intent_embedding, schema_desc_embedding).tolist() +
                self.difference_vector(search_intent_embedding, url_embedding).tolist()
            )
            
            ml_inputs.append(differences)
            index += 7
        
        # Predict
        x_for_pred = np.array(ml_inputs)
        prediction = ml_model.predict(x_for_pred)
        proba_pred = ml_model.predict_proba(x_for_pred)[:, 1]
        
        # Separate and sort results
        return self._separate_and_sort_results(results, prediction, proba_pred)
    
    def filter_large(self, results: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Filter using text-embedding-3-large model."""
        dimensions = 1536
        embed_model = "text-embedding-3-large"
        ml_model = self.load_model(
            "models-ml/google/text-embedding-3-large/GaussianNB-differences.joblib"
        )
        
        # Prepare texts for embedding
        texts_to_embed = []
        for google_res_infos in results:
            texts_to_embed.append(self.safe_non_empty_string_field_access("search_intent", google_res_infos))
            texts_to_embed.append(self.safe_non_empty_string_field_access("title", google_res_infos))
            texts_to_embed.append(self.safe_non_empty_string_field_access("snippet", google_res_infos))
            texts_to_embed.append(
                self.clean_html_for_embedding(
                    self.safe_non_empty_string_field_access("html_snippet", google_res_infos)
                )
            )
            texts_to_embed.append(self.safe_non_empty_string_field_access("meta_desc", google_res_infos))
            texts_to_embed.append(self.safe_non_empty_string_field_access("schema_desc", google_res_infos))
            texts_to_embed.append(self.safe_non_empty_string_field_access("url", google_res_infos))
        
        # Get embeddings
        all_embeddings = self.make_call_embeddings(
            texts=texts_to_embed,
            dimensions=dimensions,
            embedding_model=embed_model
        )
        
        # Compute features
        ml_inputs = []
        index = 0
        for _ in results:
            search_intent_embedding = all_embeddings[index]
            title_embedding = all_embeddings[index + 1]
            snippet_embedding = all_embeddings[index + 2]
            html_snippet_embedding = all_embeddings[index + 3]
            meta_desc_embedding = all_embeddings[index + 4]
            schema_desc_embedding = all_embeddings[index + 5]
            url_embedding = all_embeddings[index + 6]
            
            # Differences
            differences = (
                self.difference_vector(search_intent_embedding, title_embedding).tolist() +
                self.difference_vector(search_intent_embedding, snippet_embedding).tolist() +
                self.difference_vector(search_intent_embedding, html_snippet_embedding).tolist() +
                self.difference_vector(search_intent_embedding, meta_desc_embedding).tolist() +
                self.difference_vector(search_intent_embedding, schema_desc_embedding).tolist() +
                self.difference_vector(search_intent_embedding, url_embedding).tolist()
            )
            
            ml_inputs.append(differences)
            index += 7
        
        # Predict
        x_for_pred = np.array(ml_inputs)
        prediction = ml_model.predict(x_for_pred)
        proba_pred = ml_model.predict_proba(x_for_pred)[:, 1]
        
        # Separate and sort results
        return self._separate_and_sort_results(results, prediction, proba_pred)
    
    @staticmethod
    def _separate_and_sort_results(
        results: List[Dict],
        predictions,
        probabilities
    ) -> Tuple[List[Dict], List[Dict]]:
        """Separate results into relevant/irrelevant and sort by probability."""
        relevant_list = []
        irrelevant_list = []
        
        for result, pred_label, pred_proba in zip(results, predictions, probabilities):
            entry = result.copy()
            entry["relevant"] = bool(pred_label)
            entry["relevant_proba"] = float(pred_proba)
            
            if pred_label == 1:
                relevant_list.append(entry)
            else:
                irrelevant_list.append(entry)
        
        # Sort by probability descending
        relevant_list.sort(key=lambda x: x["relevant_proba"], reverse=True)
        irrelevant_list.sort(key=lambda x: x["relevant_proba"], reverse=True)
        
        return relevant_list, irrelevant_list
