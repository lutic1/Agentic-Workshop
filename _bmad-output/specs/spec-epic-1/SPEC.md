---
id: SPEC-epic-1
companions: [../../../TRIAGE_POLICY.md, ../../../mcp/triage_server.py]
sources: [../../../INTENT.md]
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Epic 1: triage decision schema and seed loader

## Why

The workshop's triage agent (Epic 2) and its eval (Epic 3) both need two foundations that do not exist yet: a strict shape for a triage decision, and the seed tickets and customers sitting in the SQLite database that `mcp/triage_server.py` already reads. Epic 1 builds those foundations, offline and without any model, so later epics have a contract to produce against and data to look up.

## Capabilities

- **CAP-1**
  - **intent:** Any triage decision can be checked against one schema: a JSON object with a category, a priority, a route and a one-sentence rationale.
  - **success:** An object with category in `billing`, `bug`, `access`, `performance`, `how-to`; priority in `P1`–`P4`; route in `billing-team`, `bug-team`, `access-team`, `performance-team`, `how-to-team`; and a rationale is accepted. An object with a value outside those sets, or a missing field, is rejected with an error that names the offending field.

- **CAP-2**
  - **intent:** One command loads the seed data into a local SQLite database, and running it again gives the same database.
  - **success:** `uv run python load_seed.py` creates `app.db` with tables `tickets` and `customers` whose columns match the headers of `seed/tickets.csv` and `seed/customers.csv`, holding 24 tickets and 20 customers. A second run leaves identical contents, with no duplicate rows.

## Constraints

- Python 3.12 or newer, managed with uv.
- The files in `seed/` are read-only.
- No network calls and no API keys anywhere in this epic.
- `mcp/triage_server.py` must keep working unchanged: `app.db` at the repo root, `tickets(ticket_id, customer_id, created_at, text)`, `customers(customer_id, name, plan, open_tickets)`.
- `app.db` is generated and never committed.

## Non-goals

- The agent, the MCP tools, evals and any user interface (Epics 2 and 3).

## Success signal

On a fresh clone with no API keys and no network, `uv run python load_seed.py` run twice leaves an `app.db` from which `get_ticket("T-1042")` returns customer `C-77`, and the schema accepts `billing` / `P2` / `billing-team` with a rationale while rejecting `billing` / `P5`.

## Assumptions

- `open_tickets` loads as an integer, since `TRIAGE_POLICY.md`'s Enterprise rule compares it to 3; other columns load as text.

## Open Questions

- Must the route match the category per `TRIAGE_POLICY.md`'s one-to-one table, rejecting e.g. `billing` with `bug-team`? `INTENT.md` only lists the allowed values.
- Does "anything else is rejected" cover extra fields beyond the four, and is "one sentence" for the rationale enforced (single-sentence check) or just non-empty?
