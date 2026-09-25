"""Evaluate the triage agent on the 20 labelled tickets (Epic 3).

Usage: uv run python eval/run_eval.py
Logs one MLflow run, prints each scorer's mean and the agent's tokens, and writes eval/latest_report.json.
"""

import asyncio
import csv
import json
import os
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("MLFLOW_GENAI_EVAL_MAX_WORKERS", "2")  # stay under free-tier rate limits

import mlflow  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from mlflow.entities import Feedback, SpanType  # noqa: E402
from mlflow.genai.scorers import scorer  # noqa: E402
from pydantic import BaseModel, Field, ValidationError  # noqa: E402

from agent import triage  # noqa: E402
from triage.schema import TriageDecision  # noqa: E402

LABELS = ROOT / "eval" / "labelled_tickets.csv"
REPORT = ROOT / "eval" / "latest_report.json"
TOOLS = ("get_ticket", "get_customer_history")

_escalations: list[dict] = []
_lock = threading.Lock()


def approve_automatically(request: dict) -> bool:
    """Evals never wait for a person: approve every escalation and count it."""
    with _lock:
        _escalations.append(request["args"])
    return True


@mlflow.trace(name="triage", span_type=SpanType.AGENT)
def predict(ticket_id: str) -> dict:
    """One trace per ticket, so an approved escalation stays in the same trace as the tool calls."""
    return asyncio.run(triage(ticket_id, approve=approve_automatically))


def load_eval_set() -> list[dict]:
    with LABELS.open(newline="", encoding="utf-8") as handle:
        return [
            {
                "inputs": {"ticket_id": row["ticket_id"]},
                "expectations": {
                    "category": row["expected_category"],
                    "priority": row["expected_priority"],
                    "judge_notes": row["judge_notes"],
                },
            }
            for row in csv.DictReader(handle)
        ]


@scorer
def valid_schema(outputs) -> Feedback:
    try:
        TriageDecision.model_validate(outputs)
        return Feedback(value=True)
    except ValidationError as error:
        return Feedback(value=False, rationale=str(error))


@scorer
def category_match(outputs, expectations) -> bool:
    return outputs.get("category") == expectations["category"]


@scorer
def priority_match(outputs, expectations) -> bool:
    return outputs.get("priority") == expectations["priority"]


@scorer
def tool_order(trace) -> Feedback:
    spans = sorted(trace.data.spans, key=lambda span: span.start_time_ns)
    calls = [span.name for span in spans if span.span_type == SpanType.TOOL and span.name in TOOLS]
    in_order = TOOLS[0] in calls and TOOLS[1] in calls and calls.index(TOOLS[0]) < calls.index(TOOLS[1])
    return Feedback(value=in_order, rationale=f"Tool calls: {', '.join(calls) or 'none'}")


class Verdict(BaseModel):
    passed: bool = Field(description="True if the rationale is sound and consistent with the notes.")
    reason: str = Field(description="One line explaining the verdict.")


def _judge():
    from langchain_groq import ChatGroq

    model = ChatGroq(model=os.getenv("JUDGE_MODEL", "openai/gpt-oss-120b"), temperature=0, api_key=os.environ["GROQ_API_KEY"])
    return model.with_structured_output(Verdict)


@scorer
def rationale_judge(inputs, outputs, expectations) -> Feedback:
    prompt = (
        "You grade a support-ticket triage agent. Decide whether its rationale is sound given the reviewer's notes.\n\n"
        f"Ticket: {inputs['ticket_id']}\n"
        f"Decision: {outputs.get('category')}, {outputs.get('priority')}, {outputs.get('route')}\n"
        f"Rationale: {outputs.get('rationale')}\n"
        f"Reviewer's notes: {expectations['judge_notes']}\n"
    )
    verdict = _judge().invoke(prompt)
    return Feedback(value=verdict.passed, rationale=verdict.reason)


def agent_tokens(run_id: str) -> int:
    traces = mlflow.search_traces(run_id=run_id, return_type="list")
    return sum((trace.info.token_usage or {}).get("total_tokens", 0) for trace in traces)


def main() -> None:
    load_dotenv(ROOT / ".env")
    mlflow.set_tracking_uri(f"sqlite:///{ROOT / 'mlflow.db'}")
    mlflow.set_experiment("triage-agent")
    mlflow.langchain.autolog()

    scorers = [valid_schema, category_match, priority_match, tool_order, rationale_judge]
    results = mlflow.genai.evaluate(data=load_eval_set(), predict_fn=predict, scorers=scorers)

    scores = {s.name: results.metrics.get(f"{s.name}/mean") for s in scorers}
    report = {"run_id": results.run_id, "tickets": 20, "scores": scores, "agent_tokens": agent_tokens(results.run_id), "escalations": len(_escalations)}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"\nEval run {results.run_id}")
    for name, value in scores.items():
        print(f"  {name:<16} {value if value is not None else 'n/a'}")
    print(f"  agent tokens     {report['agent_tokens']:,}")
    print(f"  escalations      {report['escalations']}")
    print(f"Report written to {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
