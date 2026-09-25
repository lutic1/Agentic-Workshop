"""Agent wiring tests with a scripted model: real MCP tools, real approval gate, no API keys."""

import asyncio

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

import agent
import load_seed

BILLING = {"category": "billing", "priority": "P2", "route": "billing-team", "rationale": "A double charge is a money problem."}
OUTAGE = {"category": "access", "priority": "P1", "route": "access-team", "rationale": "A whole team locked out is an outage for an Enterprise customer."}


class ScriptedModel(GenericFakeChatModel):
    """Replays a fixed list of model turns, whatever tools it's given."""

    def bind_tools(self, tools, **kwargs):
        return self


def _call(name, args, call_id):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id, "type": "tool_call"}])


def scripted(ticket_id, customer_id, decision, escalate=False):
    turns = [_call("get_ticket", {"ticket_id": ticket_id}, "1"), _call("get_customer_history", {"customer_id": customer_id}, "2")]
    if escalate:
        turns.append(_call("escalate_to_human", {"ticket_id": ticket_id, "reason": "P1 for an Enterprise customer"}, "3"))
    turns.append(_call("TriageDecision", decision, "4"))
    return ScriptedModel(messages=iter(turns))


@pytest.fixture(scope="module", autouse=True)
def app_db():
    load_seed.load()


def test_triage_returns_the_schema_after_both_tool_calls():
    decision = asyncio.run(agent.triage("T-1042", approve=lambda _: pytest.fail("no escalation expected"), model=scripted("T-1042", "C-77", BILLING)))
    assert decision == BILLING


def test_escalation_waits_for_a_person():
    asked = []
    decision = asyncio.run(agent.triage("T-1044", approve=lambda r: asked.append(r["args"]) or True, model=scripted("T-1044", "C-91", OUTAGE, escalate=True)))
    assert asked == [{"ticket_id": "T-1044", "reason": "P1 for an Enterprise customer"}]
    assert decision["priority"] == "P1"


def test_a_declined_escalation_still_returns_a_decision():
    decision = asyncio.run(agent.triage("T-1044", approve=lambda _: False, model=scripted("T-1044", "C-91", OUTAGE, escalate=True)))
    assert decision == OUTAGE


def test_provider_switch(monkeypatch):
    monkeypatch.setenv("PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.delenv("MODEL", raising=False)
    model = agent.build_model()
    assert type(model).__name__ == "ChatGroq"
    assert model.model_name == "openai/gpt-oss-120b"


def test_gemini_is_the_default(monkeypatch):
    monkeypatch.delenv("PROVIDER", raising=False)
    monkeypatch.delenv("MODEL", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    model = agent.build_model()
    assert type(model).__name__ == "ChatGoogleGenerativeAI"
    assert model.model.endswith("gemini-3.8-flash")
