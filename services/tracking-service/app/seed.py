import json
import os
from datetime import datetime
from pathlib import Path

from .database import SessionLocal
from .models import Encounter

BASELINE_ENCOUNTERS_PATH = Path(
    os.getenv("BASELINE_ENCOUNTERS_PATH", "/app/data/baseline/encounters.jsonl")
)


def seed_encounters() -> None:
    if not BASELINE_ENCOUNTERS_PATH.exists():
        print(f"Baseline file not found at {BASELINE_ENCOUNTERS_PATH}; skipping seed.")
        return

    db = SessionLocal()
    try:
        inserted = 0
        total = 0
        with BASELINE_ENCOUNTERS_PATH.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                total += 1
                item = json.loads(line)
                if db.get(Encounter, item["event_id"]):
                    continue
                db.add(
                    Encounter(
                        event_id=item["event_id"],
                        child_id=item["child_id"],
                        round_id=item["round_id"],
                        device_id=item["device_id"],
                        recorded_at=datetime.fromisoformat(item["recorded_at"]),
                        type=item["type"],
                        zero_dose_answer=item.get("zero_dose_answer"),
                        vaccinated_since_last=item.get("vaccinated_since_last"),
                        vaccinated_elsewhere=item.get("vaccinated_elsewhere"),
                        comment=item.get("comment"),
                    )
                )
                inserted += 1
        db.commit()
        print(f"Seeded {inserted} new encounters (total in file: {total}).")
    finally:
        db.close()


if __name__ == "__main__":
    seed_encounters()