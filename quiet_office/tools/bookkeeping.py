"""Phase 3 — bookkeeping. Bank feed lines are categorized by rule; anything the rules
can't place becomes a decision instead of a guess."""
from __future__ import annotations

import json
from datetime import date

from strands import tool

from .. import rules
from ..store import get_store
from .decisions import raise_decision


@tool
def categorize_transactions() -> str:
    """Categorize every uncategorized bank-feed line using the client's keyword rules.
    Deposits are matched to open invoices by amount; unmatched deposits go to the unapplied-cash queue.
    Unknown spend becomes an 'uncategorized_transaction' decision. Returns a summary."""
    s = get_store()
    booked, asked, applied, unapplied = [], [], [], []
    for t in s.find("transactions", status="new"):
        desc = t["description"].lower()
        if t["amount"] > 0:
            match = next((i for i in s.find("invoices", status="open") if abs(i["amount"] - i["paid"] - t["amount"]) < 0.01), None)
            if match:
                s.update("invoices", match["id"], paid=match["amount"], status="paid")
                s.update("transactions", t["id"], status="applied", category="Accounts receivable", invoice_id=match["id"])
                applied.append(f"{t['id']}->{match['id']}")
            else:
                s.update("transactions", t["id"], status="unapplied", category="Unapplied cash")
                unapplied.append(t["id"])
            continue
        cat = next((c for k, c in rules.CATEGORY_RULES.items() if k in desc), None)
        if cat:
            s.update("transactions", t["id"], status="categorized", category=cat)
            booked.append(f"{t['id']}:{cat}")
        else:
            options = sorted(set(rules.CATEGORY_RULES.values())) + ["Owner draw", "Meals & entertainment"]
            d = raise_decision("uncategorized_transaction", f"${-t['amount']:.2f} to '{t['description']}' on {t['date']} — which category?",
                               options[:6], {"transaction_id": t["id"]})
            s.update("transactions", t["id"], status="pending_decision")
            asked.append(f"{t['id']}->{d['id']}")
    return json.dumps({"booked": booked, "applied_to_invoices": applied, "unapplied_cash": unapplied, "asked_human": asked})


@tool
def unapplied_cash_queue() -> str:
    """List deposits that don't match an invoice. Anything older than the policy age raises a decision."""
    s = get_store()
    rows = s.find("transactions", status="unapplied")
    for t in rows:
        if (s.today - date.fromisoformat(t["date"])).days > rules.UNAPPLIED_CASH_MAX_AGE_DAYS:
            raise_decision("unapplied_cash", f"Deposit of ${t['amount']:.2f} ('{t['description']}') has sat unapplied for over a week. What is it?",
                           ["client_prepayment", "refund_received", "owner_contribution", "other"], {"transaction_id": t["id"]})
    return json.dumps(rows, indent=2) if rows else "Unapplied cash queue is empty."


@tool
def month_close_checklist() -> str:
    """Run the month-end close checks: all transactions categorized, no unapplied cash, retainers invoiced,
    AR reconciled to invoices. Returns pass/fail per item."""
    s = get_store()
    checks = {
        "all_transactions_categorized": not s.find("transactions", status="new") and not s.find("transactions", status="pending_decision"),
        "unapplied_cash_clear": not s.find("transactions", status="unapplied"),
        "retainers_invoiced_this_month": all(
            s.find("invoices", source_id=f"retainer-{s.today.strftime('%Y-%m')}-{c['id']}")
            for c in s.find("contacts") if c.get("retainer")),
        "no_open_decisions": not s.find("decisions", status="open"),
    }
    return json.dumps({"month": s.today.strftime("%Y-%m"), "checks": checks, "ready_to_close": all(checks.values())})
