"""Phase 2 — receivables. Invoices come from system events, never from typing;
the reminder ladder runs itself and escalates at day 45."""
from __future__ import annotations

import json
from datetime import date, timedelta

from strands import tool

from .. import rules
from ..store import get_store
from .decisions import raise_decision


def _issue(s, contact_id: str, kind: str, amount: float, memo: str, source_id: str) -> dict:
    terms = rules.PAYMENT_TERMS_DAYS[kind]
    row = {"id": s.new_id("INV"), "contact_id": contact_id, "kind": kind, "amount": round(amount, 2), "paid": 0.0,
           "memo": memo, "source_id": source_id, "issued": s.today.isoformat(),
           "due": (s.today + timedelta(days=terms)).isoformat(), "status": "open", "ladder_step": 0}
    s.insert("invoices", row)
    s.audit("receivables", "invoice_issued", f"{row['id']} ${amount:.2f} {kind} <- {source_id}")
    return row


@tool
def generate_invoices_from_events() -> str:
    """Turn every completed billable event and every no-show into an invoice (idempotent:
    each event is invoiced once). Returns the invoices created."""
    s = get_store()
    made = []
    for e in s.find("events"):
        if e.get("invoiced") or e["status"] not in ("completed", "no_show"):
            continue
        bt = rules.BOOKING_TYPES[e["type"]]
        contact = s.get("contacts", e["contact_id"])
        if e["status"] == "completed" and e.get("billable"):
            made.append(_issue(s, e["contact_id"], "event", bt.rate, f"{bt.name} on {e['start'][:10]}", e["id"]))
        elif e["status"] == "no_show" and contact.get("no_show_fee", True) and rules.NO_SHOW_FEE > 0:
            made.append(_issue(s, e["contact_id"], "no_show", rules.NO_SHOW_FEE, f"Missed {bt.name} on {e['start'][:10]}", e["id"]))
        s.update("events", e["id"], invoiced=True)
    return json.dumps(made, indent=2) if made else "No new invoices needed."


@tool
def issue_retainer_invoices() -> str:
    """On the first business day of the month, invoice every retainer client. Idempotent per month."""
    s = get_store()
    t = s.today
    if t.day > 3:
        return "Not the start of the month; nothing issued."
    made = []
    for c in s.find("contacts"):
        amt = c.get("retainer", 0)
        if not amt:
            continue
        tag = f"retainer-{t.strftime('%Y-%m')}-{c['id']}"
        if s.find("invoices", source_id=tag):
            continue
        made.append(_issue(s, c["id"], "retainer", amt, f"Monthly retainer {t.strftime('%B %Y')}", tag))
    return json.dumps(made, indent=2) if made else "Retainers already issued this month."


@tool
def run_reminder_ladder() -> str:
    """Advance every open invoice along the reminder ladder based on days since issue
    (day 7 friendly, 14 direct, 16 email+sms, 30 formal; day 45 escalates to a human decision).
    Paused for disputed invoices. Simulated sends. Returns what was sent or escalated."""
    s = get_store()
    out = []
    for inv in s.find("invoices", status="open"):
        age = (s.today - date.fromisoformat(inv["issued"])).days
        if inv.get("disputed"):
            continue
        for step, (day, channel, tone) in enumerate(rules.REMINDER_LADDER, start=1):
            if age >= day and inv["ladder_step"] < step:
                s.insert("reminders", {"invoice_id": inv["id"], "day": day, "channel": channel, "tone": tone, "sent": s.today.isoformat()})
                s.update("invoices", inv["id"], ladder_step=step)
                out.append(f"{inv['id']} day-{day} {tone} {channel}")
        if age >= rules.ESCALATE_AT_DAY:
            c = s.get("contacts", inv["contact_id"])
            d = raise_decision("collections_escalation",
                               f"{c['name']} owes ${inv['amount'] - inv['paid']:.2f} on {inv['id']}, {age} days old. How do you want to handle it?",
                               ["payment_plan", "pause_service", "write_off", "keep_waiting"], {"invoice_id": inv["id"]})
            out.append(f"{inv['id']} escalated -> {d['id']}")
    return "Ladder: " + (", ".join(out) if out else "nothing due")


@tool
def record_payment(invoice_id: str, amount: float, method: str = "card") -> str:
    """Apply a payment to an invoice. Partial payments keep it open and restart the ladder at day 7."""
    s = get_store()
    inv = s.get("invoices", invoice_id)
    if inv is None:
        return f"No invoice {invoice_id}"
    paid = round(inv["paid"] + amount, 2)
    status = "paid" if paid >= inv["amount"] else "open"
    s.update("invoices", invoice_id, paid=paid, status=status, ladder_step=0 if status == "open" else inv["ladder_step"])
    s.insert("payments", {"id": s.new_id("PAY"), "invoice_id": invoice_id, "amount": amount, "method": method, "on": s.today.isoformat()})
    s.audit("receivables", "payment", f"{invoice_id} ${amount:.2f} via {method} -> {status}")
    return f"{invoice_id}: paid ${paid:.2f} of ${inv['amount']:.2f}; status {status}."


@tool
def ar_aging() -> str:
    """Accounts-receivable aging in 0-15 / 16-30 / 31-45 / over 45 buckets plus days-sales-outstanding.
    Flags anything over the alert thresholds. Returns JSON."""
    s = get_store()
    buckets = {"0_15": 0.0, "16_30": 0.0, "31_45": 0.0, "over_45": 0.0}
    open_amt, weighted = 0.0, 0.0
    for inv in s.find("invoices", status="open"):
        bal = inv["amount"] - inv["paid"]
        age = (s.today - date.fromisoformat(inv["issued"])).days
        key = "0_15" if age <= 15 else "16_30" if age <= 30 else "31_45" if age <= 45 else "over_45"
        buckets[key] += bal; open_amt += bal; weighted += bal * age
    dso = round(weighted / open_amt, 1) if open_amt else 0.0
    alerts = []
    if buckets["over_45"]:
        alerts.append(f"${buckets['over_45']:.2f} over 45 days")
    if dso > rules.DSO_ALERT_DAYS:
        alerts.append(f"DSO {dso} above {rules.DSO_ALERT_DAYS}")
    return json.dumps({"buckets": {k: round(v, 2) for k, v in buckets.items()}, "open_total": round(open_amt, 2), "dso_days": dso, "alerts": alerts})
