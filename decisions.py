"""The decision inbox: the only place the office talks to a human."""
from __future__ import annotations

import json

from strands import tool

from ..store import get_store


def raise_decision(kind: str, summary: str, options: list[str], context: dict | None = None) -> dict:
    """Create a pending decision. Called by tools and by the approval-gate hook. Idempotent on (kind, summary)."""
    s = get_store()
    for d in s.find("decisions", kind=kind, summary=summary, status="open"):
        return d
    row = {"id": s.new_id("DEC"), "kind": kind, "summary": summary, "options": options,
           "context": context or {}, "status": "open", "created": s.today.isoformat(), "resolution": None}
    s.insert("decisions", row)
    s.audit("office", "decision_raised", f"{row['id']} {kind}: {summary}")
    return row


@tool
def list_open_decisions() -> str:
    """List every decision waiting on a human, with its options. Use this to build the digest
    that is sent to the owner. Returns JSON."""
    s = get_store()
    return json.dumps(s.find("decisions", status="open"), indent=2)


@tool
def resolve_decision(decision_id: str, choice: str, note: str = "") -> str:
    """Record the human's choice on a decision and apply its effect
    (e.g. approving a bill releases it for the next pay run; choosing a category books the transaction).
    choice must be one of the decision's options."""
    s = get_store()
    d = s.get("decisions", decision_id)
    if d is None:
        return f"No decision {decision_id}"
    if choice not in d["options"]:
        return f"Choice must be one of {d['options']}"
    s.update("decisions", decision_id, status="resolved", resolution={"choice": choice, "note": note, "on": s.today.isoformat()})
    ctx = d.get("context", {})
    effect = "recorded"
    if d["kind"] == "payment_approval":
        bill = s.get("bills", ctx.get("bill_id", ""))
        if bill:
            s.update("bills", bill["id"], status="approved" if choice == "approve" else "rejected")
            effect = f"bill {bill['id']} {bill['status']}"
    elif d["kind"] == "uncategorized_transaction":
        txn = s.get("transactions", ctx.get("transaction_id", ""))
        if txn:
            s.update("transactions", txn["id"], category=choice, status="categorized")
            effect = f"transaction {txn['id']} booked to {choice}"
    elif d["kind"] == "collections_escalation":
        inv = s.get("invoices", ctx.get("invoice_id", ""))
        if inv:
            new = {"payment_plan": "payment_plan", "pause_service": "paused", "write_off": "written_off"}.get(choice, inv["status"])
            s.update("invoices", inv["id"], status=new)
            effect = f"invoice {inv['id']} -> {new}"
    elif d["kind"] == "no_show_pause":
        c = s.get("contacts", ctx.get("contact_id", ""))
        if c:
            s.update("contacts", c["id"], booking_paused=(choice == "pause"))
            effect = f"contact {c['id']} booking_paused={c['booking_paused']}"
    s.audit("human", "decision_resolved", f"{decision_id} -> {choice}; {effect}")
    return f"Decision {decision_id} resolved: {choice}. Effect: {effect}."
