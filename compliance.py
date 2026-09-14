"""Supporting process — the compliance calendar. Renewals and filings that would otherwise
silently expire."""
from __future__ import annotations

import json
from datetime import date, timedelta

from strands import tool

from .. import rules
from ..store import get_store
from .decisions import raise_decision


@tool
def add_compliance_item(name: str, due_iso: str, kind: str = "filing", notes: str = "") -> str:
    """Add an item to the compliance calendar. kind: filing | renewal | tax | license."""
    s = get_store()
    row = {"id": s.new_id("CMP"), "name": name, "due": due_iso, "kind": kind, "notes": notes, "status": "open"}
    s.insert("compliance", row)
    return json.dumps(row)


@tool
def upcoming_compliance(days: int = rules.COMPLIANCE_LOOKAHEAD_DAYS) -> str:
    """List compliance items due within N days. Items due within 7 days raise a compliance_due decision
    so the owner confirms it is handled. Returns JSON."""
    s = get_store()
    horizon = s.today + timedelta(days=days)
    rows = [c for c in s.find("compliance", status="open") if date.fromisoformat(c["due"]) <= horizon]
    for c in rows:
        if (date.fromisoformat(c["due"]) - s.today).days <= 7:
            raise_decision("compliance_due", f"{c['name']} ({c['kind']}) is due {c['due']}. Confirm it is handled.",
                           ["done", "need_help", "snooze_7_days"], {"compliance_id": c["id"]})
    return json.dumps(sorted(rows, key=lambda c: c["due"]), indent=2) if rows else "Nothing due in that window."


@tool
def mark_compliance_done(item_id: str) -> str:
    """Mark a compliance item complete."""
    s = get_store()
    s.update("compliance", item_id, status="done", completed=s.today.isoformat())
    return f"{item_id} marked done."
