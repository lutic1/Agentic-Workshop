"""The triage agent (Epic 2): a LangChain agent on Gemini or Groq, with MCP tools and an approval gate."""

import os
import sys
from collections.abc import Callable
from pathlib import Path

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain.agents.structured_output import ToolStrategy
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from triage.schema import TriageDecision, TriageValidationError

ROOT = Path(__file__).resolve().parent
MCP_SERVERS = {
    "triage": {"command": sys.executable, "args": [str(ROOT / "mcp" / "triage_server.py")], "transport": "stdio"},
}
SYSTEM_PROMPT = (ROOT / "TRIAGE_POLICY.md").read_text(encoding="utf-8") + """
## How to work

1. Call get_ticket with the ticket ID.
2. Call get_customer_history with the customer_id that get_ticket returned.
3. Apply the policy. If it says to escalate, call escalate_to_human.
4. Return the decision.
"""

Approver = Callable[[dict], bool]


def build_model() -> BaseChatModel:
    """Gemini by default; PROVIDER=groq switches to Groq. MODEL overrides the model name."""
    if os.getenv("PROVIDER", "gemini").lower() == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(model=os.getenv("MODEL", "openai/gpt-oss-120b"), temperature=0)
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(model=os.getenv("MODEL", "gemini-3.8-flash"), temperature=0)


@tool
def escalate_to_human(ticket_id: str, reason: str) -> str:
    """Page the on-call person about a ticket. Only when the policy says to escalate: a P1 for an Enterprise customer."""
    return f"Escalated {ticket_id} to the on-call person: {reason}"


def ask_at_terminal(request: dict) -> bool:
    """Ask the person at the terminal to approve one escalation."""
    args = request["args"]
    answer = input(f"\nEscalate {args.get('ticket_id')} to a person? Reason: {args.get('reason')}\nApprove? [y/N] ")
    return answer.strip().lower() in {"y", "yes"}


def _retry_once() -> Callable[[Exception], str]:
    """Let the model fix one invalid decision; a second invalid one stops the run with a clear error."""
    failures = 0

    def handle(error: Exception) -> str:
        nonlocal failures
        failures += 1
        if failures > 1:
            raise TriageValidationError(f"The decision failed validation twice: {error}") from error
        return f"That decision failed validation: {error}. Fix it and return the decision again."

    return handle


async def build_agent(model: BaseChatModel | None = None):
    tools = await MultiServerMCPClient(MCP_SERVERS).get_tools()
    return create_agent(
        model or build_model(),
        [*tools, escalate_to_human],
        system_prompt=SYSTEM_PROMPT,
        response_format=ToolStrategy(TriageDecision, handle_errors=_retry_once()),
        middleware=[HumanInTheLoopMiddleware(interrupt_on={"escalate_to_human": {"allowed_decisions": ["approve", "reject"]}})],
        checkpointer=InMemorySaver(),
    )


async def triage(ticket_id: str, approve: Approver = ask_at_terminal, model: BaseChatModel | None = None) -> dict:
    """Triage one ticket and return a decision that matches the Epic 1 schema."""
    agent = await build_agent(model)
    config = {"configurable": {"thread_id": ticket_id}}
    state = await agent.ainvoke({"messages": [{"role": "user", "content": f"Triage ticket {ticket_id}."}]}, config)
    while state.get("__interrupt__"):
        requests = state["__interrupt__"][0].value["action_requests"]
        decisions = [
            {"type": "approve"} if approve(request) else {"type": "reject", "message": "A person declined the escalation."}
            for request in requests
        ]
        state = await agent.ainvoke(Command(resume={"decisions": decisions}), config)
    return state["structured_response"].model_dump()
