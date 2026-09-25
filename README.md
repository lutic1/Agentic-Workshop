# Agentic AI Workshop

The VSF Club two-day workshop repo. On Saturday you spec, build and measure a support-ticket triage agent with your coding agent and BMad. On Sunday you do the same for a business case of your own choice.

## Start here

Open your coding agent (Claude Code, Codex, Copilot CLI or Cursor) in any folder and ask:

> Fork and clone github.com/lutic1/Agentic-Workshop, then install everything it needs.

Then reopen your agent inside the new `Agentic-Workshop` folder and ask:

> What are the rules for this repo?

If the answer ends with “— VSF”, your tool is reading `AGENTS.md` and you're ready.

You need `uv`, `git`, a GitHub account and a free Gemini API key. Copy `.env.example` to `.env` and paste your keys there. A Groq key is the backup for when Gemini's free tier runs out.

## What you build on Saturday

| Epic | What it adds | Spec |
|---|---|---|
| 1 | The triage decision schema, and a loader that puts `seed/` into SQLite | You write it from `INTENT.md` with `/bmad-spec` |
| 2 | A LangChain agent that calls `mcp/triage_server.py`, with a person approving escalations | `_bmad-output/specs/spec-epic-2/` |
| 3 | An MLflow eval over 20 labelled tickets: four code checks, one LLM judge and a token report | `_bmad-output/specs/spec-epic-3/` |

Every story goes through the same loop: build it with `/bmad-build`, review it with `/bmad-code-review` in a fresh chat, and merge only on a pass.

## Behind? Switch branch

Each block has a finished checkpoint. Ask your agent to switch you to it:

| Branch | Contains |
|---|---|
| `stage-1` | The Epic 1 spec and stories |
| `stage-2` | Epic 1 built: schema and loader |
| `stage-3` | Epic 2 built: the agent, its MCP tools and the approval gate |
| `stage-4` | Epic 3 built: the eval, the judge and the token report |

## What's here

- `AGENTS.md`: the rules every coding agent reads. `CLAUDE.md` and `GEMINI.md` point to it.
- `INTENT.md`: the intent for Epic 1.
- `TRIAGE_POLICY.md`: the categories, priorities and escalation rule the agent follows.
- `seed/`: the tickets and customers the agent triages.
- `eval/labelled_tickets.csv`: 20 tickets labelled by hand, including T-1099, which tries a prompt injection.
- `mcp/triage_server.py`: the MCP server with `get_ticket` and `get_customer_history`.
- `run_agent.py`: runs the agent on one ticket, with MLflow tracing on.
- `_bmad/`, `.claude/skills/`, `.agents/skills/`: BMad 6.12, installed for Claude Code, Codex, Copilot and Cursor.
