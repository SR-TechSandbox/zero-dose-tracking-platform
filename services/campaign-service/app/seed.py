import json
import os
from datetime import date
from pathlib import Path

from .database import SessionLocal
from .models import Round

BASELINE_ROUNDS_PATH = Path(
    os.getenv("BASELINE_ROUNDS_PATH", "/app/data/baseline/rounds.json")
)


def seed_rounds() -> None:
    if not BASELINE_ROUNDS_PATH.exists():
        print(f"Baseline file not found at {BASELINE_ROUNDS_PATH}; skipping seed.")
        return

    records = json.loads(BASELINE_ROUNDS_PATH.read_text(encoding="utf-8"))
    db = SessionLocal()
    try:
        inserted = 0
        for item in records:
            exists = db.get(Round, item["round_id"])
            if not exists:
                db.add(
                    Round(
                        round_id=item["round_id"],
                        name=item["name"],
                        start_date=date.fromisoformat(item["start_date"]),
                        end_date=date.fromisoformat(item["end_date"]),
                    )
                )
                inserted += 1
        db.commit()
        print(f"Seeded {inserted} new rounds (total in file: {len(records)}).")
    finally:
        db.close()


if __name__ == "__main__":
    seed_rounds()