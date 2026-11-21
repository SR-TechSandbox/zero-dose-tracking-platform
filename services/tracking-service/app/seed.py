import json
import os
from datetime import datetime
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert as pg_insert

from .database import SessionLocal
from .models import Encounter

BASELINE_ENCOUNTERS_PATH = Path(
    os.getenv("BASELINE_ENCOUNTERS_PATH", "/app/data/baseline/encounters.jsonl")
)


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


if __name__ == "__main__":
    seed_encounters()