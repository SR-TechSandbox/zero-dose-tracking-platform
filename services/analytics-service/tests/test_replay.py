import json
from pathlib import Path

from app.replay import compute_round_transitions, replay_child_timeline

REPO_ROOT = Path(__file__).resolve().parents[3]
ROUNDS_PATH = REPO_ROOT / "data" / "baseline" / "rounds.json"
ENCOUNTERS_PATH = REPO_ROOT / "data" / "baseline" / "encounters.jsonl"


def _load_baseline():
    rounds = json.loads(ROUNDS_PATH.read_text(encoding="utf-8"))
    encounters = [
        json.loads(line)
        for line in ENCOUNTERS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return rounds, encounters


def test_rule_2_1_intra_round_correction_c043():
    """C043: E0070 ('yes') then E0094 ('no', correction) -> ends R2 as Zero-Dose."""
    rounds, encounters = _load_baseline()
    tl = replay_child_timeline("C043", rounds, encounters)

    assert tl["round_states"]["R1"]["zero_dose"] is True
    assert tl["round_states"]["R2"]["zero_dose"] is True
    # Audit trail preserves both R2 events
    r2_ids = [e["event_id"] for e in tl["audit_trail"] if e["round_id"] == "R2"]
    assert r2_ids == ["E0070", "E0094"]


def test_rule_2_2_intra_round_duplicate_c027():
    """C027: E0078 ('yes' 09:40) then E0081 ('no' 13:55) -> ends R2 as Zero-Dose."""
    rounds, encounters = _load_baseline()
    tl = replay_child_timeline("C027", rounds, encounters)

    assert tl["round_states"]["R1"]["zero_dose"] is True
    assert tl["round_states"]["R2"]["zero_dose"] is True


def test_rule_2_3_null_revisits_preserve_state():
    """Null revisit encounters must not emit state changes."""
    rounds, encounters = _load_baseline()
    # C049 is False in R1 and has a null revisit E0064 in R2
    tl = replay_child_timeline("C049", rounds, encounters)
    assert tl["round_states"]["R1"]["zero_dose"] is False
    assert tl["round_states"]["R2"]["zero_dose"] is False

    e0064 = next(e for e in tl["audit_trail"] if e["event_id"] == "E0064")
    assert e0064["state_changed"] is False


def test_rule_2_4_external_vaccination_c016():
    """C016: E0061 has vaccinated_elsewhere=True -> transitions with External tag."""
    rounds, encounters = _load_baseline()
    tl = replay_child_timeline("C016", rounds, encounters)

    assert tl["round_states"]["R1"]["zero_dose"] is True
    assert tl["round_states"]["R2"]["zero_dose"] is False
    assert (
        tl["round_states"]["R2"]["confirmation_method"]
        == "External (Vaccinated Elsewhere)"
    )


def test_rule_2_5_round_to_round_transitions():
    """Verify aggregate transitions exclude C043/C027 in R1->R2 and include C016."""
    rounds, encounters = _load_baseline()
    summary = compute_round_transitions(rounds, encounters)

    assert summary["total_children"] == 60
    assert summary["total_encounters"] == 130

    r1_to_r2 = summary["transitions"][0]
    assert r1_to_r2["from_round"] == "R1"
    assert r1_to_r2["to_round"] == "R2"

    transitioned_ids = {c["child_id"] for c in r1_to_r2["transitioned_children"]}
    assert "C016" in transitioned_ids
    assert "C043" not in transitioned_ids
    assert "C027" not in transitioned_ids