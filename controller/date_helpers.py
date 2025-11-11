"""
Date helper utilities for converting and validating date ranges across different provider APIs.
"""

from datetime import datetime, date, timezone
from typing import Optional, Tuple, List, Dict
import re

ISO_DATE_FORMAT = "%Y-%m-%d"
GOOGLE_SNIPPET_DATE_FORMAT = "%b %d, %Y"  # e.g., "Aug 12, 2024"


def parse_iso_date(iso_str: str) -> date:
    """
    Parse an ISO date string (YYYY-MM-DD) into a date object.
    
    Args:
        iso_str: Date string in YYYY-MM-DD format
        
    Returns:
        date object
        
    Raises:
        ValueError: If the date string is invalid
    """
    return datetime.strptime(iso_str, ISO_DATE_FORMAT).date()


def to_unix_epoch_seconds(iso_str: str, end_of_day: bool = False) -> int:
    """
    Convert an ISO date string to Unix epoch seconds (UTC).
    
    Args:
        iso_str: Date string in YYYY-MM-DD format
        end_of_day: If True, returns timestamp for 23:59:59 of that day
        
    Returns:
        Unix epoch seconds (integer)
    """
    d = parse_iso_date(iso_str)
    if end_of_day:
        dt = datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc)
    else:
        dt = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc)
    return int(dt.timestamp())


def validate_date_range(from_date: Optional[str], to_date: Optional[str]) -> Tuple[bool, str]:
    """
    Validate a date range.
    
    Args:
        from_date: Start date in YYYY-MM-DD format or None
        to_date: End date in YYYY-MM-DD format or None
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not from_date and not to_date:
        return True, ""
    
    try:
        if from_date:
            f = parse_iso_date(from_date)
        if to_date:
            t = parse_iso_date(to_date)
        
        if from_date and to_date and f > t:
            return False, "From date must be earlier than or equal to To date"
        
        return True, ""
    except ValueError as e:
        return False, f"Invalid date format: {e}"


def parse_google_snippet_date(snippet: str) -> Optional[date]:
    """
    Extract and parse date from Google search snippet.
    
    Google snippets often start with dates in format "Aug 12, 2024 ..." or "Mar 4, 2020 ..."
    
    Args:
        snippet: Google search result snippet text
        
    Returns:
        date object if found and parsed successfully, None otherwise
    """
    if not snippet:
        return None
    
    # Pattern to match dates like "Aug 12, 2024" or "Mar 4, 2020" at the start
    # Format: Month(3 letters) Day(1-2 digits), Year(4 digits)
    pattern = r'^([A-Z][a-z]{2})\s+(\d{1,2}),\s+(\d{4})'
    match = re.match(pattern, snippet.strip())
    
    if match:
        try:
            date_str = f"{match.group(1)} {match.group(2)}, {match.group(3)}"
            return datetime.strptime(date_str, GOOGLE_SNIPPET_DATE_FORMAT).date()
        except ValueError:
            return None
    
    return None


def filter_google_results_by_date(
    results: List[Dict],
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> List[Dict]:
    """
    Filter Google search results by date range using snippet dates.
    
    Google snippets often start with dates in format "Aug 12, 2024 ..."
    This function extracts those dates and filters results accordingly.
    
    Args:
        results: List of Google result dictionaries with 'snippet' field
        from_date: Start date in YYYY-MM-DD format or None
        to_date: End date in YYYY-MM-DD format or None
        
    Returns:
        Filtered list of results
    """
    if not from_date and not to_date:
        return results
    
    f = parse_iso_date(from_date) if from_date else None
    t = parse_iso_date(to_date) if to_date else None
    
    print(f"[Filter] Date range: {f} to {t}")
    
    filtered = []
    dates_found = 0
    dates_excluded = 0
    
    for idx, result in enumerate(results):
        result_date = None
        
        # Try to extract date from snippet first
        snippet = result.get("snippet", "")
        result_date = parse_google_snippet_date(snippet)
        
        # If no date in snippet, try html_snippet
        if not result_date:
            html_snippet = result.get("html_snippet", "")
            result_date = parse_google_snippet_date(html_snippet)
        
        if result_date:
            dates_found += 1
            print(f"[Filter] Result {idx+1}: date={result_date}, snippet='{snippet[:50]}...'")
        
        # Apply filter
        if result_date:
            if f and result_date < f:
                print(f"[Filter]   -> Excluded (before {f})")
                dates_excluded += 1
                continue
            if t and result_date > t:
                print(f"[Filter]   -> Excluded (after {t})")
                dates_excluded += 1
                continue
            print(f"[Filter]   -> Included")
        else:
            print(f"[Filter] Result {idx+1}: NO DATE FOUND, including by default")
        
        filtered.append(result)
    
    print(f"[Filter] Summary: {dates_found}/{len(results)} had dates, {dates_excluded} excluded, {len(filtered)} remaining")
    
    return filtered


def filter_results_by_date(
    results: List[Dict],
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    date_field_candidates: Tuple[str, ...] = ("created_at", "creation_date", "published", "date")
) -> List[Dict]:
    """
    Client-side filter for results by date range.
    
    Use this for providers that don't support server-side date filtering.
    
    Args:
        results: List of result dictionaries
        from_date: Start date in YYYY-MM-DD format or None
        to_date: End date in YYYY-MM-DD format or None
        date_field_candidates: Tuple of field names to check for dates (in priority order)
        
    Returns:
        Filtered list of results
    """
    if not from_date and not to_date:
        return results
    
    f = parse_iso_date(from_date) if from_date else None
    t = parse_iso_date(to_date) if to_date else None
    
    filtered = []
    for result in results:
        result_date = None
        
        # Try to extract date from result
        for field in date_field_candidates:
            if field in result and result[field]:
                try:
                    value = result[field]
                    if isinstance(value, int):
                        # Unix epoch seconds
                        result_date = datetime.utcfromtimestamp(value).date()
                    elif isinstance(value, str):
                        # ISO timestamp or similar
                        # Handle both with and without timezone
                        value_clean = value.replace("Z", "+00:00")
                        result_date = datetime.fromisoformat(value_clean).date()
                    break
                except (ValueError, OSError):
                    continue
        
        # Apply filter
        if result_date:
            if f and result_date < f:
                continue
            if t and result_date > t:
                continue
        # If no date found, include the result (policy: don't exclude unknowns)
        
        filtered.append(result)
    
    return filtered
