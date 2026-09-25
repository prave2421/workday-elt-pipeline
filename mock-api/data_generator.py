"""
Workday-style workforce data generator using Faker.
Generates realistic HR data with nested JSON structures.
Supports change simulation: hires, terminations, promotions, transfers.
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import Optional

from faker import Faker

fake = Faker()
Faker.seed(42)

# --- Reference data ---
DEPARTMENTS = [
    {"id": "ORG001", "name": "Engineering", "parent_id": None, "type": "Department"},
    {"id": "ORG002", "name": "Product", "parent_id": None, "type": "Department"},
    {"id": "ORG003", "name": "Sales", "parent_id": None, "type": "Department"},
    {"id": "ORG004", "name": "HR", "parent_id": None, "type": "Department"},
    {"id": "ORG005", "name": "Finance", "parent_id": None, "type": "Department"},
    {"id": "ORG006", "name": "Backend Engineering", "parent_id": "ORG001", "type": "Team"},
    {"id": "ORG007", "name": "Frontend Engineering", "parent_id": "ORG001", "type": "Team"},
    {"id": "ORG008", "name": "Data Engineering", "parent_id": "ORG001", "type": "Team"},
    {"id": "ORG009", "name": "Enterprise Sales", "parent_id": "ORG003", "type": "Team"},
    {"id": "ORG010", "name": "SMB Sales", "parent_id": "ORG003", "type": "Team"},
]

POSITIONS = [
    {"id": "POS001", "title": "Software Engineer", "level": "IC3", "family": "Engineering"},
    {"id": "POS002", "title": "Senior Software Engineer", "level": "IC4", "family": "Engineering"},
    {"id": "POS003", "title": "Staff Engineer", "level": "IC5", "family": "Engineering"},
    {"id": "POS004", "title": "Engineering Manager", "level": "M1", "family": "Engineering"},
    {"id": "POS005", "title": "Product Manager", "level": "IC4", "family": "Product"},
    {"id": "POS006", "title": "Senior Product Manager", "level": "IC5", "family": "Product"},
    {"id": "POS007", "title": "Sales Representative", "level": "IC3", "family": "Sales"},
    {"id": "POS008", "title": "Senior Sales Rep", "level": "IC4", "family": "Sales"},
    {"id": "POS009", "title": "HR Business Partner", "level": "IC4", "family": "HR"},
    {"id": "POS010", "title": "Financial Analyst", "level": "IC3", "family": "Finance"},
    {"id": "POS011", "title": "Data Engineer", "level": "IC3", "family": "Engineering"},
    {"id": "POS012", "title": "Senior Data Engineer", "level": "IC4", "family": "Engineering"},
    {"id": "POS013", "title": "Director of Engineering", "level": "M2", "family": "Engineering"},
    {"id": "POS014", "title": "VP of Sales", "level": "M3", "family": "Sales"},
]

LOCATIONS = ["New York", "San Francisco", "Austin", "London", "Toronto", "Remote"]
EMPLOYMENT_TYPES = ["Full-Time", "Part-Time", "Contract"]
COMPENSATION_TYPES = ["Salary", "Hourly"]
CURRENCIES = ["USD", "GBP", "CAD"]
TIME_OFF_TYPES = ["PTO", "Sick", "Parental", "Bereavement", "Unpaid"]
CHANGE_REASONS = [
    "Promotion", "Transfer", "Reorganization", "Merit Increase",
    "New Hire", "Voluntary Termination", "Involuntary Termination",
    "Retirement", "Lateral Move",
]

SALARY_RANGES = {
    "IC3": (75000, 120000),
    "IC4": (110000, 170000),
    "IC5": (150000, 230000),
    "M1": (140000, 200000),
    "M2": (180000, 260000),
    "M3": (220000, 350000),
}


class WorkforceState:
    """Maintains in-memory state of the workforce for change simulation."""

    def __init__(self):
        self.workers: dict = {}
        self.job_changes: list = []
        self.compensation_records: list = []
        self.time_off_records: list = []
        self._initialized = False

    def initialize(self, num_workers: int = 50):
        """Generate initial workforce."""
        if self._initialized:
            return

        for _ in range(num_workers):
            worker = self._create_worker()
            self.workers[worker["worker_id"]] = worker

            # Initial hire job change
            self.job_changes.append(self._create_job_change(
                worker_id=worker["worker_id"],
                change_type="New Hire",
                effective_date=worker["hire_date"],
                new_position_id=worker["current_position"]["position_id"],
                new_org_id=worker["current_position"]["organization_id"],
            ))

            # Initial compensation
            self.compensation_records.append(self._create_compensation(
                worker_id=worker["worker_id"],
                effective_date=worker["hire_date"],
                position_level=worker["current_position"]["level"],
            ))

        self._initialized = True

    def _create_worker(self, hire_date: Optional[datetime] = None) -> dict:
        """Generate a single worker with nested Workday-style structure."""
        worker_id = f"WKR-{uuid.uuid4().hex[:8].upper()}"
        position = random.choice(POSITIONS)
        org = random.choice(DEPARTMENTS)
        location = random.choice(LOCATIONS)

        if hire_date is None:
            hire_date = fake.date_between(start_date="-3y", end_date="-30d")

        now = datetime.utcnow()

        return {
            "worker_id": worker_id,
            "personal_data": {
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "email": fake.company_email(),
                "phone": fake.phone_number(),
                "date_of_birth": str(fake.date_of_birth(minimum_age=22, maximum_age=65)),
                "gender": random.choice(["Male", "Female", "Non-Binary"]),
                "nationality": fake.country(),
            },
            "employment_data": {
                "employment_type": random.choice(EMPLOYMENT_TYPES),
                "status": "Active",
                "hire_date": str(hire_date),
                "termination_date": None,
                "termination_reason": None,
            },
            "current_position": {
                "position_id": position["id"],
                "title": position["title"],
                "level": position["level"],
                "job_family": position["family"],
                "organization_id": org["id"],
                "organization_name": org["name"],
                "location": location,
                "manager_id": None,
            },
            "hire_date": str(hire_date),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

    def _create_job_change(self, worker_id: str, change_type: str,
                           effective_date, new_position_id: str = None,
                           new_org_id: str = None,
                           old_position_id: str = None,
                           old_org_id: str = None) -> dict:
        now = datetime.utcnow()
        return {
            "change_id": f"JCH-{uuid.uuid4().hex[:8].upper()}",
            "worker_id": worker_id,
            "change_type": change_type,
            "reason": change_type,
            "effective_date": str(effective_date),
            "old_position_id": old_position_id,
            "new_position_id": new_position_id,
            "old_organization_id": old_org_id,
            "new_organization_id": new_org_id,
            "initiated_by": fake.name(),
            "approval_status": "Approved",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

    def _create_compensation(self, worker_id: str, effective_date,
                             position_level: str = "IC3") -> dict:
        salary_range = SALARY_RANGES.get(position_level, (70000, 130000))
        base_salary = round(random.uniform(*salary_range), 2)
        bonus_pct = random.choice([0, 5, 10, 15, 20])
        now = datetime.utcnow()

        return {
            "compensation_id": f"CMP-{uuid.uuid4().hex[:8].upper()}",
            "worker_id": worker_id,
            "effective_date": str(effective_date),
            "compensation_type": "Salary",
            "currency": random.choice(CURRENCIES),
            "base_salary": base_salary,
            "bonus_target_pct": bonus_pct,
            "bonus_target_amount": round(base_salary * bonus_pct / 100, 2),
            "total_compensation": round(base_salary * (1 + bonus_pct / 100), 2),
            "pay_frequency": "Semi-Monthly",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

    def simulate_changes(self, num_events: int = 10) -> list:
        """
        Simulate workforce changes: hires, terminations, promotions, transfers.
        Returns list of events generated.
        """
        events = []
        active_workers = [w for w in self.workers.values()
                          if w["employment_data"]["status"] == "Active"]
        today = datetime.utcnow().date()

        for _ in range(num_events):
            event_type = random.choices(
                ["hire", "termination", "promotion", "transfer", "time_off"],
                weights=[25, 15, 20, 15, 25],
                k=1
            )[0]

            if event_type == "hire":
                worker = self._create_worker(hire_date=today)
                self.workers[worker["worker_id"]] = worker
                self.job_changes.append(self._create_job_change(
                    worker_id=worker["worker_id"],
                    change_type="New Hire",
                    effective_date=today,
                    new_position_id=worker["current_position"]["position_id"],
                    new_org_id=worker["current_position"]["organization_id"],
                ))
                self.compensation_records.append(self._create_compensation(
                    worker_id=worker["worker_id"],
                    effective_date=today,
                    position_level=worker["current_position"]["level"],
                ))
                events.append({"type": "hire", "worker_id": worker["worker_id"]})

            elif event_type == "termination" and active_workers:
                worker = random.choice(active_workers)
                old_pos = worker["current_position"]["position_id"]
                old_org = worker["current_position"]["organization_id"]
                worker["employment_data"]["status"] = "Terminated"
                worker["employment_data"]["termination_date"] = str(today)
                worker["employment_data"]["termination_reason"] = random.choice(
                    ["Voluntary", "Involuntary", "Retirement"]
                )
                worker["updated_at"] = datetime.utcnow().isoformat()
                self.job_changes.append(self._create_job_change(
                    worker_id=worker["worker_id"],
                    change_type="Termination",
                    effective_date=today,
                    old_position_id=old_pos,
                    old_org_id=old_org,
                ))
                active_workers.remove(worker)
                events.append({"type": "termination", "worker_id": worker["worker_id"]})

            elif event_type == "promotion" and active_workers:
                worker = random.choice(active_workers)
                old_pos_id = worker["current_position"]["position_id"]
                old_org_id = worker["current_position"]["organization_id"]
                new_position = random.choice(POSITIONS)
                worker["current_position"]["position_id"] = new_position["id"]
                worker["current_position"]["title"] = new_position["title"]
                worker["current_position"]["level"] = new_position["level"]
                worker["updated_at"] = datetime.utcnow().isoformat()
                self.job_changes.append(self._create_job_change(
                    worker_id=worker["worker_id"],
                    change_type="Promotion",
                    effective_date=today,
                    old_position_id=old_pos_id,
                    new_position_id=new_position["id"],
                    old_org_id=old_org_id,
                    new_org_id=old_org_id,
                ))
                self.compensation_records.append(self._create_compensation(
                    worker_id=worker["worker_id"],
                    effective_date=today,
                    position_level=new_position["level"],
                ))
                events.append({"type": "promotion", "worker_id": worker["worker_id"]})

            elif event_type == "transfer" and active_workers:
                worker = random.choice(active_workers)
                old_org_id = worker["current_position"]["organization_id"]
                new_org = random.choice(DEPARTMENTS)
                worker["current_position"]["organization_id"] = new_org["id"]
                worker["current_position"]["organization_name"] = new_org["name"]
                worker["current_position"]["location"] = random.choice(LOCATIONS)
                worker["updated_at"] = datetime.utcnow().isoformat()
                self.job_changes.append(self._create_job_change(
                    worker_id=worker["worker_id"],
                    change_type="Transfer",
                    effective_date=today,
                    old_position_id=worker["current_position"]["position_id"],
                    new_position_id=worker["current_position"]["position_id"],
                    old_org_id=old_org_id,
                    new_org_id=new_org["id"],
                ))
                events.append({"type": "transfer", "worker_id": worker["worker_id"]})

            elif event_type == "time_off" and active_workers:
                worker = random.choice(active_workers)
                start = today + timedelta(days=random.randint(1, 30))
                duration = random.randint(1, 10)
                self.time_off_records.append({
                    "time_off_id": f"PTO-{uuid.uuid4().hex[:8].upper()}",
                    "worker_id": worker["worker_id"],
                    "type": random.choice(TIME_OFF_TYPES),
                    "start_date": str(start),
                    "end_date": str(start + timedelta(days=duration)),
                    "days_requested": duration,
                    "status": random.choice(["Approved", "Pending"]),
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                })
                events.append({"type": "time_off", "worker_id": worker["worker_id"]})

        return events


# Global state instance
workforce = WorkforceState()
