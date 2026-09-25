"""
Paginated client for the Mock Workday API.
Handles pagination, incremental extraction via updated_since, and writes JSON to landing.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

API_BASE_URL = os.environ.get("WORKDAY_API_URL", "http://mock-workday-api:8000")
LANDING_PATH = "/opt/airflow/data/landing"
PAGE_SIZE = 50


def extract_endpoint(
    endpoint: str,
    load_date: str,
    updated_since: Optional[str] = None,
) -> str:
    """
    Extract all records from a Workday API endpoint with pagination.

    Args:
        endpoint: API endpoint name (workers, positions, etc.)
        load_date: YYYY-MM-DD for partitioning
        updated_since: ISO timestamp for incremental pulls

    Returns:
        Path to output directory
    """
    output_dir = Path(LANDING_PATH) / endpoint / f"load_date={load_date}"
    output_dir.mkdir(parents=True, exist_ok=True)

    all_records = []
    offset = 0
    total = None

    while True:
        params = {"offset": offset, "limit": PAGE_SIZE}
        if updated_since:
            params["updated_since"] = updated_since

        url = f"{API_BASE_URL}/{endpoint}"
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        records = data.get("data", [])
        total = data.get("total", 0)
        has_more = data.get("has_more", False)

        all_records.extend(records)
        print(f"  [{endpoint}] Fetched {len(records)} records (offset={offset}, total={total})")

        if not has_more or not records:
            break

        offset += PAGE_SIZE

    # Write to landing
    output_file = output_dir / f"{endpoint}_{load_date}.json"
    with open(output_file, "w") as f:
        json.dump(all_records, f, indent=2)

    print(f"  [{endpoint}] Total: {len(all_records)} records → {output_file}")
    return str(output_dir)


def simulate_changes(num_events: int = 10) -> dict:
    """Trigger change simulation on the mock API."""
    url = f"{API_BASE_URL}/simulate"
    response = requests.post(url, params={"num_events": num_events}, timeout=30)
    response.raise_for_status()
    result = response.json()
    print(f"  Simulated {result['events_generated']} events. "
          f"Workforce: {result['workforce_size']} total, {result['active_count']} active")
    return result
