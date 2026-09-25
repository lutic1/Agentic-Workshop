"""Triage one support ticket with the agent and print the decision.

Usage: uv run python run_agent.py T-1042
"""

import asyncio
import json
import sys

import mlflow
from dotenv import load_dotenv


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: uv run python run_agent.py <ticket_id>")
    ticket_id = sys.argv[1]

    load_dotenv()
    mlflow.set_tracking_uri("sqlite:///mlflow.db")
    mlflow.set_experiment("triage-agent")
    mlflow.langchain.autolog()

    try:
        from agent import triage
    except ImportError:
        raise SystemExit("The agent isn't built yet. That's Epic 2: _bmad-output/specs/spec-epic-2/SPEC.md")

    with mlflow.start_span(name="triage", span_type="AGENT") as span:
        span.set_inputs({"ticket_id": ticket_id})
        decision = asyncio.run(triage(ticket_id))
        span.set_outputs(decision)
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    main()
