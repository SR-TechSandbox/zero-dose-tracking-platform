from datetime import datetime
from typing import Any, Optional


def _parse_ts(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def replay_child_timeline(
    child_id: str,
    rounds: list[dict[str, Any]],
    encounters: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Deterministically replay all encounters for a single child in chronological order.

    Rules enforced:
    - 2.1 Intra-round corrections (e.g. C043): explicit "no" resets zero_dose=True;
      all events remain preserved in the audit trail.
    - 2.2 Intra-round duplicates (e.g. C027): last decisive event in the round wins.
    - 2.3 Null revisits: preserve prior zero_dose state; no state change emitted.
    - 2.4 External vaccination (e.g. C016): vaccinated_elsewhere=True sets
      confirmation_method="External (Vaccinated Elsewhere)".
    """
    ordered_rounds = sorted(rounds, key=lambda r: r["start_date"])
    child_events = sorted(
        [e for e in encounters if e["child_id"] == child_id],
        key=lambda e: (_parse_ts(e["recorded_at"]), e["event_id"]),
    )

    events_by_round: dict[str, list[dict[str, Any]]] = {}
    for ev in child_events:
        events_by_round.setdefault(ev["round_id"], []).append(ev)

    current_zero_dose: Optional[bool] = None
    confirmation_method: Optional[str] = None
    round_states: dict[str, dict[str, Any]] = {}
    audit_trail: list[dict[str, Any]] = []

    for r in ordered_rounds:
        rid = r["round_id"]
        for ev in events_by_round.get(rid, []):
            prev_state = current_zero_dose
            ev_type = ev.get("type")
            state_changed = False

            if ev_type == "enumeration":
                ans = ev.get("zero_dose_answer")
                if ans is not None:
                    current_zero_dose = bool(ans)
                    confirmation_method = None if current_zero_dose else "Prior Vaccination"
                    state_changed = current_zero_dose != prev_state

            elif ev_type == "revisit":
                vax = ev.get("vaccinated_since_last")
                ext = ev.get("vaccinated_elsewhere")

                if vax == "yes" or ext is True:
                    current_zero_dose = False
                    confirmation_method = (
                        "External (Vaccinated Elsewhere)"
                        if ext is True
                        else "Campaign Vaccination"
                    )
                    state_changed = current_zero_dose != prev_state
                elif vax == "no":
                    # Explicit negative answer (including intra-round corrections)
                    # resets status back to Zero-Dose (True).
                    current_zero_dose = True
                    confirmation_method = None
                    state_changed = current_zero_dose != prev_state
                else:
                    # Rule 2.3: Null revisit preserves prior zero_dose flag.
                    state_changed = False

            audit_trail.append(
                {
                    "event_id": ev["event_id"],
                    "round_id": rid,
                    "recorded_at": ev["recorded_at"],
                    "type": ev_type,
                    "zero_dose_after": current_zero_dose,
                    "confirmation_method": confirmation_method,
                    "state_changed": state_changed,
                    "comment": ev.get("comment"),
                }
            )

        round_states[rid] = {
            "round_id": rid,
            "zero_dose": current_zero_dose,
            "confirmation_method": confirmation_method,
        }

    return {
        "child_id": child_id,
        "current_zero_dose": current_zero_dose,
        "confirmation_method": confirmation_method,
        "round_states": round_states,
        "audit_trail": audit_trail,
    }

import re

def _natural_child_key(child_id: str) -> tuple[str, int, str]:
    match = re.fullmatch(r"([A-Za-z_-]*?)(\d+)", child_id.strip())
    if match:
        prefix, num = match.groups()
        return (prefix.lower(), int(num), child_id)
    return (child_id.lower(), 10**9, child_id)


def compute_round_transitions(
    rounds: list[dict[str, Any]],
    encounters: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Compute round-to-round transitions across all children (Rule 2.5):
    A child transitions from Round A -> Round B iff:
      1. Effective end-of-round status in Round A was Zero-Dose (True)
      2. Effective end-of-round status in Round B was Vaccinated (False)
    """
    ordered_rounds = sorted(rounds, key=lambda r: r["start_date"])
    child_ids = sorted({e["child_id"] for e in encounters}, key=_natural_child_key)

    timelines = {
        cid: replay_child_timeline(cid, ordered_rounds, encounters)
        for cid in child_ids
    }

    transitioned_children.sort(key=lambda ch: _natural_child_key(ch["child_id"]))
    transitions: list[dict[str, Any]] = []
    for idx in range(len(ordered_rounds) - 1):
        r_from = ordered_rounds[idx]["round_id"]
        r_to = ordered_rounds[idx + 1]["round_id"]

        transitioned_children: list[dict[str, Any]] = []
        remaining_zero_dose: list[str] = []

        for cid, tl in timelines.items():
            state_a = tl["round_states"][r_from]["zero_dose"]
            state_b = tl["round_states"][r_to]["zero_dose"]

            if state_a is True and state_b is False:
                transitioned_children.append(
                    {
                        "child_id": cid,
                        "confirmation_method": tl["round_states"][r_to][
                            "confirmation_method"
                        ],
                    }
                )
            elif state_a is True and state_b is True:
                remaining_zero_dose.append(cid)

        transitions.append(
            {
                "from_round": r_from,
                "to_round": r_to,
                "transitioned_count": len(transitioned_children),
                "remaining_zero_dose_count": len(remaining_zero_dose),
                "transitioned_children": transitioned_children,
            }
        )

    return {
        "total_children": len(child_ids),
        "total_encounters": len(encounters),
        "rounds": [r["round_id"] for r in ordered_rounds],
        "transitions": transitions,
    }