from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Optional


def _parse_iso(ts: str) -> datetime:
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)


def _safe_ts(val: Any) -> datetime:
    if isinstance(val, datetime):
        return val
    if isinstance(val, str) and val.strip():
        try:
            return _parse_iso(val.strip())
        except ValueError:
            pass
    return datetime.min


def _natural_child_key(child_id: str) -> tuple[str, int, str]:
    match = re.fullmatch(r"([A-Za-z_-]*?)(\d+)", str(child_id).strip())
    if match:
        prefix, num = match.groups()
        return (prefix.lower(), int(num), str(child_id))
    return (str(child_id).lower(), 10**9, str(child_id))


def _normalize_round_id(item: Any) -> Optional[str]:
    if isinstance(item, dict):
        rid = item.get("round_id")
        return str(rid) if rid else None
    if isinstance(item, str) and item.strip():
        return item.strip()
    return None


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
    encounters_or_rounds: list[Any],
    rounds_or_encounters: list[Any],
) -> dict[str, Any]:
    # Support both (child_id, encounters, ordered_rounds) and (child_id, rounds, encounters)
    first_has_child = any(
        isinstance(x, dict) and "child_id" in x for x in encounters_or_rounds
    )
    second_has_child = any(
        isinstance(x, dict) and "child_id" in x for x in rounds_or_encounters
    )

    if second_has_child and not first_has_child:
        raw_rounds = encounters_or_rounds
        raw_encounters = rounds_or_encounters
    else:
        raw_encounters = encounters_or_rounds
        raw_rounds = rounds_or_encounters

    child_events = [
        e
        for e in raw_encounters
        if isinstance(e, dict) and str(e.get("child_id", "")) == str(child_id)
    ]
    child_events.sort(
        key=lambda e: (_safe_ts(e.get("recorded_at")), str(e.get("event_id", "")))
    )

    events_by_round: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ev in child_events:
        r_str = _normalize_round_id(ev.get("round_id"))
        if r_str:
            events_by_round[r_str].append(ev)

    current_zero_dose: Optional[bool] = None
    current_confirmation: Optional[str] = None
    audit_trail: list[dict[str, Any]] = []

    all_round_ids: list[str] = []
    seen_rounds: set[str] = set()
    for r in raw_rounds:
        r_str = _normalize_round_id(r)
        if r_str and r_str not in seen_rounds:
            seen_rounds.add(r_str)
            all_round_ids.append(r_str)
    for ev in child_events:
        r_str = _normalize_round_id(ev.get("round_id"))
        if r_str and r_str not in seen_rounds:
            seen_rounds.add(r_str)
            all_round_ids.append(r_str)

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

            rec_at = ev.get("recorded_at")
            audit_trail.append(
                {
                    "event_id": str(ev.get("event_id", "")),
                    "round_id": r_id,
                    "recorded_at": rec_at.isoformat()
                    if isinstance(rec_at, datetime)
                    else str(rec_at or ""),
                    "type": str(ev.get("type") or "revisit"),
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
    rounds_meta: list[Any],
    encounters: list[Any],
) -> dict[str, Any]:
    first_has_child = any(
        isinstance(x, dict) and "child_id" in x for x in rounds_meta
    )
    second_has_child = any(
        isinstance(x, dict) and "child_id" in x for x in encounters
    )
    if first_has_child and not second_has_child:
        valid_encounters = [
            e for e in rounds_meta if isinstance(e, dict) and "child_id" in e
        ]
        valid_rounds = [
            r for r in encounters if isinstance(r, dict) and _normalize_round_id(r)
        ]
    else:
        valid_encounters = [
            e for e in encounters if isinstance(e, dict) and "child_id" in e
        ]
        valid_rounds = [
            r for r in rounds_meta if isinstance(r, dict) and _normalize_round_id(r)
        ]

    ordered_rounds: list[str] = []
    seen: set[str] = set()
    for r in valid_rounds:
        r_str = _normalize_round_id(r)
        if r_str and r_str not in seen:
            seen.add(r_str)
            ordered_rounds.append(r_str)
    for ev in valid_encounters:
        r_str = _normalize_round_id(ev.get("round_id"))
        if r_str and r_str not in seen:
            seen.add(r_str)
            ordered_rounds.append(r_str)

    child_ids = sorted(
        {str(e["child_id"]) for e in valid_encounters}, key=_natural_child_key
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