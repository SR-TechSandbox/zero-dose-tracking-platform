import csv
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert as pg_insert

from .database import SessionLocal
from .models import Beneficiary, Encounter, Vaccination

BASELINE_ENCOUNTERS_PATH = Path(
    os.getenv("BASELINE_ENCOUNTERS_PATH", "/app/data/baseline/encounters.jsonl")
)
BASELINE_CHILDREN_PATH = Path(
    os.getenv("BASELINE_CHILDREN_PATH", "/app/data/baseline/children.csv")
)

SETTLEMENT_TO_CAMPAIGN = {
    "Kwanar Dawa": "camp-001",
    "Sabon Layi": "camp-001",
    "Kofar Ruwa": "camp-002",
    "Unguwar Rimi": "camp-002",
    "Rimin Kebe": "camp-003",
    "Tudun Fulani": "camp-003",
}


def seed_encounters() -> None:
    if not BASELINE_ENCOUNTERS_PATH.exists():
        print(f"Baseline file not found at {BASELINE_ENCOUNTERS_PATH}; skipping seed.")
        return

    rows = []
    with BASELINE_ENCOUNTERS_PATH.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            rows.append(
                {
                    "event_id": item["event_id"],
                    "child_id": item["child_id"],
                    "round_id": item["round_id"],
                    "device_id": item["device_id"],
                    "recorded_at": datetime.fromisoformat(item["recorded_at"]),
                    "type": item["type"],
                    "zero_dose_answer": item.get("zero_dose_answer"),
                    "vaccinated_since_last": item.get("vaccinated_since_last"),
                    "vaccinated_elsewhere": item.get("vaccinated_elsewhere"),
                    "comment": item.get("comment"),
                }
            )

    db = SessionLocal()
    try:
        if rows:
            stmt = pg_insert(Encounter).values(rows).on_conflict_do_nothing(
                index_elements=["event_id"]
            )
            result = db.execute(stmt)
            db.commit()
            print(
                f"Seeded {result.rowcount} new encounters (total in file: {len(rows)})."
            )
    finally:
        db.close()


def seed_children() -> None:
    if not BASELINE_CHILDREN_PATH.exists():
        print(f"Children file not found at {BASELINE_CHILDREN_PATH}; skipping seed.")
        return

    today = date.today()
    now = datetime.now(timezone.utc)
    beneficiary_rows = []
    vaccination_rows = []

    with BASELINE_CHILDREN_PATH.open("r", encoding="utf-8", newline="") as fh:
        for i, r in enumerate(csv.DictReader(fh)):
            cid = r["child_id"].strip()
            settlement = r["settlement"].strip()
            dob = date.fromisoformat(r["dob"].strip())
            age_months = max(0, (today.year - dob.year) * 12 + (today.month - dob.month))

            beneficiary_rows.append(
                {
                    "id": cid,
                    "campaign_id": SETTLEMENT_TO_CAMPAIGN.get(settlement, "camp-001"),
                    "full_name": r["name"].strip(),
                    "age_months": age_months,
                    "district": settlement,
                    "registered_by": "worker.user",
                    "created_at": now - timedelta(days=i % 7),
                }
            )

            # Seed DTP1 for first 35 children; leave 25 zero-dose children for interactive testing
            if i < 35:
                vaccination_rows.append(
                    {
                        "id": f"vac-{cid}",
                        "beneficiary_id": cid,
                        "vaccine_name": "DTP1",
                        "dose_number": 1,
                        "administered_by": "worker.user",
                        "administered_at": now - timedelta(days=i % 5),
                    }
                )

    db = SessionLocal()
    try:
        if beneficiary_rows:
            b_stmt = pg_insert(Beneficiary).values(beneficiary_rows).on_conflict_do_nothing(
                index_elements=["id"]
            )
            b_res = db.execute(b_stmt)
            db.commit()
            print(
                f"Seeded {b_res.rowcount} new beneficiaries (total in file: {len(beneficiary_rows)})."
            )

        if vaccination_rows:
            v_stmt = pg_insert(Vaccination).values(vaccination_rows).on_conflict_do_nothing(
                index_elements=["id"]
            )
            v_res = db.execute(v_stmt)
            db.commit()
            print(
                f"Seeded {v_res.rowcount} new vaccinations (total: {len(vaccination_rows)})."
            )
    finally:
        db.close()


if __name__ == "__main__":
    seed_encounters()
    seed_children()