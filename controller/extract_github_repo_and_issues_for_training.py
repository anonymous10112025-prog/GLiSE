import json
from pathlib import Path

# ---------------------
#  IMPORT YOUR MODULES
# ---------------------
from model.providers import get_provider
from model.LLMProvider import LLMProvider
from model.Settings import get_settings


# ---------------------
#  HELPERS
# ---------------------

def load_json_if_exists(path: str):
    """Return JSON list if file exists; otherwise return empty list."""
    p = Path(path)
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_json(data, path: str):
    """Write data to JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def append_results(existing: list, new_results: list):
    """
    Extend existing results while ensuring duplicates only if BOTH URI and intent match.
    We assume each result has: 
      result["url"] (or "html_url" depending on the API)
      result["search_intent"]
    """
    indexed = {(r.get("url"), r.get("search_intent")) for r in existing}

    for r in new_results:
        tup = (r.get("url"), r.get("search_intent"))
        if tup not in indexed:
            existing.append(r)
            indexed.add(tup)

    return existing


def normalize_url(result_item: dict, fallback_key="html_url"):
    """
    Normalize URL key. 
    GitHub search results sometimes store URL under "html_url" or "url".
    We enforce "url".
    """
    if "url" not in result_item:
        if fallback_key in result_item:
            result_item["url"] = result_item.get(fallback_key)
        else:
            result_item["url"] = None
    return result_item


# ---------------------
#  MAIN
# ---------------------
def main():
    # Get settings
    settings = get_settings()

    # Input JSON file path
    json_path = input("Enter path to the search-intent JSON file: ").strip()
    json_out = input("Enter path to JSON file to store results: ").strip()
    source_provider = input("Enter the provider ID (so, gh_repos, gh_issues, google): ").strip()
    max_per_request = int(input("Enter max results per request: ").strip())
    nbr_queries = int(input("Enter number of queries to generate: ").strip())
    
    # LLM configuration
    llm_model = input("Enter LLM model to use (default: gpt-4o): ").strip() or "gpt-4o"
    system_prompt = "You are a helpful assistant that generates search queries for grey literature research."

    if not Path(json_path).exists():
        print(f"ERROR: File not found: {json_path}")
        return

    # Load search-intent JSON
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    intents = data.get("search intent", [])
    if not intents:
        print("No search intent found.")
        return

    print(f"Loaded {len(intents)} search intents.")

    # Pre-load existing results (append mode)
    existing_results = load_json_if_exists(json_out)
    
    # Initialize LLM provider
    llm_provider = LLMProvider(model=llm_model, system_prompt=system_prompt, temperature=0.7)
    
    # Get the search provider
    try:
        provider = get_provider(source_provider)
        print(f"\nUsing provider: {provider.name}")
    except ValueError as e:
        print(f"ERROR: {e}")
        print("Valid provider IDs: so, gh_repos, gh_issues, google")
        return

    # Iterate over search intents
    for intent in intents:
        print(f"\n=== Intent: {intent}")
        
        # Generate queries using the provider
        try:
            if source_provider == "google":
                # Google needs doc and gray numbers
                doc_n = int(nbr_queries / 2)
                gray_n = nbr_queries - doc_n
                queries = provider.generate_queries(
                    llm_provider=llm_provider,
                    intent=intent,
                    queries_number=nbr_queries,
                    languages=None,
                    documentation_queries_number=doc_n,
                    gl_queries_number=gray_n
                )
            else:
                queries = provider.generate_queries(
                    llm_provider=llm_provider,
                    intent=intent,
                    queries_number=nbr_queries,
                    languages=None,
                    documentation_queries_number=None,
                    gl_queries_number=None
                )
            
            print(f"Generated {len(queries)} queries")
            
            # Execute searches for each query
            for q in queries:
                print(f"[Query] {q}")
                search_results = provider.search(q, max_per_request)
                print(f"  → {len(search_results)} results found")

                # Prepare results for storage
                to_store = []
                for item in search_results:
                    item = normalize_url(item)
                    record = {
                        **item,
                        "search_intent": intent,
                        "query": q,
                        "Grade": 0,
                        "Rated": False
                    }
                    to_store.append(record)

                existing_results = append_results(existing_results, to_store)
                
        except Exception as e:
            print(f"ERROR processing intent '{intent}': {e}")
            continue

    # Save results
    save_json(existing_results, json_out)

    print("\n✅ DONE")
    print(f"Total results: {len(existing_results)}")
    print(f"Results stored in: {json_out}")


if __name__ == "__main__":
    main()
