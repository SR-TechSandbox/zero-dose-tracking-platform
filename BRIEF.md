# Take-Home: Zero-Dose Tracking Across Campaign Rounds

## Background

In vaccination campaigns, a **zero-dose child** is one who has never received any vaccine dose. Finding these children and getting them vaccinated is the campaign's highest-value outcome, so supervisors need to know: *how many zero-dose children did we reach between rounds?*

Field workers enumerate children in Round 1 (capturing a zero-dose flag) and revisit them in later rounds. This feature request comes from our real backlog:

> Persist the zero-dose flag on the child record across campaign rounds, and show it to recorders when they encounter the child in a later round. Add a "vaccinated since last campaign?" prompt that, when answered, updates the flag (yes → no) while retaining the historical value and a timestamp for each change, including guardian-confirmed vaccination elsewhere. Add a round filter to the supervisor dashboard showing how many children moved from zero-dose to vaccinated between rounds.

## Your task

Build a small end-to-end application over the provided sample data (`data/`):

1. **Backend** (any language): API + persistence. All three data files load automatically at startup. Model the zero-dose flag with **full history** — every change retained with its timestamp and source. Expose:
   - a child's current flag + complete flag history,
   - the supervisor aggregate: children who moved from zero-dose to vaccinated between a selectable pair of consecutive rounds,
   - a write path: record a new revisit encounter (child, round, answer) that updates the flag per your rules while preserving history.
2. **Frontend**: a thin web UI — a supervisor view (round-pair selector + the moved count + the list of those children) and a child detail view (current flag, history timeline, and a simple form to record a new encounter). Function over polish.
3. **Containerization**: a `docker-compose.yml` at the repo root. **`docker compose up` must be the only command needed** — builds, starts everything, loads the data; README states the URL.

The sample data contains inconsistencies and edge conditions you should handle; deciding what they mean — and making your decisions visible — is part of the task.

## Deliverables

1. `spec.md` — the problem restated, every ambiguity you found and how you resolved it (with reasoning), explicit out-of-scope list.
2. `plan.md` — milestones, data model, API sketch, test strategy, what you'd do with one more day.
3. Working code (backend + frontend) + tests + `docker-compose.yml` + `README.md` (run instructions, including the test command).
4. `ai-log.md` — your AI prompts/transcript (or exported session), plus 3–5 sentences on where the AI was wrong and how you caught it.

## Rules

- **Hard cap: 4 hours.** Stop at 4 hours and submit what you have — scoping under a time budget is part of what we assess.
- **AI use is required.** Use Claude/Copilot/etc. allowed;

## Submission checklist

- [ ] `docker compose up` from a clean clone brings up the full app with data loaded
- [ ] README states the URL and the test command
- [ ] `spec.md`, `plan.md`, `ai-log.md` present
- [ ] Tests run and pass (state the command)
- [ ] Zip the repo (or share a private git link) — include everything needed, exclude build artifacts
