from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Optional


def _parse_iso(ts: str) -> datetime:
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)


def _natural_child_key(child_id: str) -> tuple[str, int, str]:
    match = re.fullmatch(r"([A-Za-z_-]*?)(\d+)", child_id.strip())
    if match:
        prefix, num = match.groups()
        return (prefix.lower(), int(num), child_id)
    return (child_id.lower(), 10**9, child_id)


def _derive_confirmation_method(event: dict[str, Any]) -> Optional[str]:
    if event.get("vaccinated_since_last") == "yes":
        if event.get("vaccinated_elsewhere") is True:
            return "External (Vaccinated Elsewhere)"
        return "Campaign / Field Dose"
    if event.get("type") == "enumeration" and event.get("zero_dose_answer") is False:
        return "Enumeration (Already Vaccinated)"
    return None


def _derive_zero_dose_after(
    event: dict[str, Any], prev_zero_dose: Optional[bool]
) -> tuple[Optional[bool], Optional[str]]:
    """
    Returns (new_zero_dose_state, confirmation_method_if_changed_or_confirmed).
    Null/ambiguous revisits preserve prior state (never flip to zero-dose on missing data).
    """
    ev_type = event.get("type")

    if ev_type == "enumeration":
        ans = event.get("zero_dose_answer")
        if ans is True:
            return True, None
        if ans is False:
            return False, _derive_confirmation_method(event)
        return prev_zero_dose, None

    if ev_type == "revisit":
        vsl = event.get("vaccinated_since_last")
        if vsl == "yes":
            return False, _derive_confirmation_method(event)
        if vsl == "no":
            return True, None
        return prev_zero_dose, None

    return prev_zero_dose, None


def replay_child_timeline(
    child_id: str,
    encounters: list[dict[str, Any]],
    ordered_rounds: list[str],
) -> dict[str, Any]:
    child_events = [e for e in encounters if e.get("child_id") == child_id]
    child_events.sort(
        key=lambda e: (_parse_iso(e["recorded_at"]), str(e.get("event_id", "")))
    )

    events_by_round: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ev in child_events:
        events_by_round[ev["round_id"]].append(ev)

    current_zero_dose: Optional[bool] = None
    current_confirmation: Optional[str] = None
    audit_trail: list[dict[str, Any]] = []

    all_round_ids: list[str] = []
    seen_rounds: set[str] = set()
    for r in ordered_rounds:
        if r not in seen_rounds:
            seen_rounds.add(r)
            all_round_ids.append(r)
    for ev in child_events:
        r = ev["round_id"]
        if r not in seen_rounds:
            seen_rounds.add(r)
            all_round_ids.append(r)

    round_states: dict[str, dict[str, Any]] = {}

    for r_id in all_round_ids:
        r_events = events_by_round.get(r_id, [])
        round_confirmation: Optional[str] = None

        for ev in r_events:
            prev_state = current_zero_dose
            next_state, conf = _derive_zero_dose_after(ev, prev_state)
            state_changed = next_state != prev_state
            current_zero_dose = next_state
            if conf:
                current_confirmation = conf
                round_confirmation = conf
            elif current_zero_dose is True:
                current_confirmation = None
                round_confirmation = None

            audit_trail.append(
                {
                    "event_id": ev["event_id"],
                    "round_id": r_id,
                    "recorded_at": ev["recorded_at"],
                    "type": ev["type"],
                    "zero_dose_after": current_zero_dose,
                    "confirmation_method": round_confirmation
                    if current_zero_dose is False
                    else None,
                    "state_changed": state_changed,
                    "comment": ev.get("comment"),
                }
            )

        round_states[r_id] = {
            "round_id": r_id,
            "zero_dose": current_zero_dose,
            "confirmation_method": round_confirmation
            if current_zero_dose is False
            else None,
        }

    return {
        "child_id": child_id,
        "current_zero_dose": current_zero_dose,
        "confirmation_method": current_confirmation
        if current_zero_dose is False
        else None,
        "round_states": round_states,
        "audit_trail": audit_trail,
    }


def compute_round_transitions(
    rounds_meta: list[dict[str, Any]],
    encounters: list[dict[str, Any]],
) -> dict[str, Any]:
    valid_encounters = [
        e for e in encounters if isinstance(e, dict) and "child_id" in e
    ]
    valid_rounds = [
        r for r in rounds_meta if isinstance(r, dict) and "round_id" in r
    ]

    ordered_rounds = [r["round_id"] for r in valid_rounds]
    seen = set(ordered_rounds)
    for ev in valid_encounters:
        r = ev.get("round_id")
        if r and r not in seen:
            seen.add(r)
            ordered_rounds.append(r)

    child_ids = sorted(
        {e["child_id"] for e in valid_encounters}, key=_natural_child_key
    )
    timelines = [
        replay_child_timeline(cid, valid_encounters, ordered_rounds)
        for cid in child_ids
    ]

    transitions: list[dict[str, Any]] = []
    for idx in range(len(ordered_rounds) - 1):
        r_from = ordered_rounds[idx]
        r_to = ordered_rounds[idx + 1]

        transitioned_children: list[dict[str, Any]] = []
        remaining_zero_dose = 0

        for tl in timelines:
            st_from = tl["round_states"].get(r_from, {}).get("zero_dose")
            st_to_obj = tl["round_states"].get(r_to, {})
            st_to = st_to_obj.get("zero_dose")

            if st_from is True and st_to is False:
                transitioned_children.append(
                    {
                        "child_id": tl["child_id"],
                        "confirmation_method": st_to_obj.get("confirmation_method"),
                    }
                )
            if st_to is True:
                remaining_zero_dose += 1

        transitioned_children.sort(
            key=lambda ch: _natural_child_key(ch["child_id"])
        )

        transitions.append(
            {
                "from_round": r_from,
                "to_round": r_to,
                "transitioned_count": len(transitioned_children),
                "remaining_zero_dose_count": remaining_zero_dose,
                "transitioned_children": transitioned_children,
            }
        )

    return {
        "total_children": len(child_ids),
        "total_encounters": len(valid_encounters),
        "rounds": ordered_rounds,
        "transitions": transitions,
    }