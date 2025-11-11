"""
queries_generate_split.py
Script 1: generate search queries from a prompt.
Produces two separate CSVs:
  - queries_code.csv  for StackOverflow, GitHub Code, GitHub Issues/PRs
  - queries_google.csv for Google (docs and gray literature)
"""

import os
import sys
import csv
import argparse
from typing import List

from model.GLProvider import GLProvider
from model.LLMProvider import LLMProvider

def parse_args():
    model_choices = LLMProvider.get_model_choices()

    ap = argparse.ArgumentParser(description="Generate queries and save two CSVs")
    ap.add_argument("--intent", type=str, required=False, help="Search intent in natural language")
    ap.add_argument("--platforms", nargs="*", default=None, help="so gh_code gh_issues google. Default if not provided: all.")
    ap.add_argument("--languages", nargs="*", default=None, help="Languages. Default if not provided: all")
    ap.add_argument("--n", type=int, default=10, help="Number of queries per platform (Google will auto-split 50/50 between docs and gray literature)")
    ap.add_argument("--model", type=str, default=os.getenv("QUERY_DEFAULT_MODEL"), choices=model_choices.split(",") if model_choices else None,
                    help=f"LLM model to use. Available: {', '.join(model_choices.split(','))}" if model_choices else "LLM model to use.   No restrictions.")
    return ap.parse_args()

def interactive_prompt(prompt: str) -> str:
    try:
        return input(prompt)
    except EOFError:
        return ""

def save_queries_to_csv(filename: str, lines: List[str]):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Category", "Platform", "Query"])
        for ln in lines:
            try:
                cat, plat, q = ln.split(",", 2)
                w.writerow([cat, plat, q.strip('"')])
            except ValueError:
                continue

def generate_queries(model: str, system_prompt: str, temperature: float, intent: str, platforms: List[str], languages: List[str],
                     general_n: int, from_date: str = None, to_date: str = None,
                     progress_callback=None, start_callback=None, 
                     cancel_check=None) -> dict:
    """
    Generate queries for multiple platforms.
    
    Args:
        model: LLM model name
        system_prompt: System prompt for LLM
        temperature: Temperature setting
        intent: Search intent
        platforms: List of platform IDs
        languages: List of language codes
        general_n: Number of queries per platform
        progress_callback: Optional callback function(source_id, source_name, queries) called after each source completes
        start_callback: Optional callback function(source_id, source_name) called before starting each source
        cancel_check: Optional function that returns True if user requested cancellation
    
    Returns:
        Dictionary mapping source_id to list of query strings
    """
    
    llm_provider = LLMProvider(model=model, system_prompt=system_prompt, temperature=temperature)
    results = {}

    gl_providers_registry = GLProvider.get_providers_list()
    
    for plat in platforms:
        # Check if user requested cancellation
        if cancel_check and cancel_check():
            break
        
        provider = gl_providers_registry.get(plat)
        if not provider:
            print(f"Warning: No provider found for platform id '{plat}'. Skipping.", file=sys.stderr)
            continue
        
        # Notify that we're starting this source
        if start_callback:
            start_callback(plat, provider.name)

        try:
            queries = provider.generateQueries(
                llm_provider=llm_provider,
                intent=intent,
                queries_number=general_n,
                languages=languages,
                from_date=from_date,
                to_date=to_date
            )

            # Store results
            results[plat] = queries

            # Call progress callback if provided
            if progress_callback:
                progress_callback(plat, provider.name, queries)

        except Exception as e:
            print(f"Error generating queries for {provider.name}: {e}", file=sys.stderr)
            results[plat] = []
            if progress_callback:
                progress_callback(plat, provider.name, [])
    
    return results

def main():
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY is not set.", file=sys.stderr)
        sys.exit(1)

    args = parse_args()
    intent = args.intent or interactive_prompt("Describe your need: ").strip()
    if not intent:
        print("No intent provided. Aborting.", file=sys.stderr)
        sys.exit(2)

    results = generate_queries(
        model=args.model or os.getenv("DEFAULT_MODEL"),
        system_prompt=os.getenv("SYSTEM_PROMPT", ""),
        temperature=float(os.getenv("TEMPERATURE", "0.2")),
        intent=intent,
        platforms=args.platforms if args.platforms not in (None, [], ["all"]) else ["so", "gh_code", "gh_issues", "google"],
        languages=args.languages if args.languages not in (None, [], ["all"]) else ["all"],
        general_n=args.n
    )

    # Convert results to CSV format
    code_lines = []
    google_lines = []
    gl_providers_registry = GLProvider.get_providers_list()
    
    for plat, queries in results.items():
        provider = gl_providers_registry.get(plat)
        provider_name = provider.name if provider else plat
        
        if plat == "google":
            for q in queries:
                google_lines.append(f"{plat},{provider_name},\"{q}\"")
        else:
            for q in queries:
                code_lines.append(f"{plat},{provider_name},\"{q}\"")
    
    for ln in code_lines + google_lines:
        print(ln)
    
    save_queries_to_csv("queries_code.csv", code_lines)
    save_queries_to_csv("queries_google.csv", google_lines)

    print("Saved queries_code.csv and queries_google.csv")

if __name__ == "__main__":
    main()
