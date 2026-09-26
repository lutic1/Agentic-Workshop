---
id: SPEC-epic-1
companions: [../../../mcp/triage_server.py]
sources: [../../../INTENT.md]
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Epic 1: triage data and schema

## Why

The workshop's later epics — the triage agent (Epic 2) and its eval (Epic 3) — both need a decision format to produce and check against, and both need real ticket and customer data to run over. Neither exists yet: there's no schema a decision can be validated against, and `seed/tickets.csv` / `seed/customers.csv` aren't loaded anywhere queryable. Epic 1 is the foundation those epics build on, and it has to be in place before Saturday's agent-building work can start.

## Capabilities

- **CAP-1**
  - **intent:** Any triage decision can be validated as a JSON object with a category, priority, route and rationale, with anything malformed or out-of-schema rejected.
  - **success:** A decision with category one of `billing`, `bug`, `access`, `performance`, `how-to`, priority one of `P1`–`P4`, route one of `billing-team`, `bug-team`, `access-team`, `performance-team`, `how-to-team`, and a one-sentence rationale validates. A decision with an unrecognized category/priority/route, a missing field, or extra fields is rejected with a clear error naming what's wrong.

- **CAP-2**
  - **intent:** A person can load the seed tickets and customers into a local database with one command.
  - **success:** `uv run python load_seed.py` loads `seed/tickets.csv` and `seed/customers.csv` into `app.db` as tables `tickets` (`ticket_id`, `customer_id`, `created_at`, `text`) and `customers` (`customer_id`, `name`, `plan`, `open_tickets`), matching the CSVs row for row. Running it twice in a row leaves `app.db` in the same state — no duplicate rows, no error.

## Constraints

- Python 3.12 or newer, managed with `uv`; packages added with `uv add`.
- `seed/tickets.csv` and `seed/customers.csv` are read-only; `load_seed.py` only reads them.
- No network calls and no API keys anywhere in this epic.
- `app.db`'s tables and columns must exactly match what `mcp/triage_server.py` already queries — `tickets(ticket_id, customer_id, created_at, text)` and `customers(customer_id, name, plan, open_tickets)` — since that file is read-only and cannot be adapted to a different schema.

## Non-goals

- The LangChain triage agent (Epic 2).
- The MCP tools themselves — `mcp/triage_server.py` already exists and isn't touched this epic.
- The eval harness and LLM judge (Epic 3).
- Any user interface.

## Success signal

`uv run python load_seed.py` populates `app.db` from the seed CSVs, and running it again leaves the same data in place. A decision like `{"category": "billing", "priority": "P2", "route": "billing-team", "rationale": "..."}` validates against the schema, while a decision with an unknown category or a missing field is rejected with a clear error.

## Open Questions

- Where the triage-decision schema should live (module/file name) and how it validates (pydantic model, dataclass, hand-written checks, or a JSON Schema file) isn't specified by `INTENT.md` — but Epic 2 (CAP-4) and Epic 3 (CAP-2) both already reference validating against "the Epic 1 schema" as a reusable artifact, so this epic needs to give it a concrete, importable location and API.
