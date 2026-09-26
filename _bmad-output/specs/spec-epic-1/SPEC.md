---
id: SPEC-epic-1
companions: [../../../mcp/triage_server.py]
sources: [../../../INTENT.md]
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Epic 1: triage data and schema

## Why

The triage agent (Epic 2) and its eval (Epic 3) both need two things that do not exist yet: a strict definition of what a triage decision is, and a local database of tickets and customers for the MCP tools to read. Epic 1 lays that foundation offline, with no model or API key involved, so later epics build on a fixed contract instead of guessing at one.

## Capabilities

- **CAP-1**
  - **intent:** Code can check whether an object is a valid triage decision: a category, a priority, a route and a one-sentence rationale.
  - **success:** An object with category in {billing, bug, access, performance, how-to}, priority in {P1, P2, P3, P4}, route in {billing-team, bug-team, access-team, performance-team, how-to-team} and a rationale passes. A wrong enum value, a missing field or an extra field each fails with an error that names the field.

- **CAP-2**
  - **intent:** A person can load the seed data into a local SQLite database with one command.
  - **success:** After `uv run python load_seed.py`, `app.db` holds table `tickets` (columns `ticket_id, customer_id, created_at, text`) and table `customers` (columns `customer_id, name, plan, open_tickets`), with row counts equal to `seed/tickets.csv` and `seed/customers.csv`.

- **CAP-3**
  - **intent:** Loading the seed data is repeatable.
  - **success:** Running `load_seed.py` twice leaves identical table contents and row counts, with no duplicate rows.

## Constraints

- Python 3.12 or newer, managed with uv.
- Files in `seed/` are read-only.
- No network calls and no API keys in this epic.
- `mcp/triage_server.py` already queries `app.db`; its table and column names must keep working unchanged.
- Epic 2 uses the schema as the agent's structured output and validator without modifying it, so it must be importable from Python.

## Non-goals

- The agent (Epic 2).
- The MCP tools.
- Evals (Epic 3).
- Any user interface.

## Success signal

`uv run python load_seed.py`, run twice, leaves an `app.db` that `mcp/triage_server.py` can query for ticket T-1042 and customer C-77. The schema accepts `{"category": "billing", "priority": "P2", "route": "billing-team", "rationale": "..."}` and rejects `"priority": "P5"` with a clear error.

## Assumptions

- An object with fields beyond the four is rejected ("anything else is rejected" read strictly).
- `app.db` is written at the project root, where `mcp/triage_server.py` looks for it.

## Open Questions

- Must the schema enforce `TRIAGE_POLICY.md`'s category-to-route pairing (billing → billing-team, etc.), or accept any valid category with any valid route?
- How is "one-sentence rationale" enforced: reject only empty text, or also reject multi-sentence text?
- Should `open_tickets` be stored as INTEGER, or all columns as text as read from the CSV?
