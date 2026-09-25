"""MCP server that gives the triage agent read access to app.db over stdio."""

import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP

DB_PATH = Path(__file__).resolve().parent.parent / "app.db"

server = FastMCP("triage", log_level="WARNING")


def _query(sql: str, *params: str) -> list[dict]:
    if not DB_PATH.exists():
        raise FileNotFoundError("app.db not found. Load the data first: uv run python load_seed.py")
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute(sql, params)]


@server.tool()
def get_ticket(ticket_id: str) -> dict:
    """Return one support ticket by its ID (for example T-1042): the customer_id, when it was created and the customer's text."""
    rows = _query("SELECT ticket_id, customer_id, created_at, text FROM tickets WHERE ticket_id = ?", ticket_id)
    if not rows:
        raise ValueError(f"No ticket with ID {ticket_id}")
    return rows[0]


@server.tool()
def get_customer_history(customer_id: str) -> dict:
    """Return a customer's plan and open ticket count, plus the IDs of their other tickets. Needs the customer_id from get_ticket."""
    rows = _query("SELECT customer_id, name, plan, open_tickets FROM customers WHERE customer_id = ?", customer_id)
    if not rows:
        raise ValueError(f"No customer with ID {customer_id}")
    customer = rows[0]
    customer["ticket_ids"] = [r["ticket_id"] for r in _query("SELECT ticket_id FROM tickets WHERE customer_id = ?", customer_id)]
    return customer


if __name__ == "__main__":
    server.run()
