import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert as pg_insert

from .database import SessionLocal
from .models import Campaign, Round

BASELINE_ROUNDS_PATH = Path(
    os.getenv("BASELINE_ROUNDS_PATH", "/app/data/baseline/rounds.json")
)


def seed_rounds() -> None:
    if not BASELINE_ROUNDS_PATH.exists():
        print(f"Baseline file not found at {BASELINE_ROUNDS_PATH}; skipping seed.")
        return

    records = json.loads(BASELINE_ROUNDS_PATH.read_text(encoding="utf-8"))
    rows = [
        {
            "round_id": item["round_id"],
            "name": item["name"],
            "start_date": date.fromisoformat(item["start_date"]),
            "end_date": date.fromisoformat(item["end_date"]),
        }
        for item in records
    ]

    db = SessionLocal()
    try:
        if rows:
            stmt = pg_insert(Round).values(rows).on_conflict_do_nothing(
                index_elements=["round_id"]
            )
            result = db.execute(stmt)
            db.commit()
            print(
                f"Seeded {result.rowcount} new rounds (total in file: {len(rows)})."
            )
    finally:
        db.close()


def seed_campaigns() -> None:
    now = datetime.now(timezone.utc)
    rows = [
        {
            "id": "camp-001",
            "name": "Zero-Dose Outreach - Kwanar Dawa & Sabon Layi",
            "district": "Kwanar Dawa",
            "target_beneficiaries": 25,
            "status": "active",
            "created_by": "admin",
            "created_at": now - timedelta(days=10),
        },
        {
            "id": "camp-002",
            "name": "Zero-Dose Outreach - Kofar Ruwa & Unguwar Rimi",
            "district": "Kofar Ruwa",
            "target_beneficiaries": 25,
            "status": "active",
            "created_by": "admin",
            "created_at": now - timedelta(days=6),
        },
        {
            "id": "camp-003",
            "name": "Zero-Dose Outreach - Rimin Kebe & Tudun Fulani",
            "district": "Rimin Kebe",
            "target_beneficiaries": 25,
            "status": "active",
            "created_by": "admin",
            "created_at": now - timedelta(days=3),
        },
    ]

    db = SessionLocal()
    try:
        stmt = pg_insert(Campaign).values(rows).on_conflict_do_nothing(
            index_elements=["id"]
        )
        result = db.execute(stmt)
        db.commit()
        print(f"Seeded {result.rowcount} new campaigns (total: {len(rows)}).")
    finally:
        db.close()


if __name__ == "__main__":
    seed_rounds()
    seed_campaigns()