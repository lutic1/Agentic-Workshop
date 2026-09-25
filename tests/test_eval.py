"""Runs the real eval pipeline on three tickets with a scripted agent model and a stub judge."""

import asyncio
import importlib.util
from pathlib import Path

import mlflow
import pytest

import agent
import load_seed
from test_agent import scripted

RUN_EVAL = Path(__file__).resolve().parent.parent / "eval" / "run_eval.py"
CUSTOMERS = {"T-1042": "C-77", "T-1045": "C-33", "T-1044": "C-91"}


@pytest.fixture
def run_eval(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("run_eval", RUN_EVAL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    load_seed.load()
    mlflow.set_tracking_uri(f"sqlite:///{tmp_path / 'mlflow.db'}")
    mlflow.set_experiment("triage-agent-test")
    mlflow.langchain.autolog()

    class StubJudge:
        def invoke(self, prompt):
            return module.Verdict(passed="Rationale:" in prompt, reason="stub judge")

    monkeypatch.setattr(module, "_judge", lambda: StubJudge())
    return module


def test_scorers_on_real_traces(run_eval):
    rows = [row for row in run_eval.load_eval_set() if row["inputs"]["ticket_id"] in CUSTOMERS]
    answers = {
        "T-1042": {"category": "billing", "priority": "P2", "route": "billing-team", "rationale": "A double charge is a money problem."},
        "T-1045": {"category": "billing", "priority": "P3", "route": "billing-team", "rationale": "Changing the billing period is a detail change."},
        "T-1044": {"category": "access", "priority": "P1", "route": "access-team", "rationale": "A whole team is locked out."},
    }

    @mlflow.trace(name="triage", span_type="AGENT")
    def predict(ticket_id: str) -> dict:
        model = scripted(ticket_id, CUSTOMERS[ticket_id], answers[ticket_id], escalate=ticket_id == "T-1044")
        return asyncio.run(agent.triage(ticket_id, approve=run_eval.approve_automatically, model=model))

    scorers = [run_eval.valid_schema, run_eval.category_match, run_eval.priority_match, run_eval.tool_order, run_eval.rationale_judge]
    results = mlflow.genai.evaluate(data=rows, predict_fn=predict, scorers=scorers)

    assert results.metrics["valid_schema/mean"] == 1.0
    assert results.metrics["category_match/mean"] == 1.0
    assert results.metrics["priority_match/mean"] == pytest.approx(2 / 3)
    assert results.metrics["tool_order/mean"] == 1.0
    assert results.metrics["rationale_judge/mean"] == 1.0
    assert len(run_eval._escalations) == 1
    assert run_eval.agent_tokens(results.run_id) >= 0
