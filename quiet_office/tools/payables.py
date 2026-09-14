"""Phase 4 — payables. Bills are captured, small known-vendor bills are paid automatically,
everything else waits for a one-tap approval."""
from __future__ import annotations

import json
from datetime import date, timedelta

from strands import tool

from .. import rules
from ..store import get_store
from .decisions import raise_decision


@tool
def capture_bill(vendor: str, amount: float, due_iso: str, memo: str = "") -> str:
    """Record a vendor bill from email or upload. Known vendors under the auto-pay limit are approved
    automatically; new vendors or larger amounts raise a payment_approval decision."""
    s = get_store()
    known = any(b["vendor"].lower() == vendor.lower() and b["status"] == "paid" for b in s.find("bills"))
    row = {"id": s.new_id("BILL"), "vendor": vendor, "amount": round(amount, 2), "due": due_iso, "memo": memo,
           "received": s.today.isoformat(), "status": "pending"}
    s.insert("bills", row)
    if known and amount <= rules.AUTO_PAY_LIMIT:
        s.update("bills", row["id"], status="approved")
        s.audit("payables", "auto_approved", f"{row['id']} {vendor} ${amount:.2f}")
        return f"{row['id']} auto-approved (known vendor, under ${rules.AUTO_PAY_LIMIT:.0f})."
    why = "first-time vendor" if not known else f"over the ${rules.AUTO_PAY_LIMIT:.0f} auto-pay limit"
    d = raise_decision("payment_approval", f"Pay {vendor} ${amount:.2f} due {due_iso}? ({why}) {memo}".strip(),
                       ["approve", "reject"], {"bill_id": row["id"]})
    return f"{row['id']} needs approval ({why}) -> {d['id']}"


def _auto_approve_pending(s) -> list[str]:
    """Known vendors under the auto-pay limit are approved without a human; the rest raise a decision."""
    out = []
    paid_vendors = {b["vendor"].lower() for b in s.find("bills", status="paid")}
    for b in s.find("bills", status="pending"):
        if b["vendor"].lower() in paid_vendors and b["amount"] <= rules.AUTO_PAY_LIMIT:
            s.update("bills", b["id"], status="approved")
            s.audit("payables", "auto_approved", f"{b['id']} {b['vendor']} ${b['amount']:.2f}")
            out.append(b["id"])
        else:
            why = "first-time vendor" if b["vendor"].lower() not in paid_vendors else f"over the ${rules.AUTO_PAY_LIMIT:.0f} auto-pay limit"
            raise_decision("payment_approval", f"Pay {b['vendor']} ${b['amount']:.2f} due {b['due']}? ({why}) {b.get('memo','')}".strip(),
                           ["approve", "reject"], {"bill_id": b["id"]})
    return out


@tool
def bills_due(days: int = 14) -> str:
    """List bills due within N days with their approval status. Returns JSON."""
    s = get_store()
    _auto_approve_pending(s)
    horizon = s.today + timedelta(days=days)
    rows = [b for b in s.find("bills") if b["status"] in ("pending", "approved") and date.fromisoformat(b["due"]) <= horizon]
    return json.dumps(sorted(rows, key=lambda b: b["due"]), indent=2) if rows else "No bills due in that window."


@tool
def pay_bill(bill_id: str) -> str:
    """Pay a single approved bill (simulated ACH). This is a money-moving tool: the approval gate
    refuses it for bills that a human has not approved."""
    s = get_store()
    b = s.get("bills", bill_id)
    if b is None:
        return f"No bill {bill_id}"
    if b["status"] != "approved":
        return f"Refused: {bill_id} is {b['status']}, not approved."
    s.update("bills", bill_id, status="paid", paid_on=s.today.isoformat())
    s.insert("transactions", {"id": s.new_id("TXN"), "date": s.today.isoformat(), "amount": -b["amount"],
                              "description": f"ACH {b['vendor']}", "status": "categorized", "category": "Accounts payable"})
    s.audit("payables", "paid", f"{bill_id} {b['vendor']} ${b['amount']:.2f}")
    return f"Paid {bill_id} {b['vendor']} ${b['amount']:.2f}."


@tool
def run_payment_run() -> str:
    """Pay every approved bill due within 7 days in one batch. Pending (unapproved) bills are skipped and listed."""
    s = get_store()
    _auto_approve_pending(s)
    horizon = s.today + timedelta(days=7)
    paid, skipped = [], []
    for b in s.find("bills"):
        if date.fromisoformat(b["due"]) > horizon or b["status"] not in ("approved", "pending"):
            continue
        if b["status"] == "approved":
            paid.append(pay_bill(bill_id=b["id"]))  # direct call; still guarded by status check
        else:
            skipped.append(f"{b['id']} {b['vendor']} awaiting approval")
    return json.dumps({"paid": paid, "skipped": skipped})
