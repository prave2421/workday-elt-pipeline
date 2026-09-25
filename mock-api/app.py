"""
Mock Workday API — FastAPI service simulating Workday HCM endpoints.

Features:
  - Pagination (offset/limit with total count)
  - updated_since filter for incremental extracts
  - Nested JSON matching Workday response style
  - POST /simulate to generate workforce changes
"""

from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Query
from data_generator import workforce, DEPARTMENTS, POSITIONS

app = FastAPI(
    title="Mock Workday API",
    description="Simulates Workday HCM endpoints for ELT pipeline testing",
    version="1.0.0",
)


@app.on_event("startup")
def startup():
    """Generate initial workforce on startup."""
    workforce.initialize(num_workers=50)


def paginate(data: list, offset: int, limit: int) -> dict:
    """Workday-style paginated response."""
    total = len(data)
    page = data[offset: offset + limit]
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": (offset + limit) < total,
        "data": page,
    }


def filter_by_updated_since(records: list, updated_since: Optional[str]) -> list:
    """Filter records updated after the given timestamp."""
    if not updated_since:
        return records

    cutoff = datetime.fromisoformat(updated_since)
    filtered = []
    for r in records:
        updated_at = r.get("updated_at") or r.get("created_at", "")
        if updated_at and datetime.fromisoformat(updated_at) >= cutoff:
            filtered.append(r)
    return filtered


# --- Endpoints ---

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "worker_count": len(workforce.workers),
        "active_workers": sum(
            1 for w in workforce.workers.values()
            if w["employment_data"]["status"] == "Active"
        ),
    }


@app.get("/workers")
def get_workers(
    updated_since: Optional[str] = Query(None, description="ISO timestamp filter"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Get worker records with nested personal, employment, and position data."""
    workers = list(workforce.workers.values())
    workers = filter_by_updated_since(workers, updated_since)
    workers.sort(key=lambda w: w.get("updated_at", ""), reverse=True)
    return paginate(workers, offset, limit)


@app.get("/positions")
def get_positions(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Get position catalog."""
    positions = [
        {**p, "created_at": datetime.utcnow().isoformat(),
         "updated_at": datetime.utcnow().isoformat()}
        for p in POSITIONS
    ]
    return paginate(positions, offset, limit)


@app.get("/organizations")
def get_organizations(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Get organization hierarchy."""
    orgs = [
        {**o, "created_at": datetime.utcnow().isoformat(),
         "updated_at": datetime.utcnow().isoformat()}
        for o in DEPARTMENTS
    ]
    return paginate(orgs, offset, limit)


@app.get("/compensation")
def get_compensation(
    updated_since: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Get compensation records."""
    records = filter_by_updated_since(workforce.compensation_records, updated_since)
    records.sort(key=lambda r: r.get("updated_at", ""), reverse=True)
    return paginate(records, offset, limit)


@app.get("/time_off")
def get_time_off(
    updated_since: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Get time off / leave records."""
    records = filter_by_updated_since(workforce.time_off_records, updated_since)
    records.sort(key=lambda r: r.get("updated_at", ""), reverse=True)
    return paginate(records, offset, limit)


@app.get("/job_changes")
def get_job_changes(
    updated_since: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Get job change history — promotions, transfers, hires, terminations."""
    records = filter_by_updated_since(workforce.job_changes, updated_since)
    records.sort(key=lambda r: r.get("updated_at", ""), reverse=True)
    return paginate(records, offset, limit)


@app.post("/simulate")
def simulate_changes(num_events: int = Query(10, ge=1, le=50)):
    """
    Simulate workforce changes: hires, terminations, promotions, transfers, time_off.
    Call this between pipeline runs to generate new data for incremental loads.
    """
    events = workforce.simulate_changes(num_events)
    return {
        "events_generated": len(events),
        "events": events,
        "workforce_size": len(workforce.workers),
        "active_count": sum(
            1 for w in workforce.workers.values()
            if w["employment_data"]["status"] == "Active"
        ),
    }
