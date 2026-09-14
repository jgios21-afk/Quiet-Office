"""Phase 5 — reception. Inbound calls, emails and chats are triaged against the CRM;
known people get routed, strangers get a polite hold and a decision."""
from __future__ import annotations

import json

from strands import tool

from ..store import get_store
from .decisions import raise_decision

SPAM_HINTS = ("seo", "extended warranty", "guaranteed ranking", "crypto", "lottery")


@tool
def lookup_contact(name_or_email: str) -> str:
    """Find a contact by name or email (case-insensitive substring). Returns JSON list."""
    q = name_or_email.lower()
    hits = [c for c in get_store().find("contacts") if q in c["name"].lower() or q in c.get("email", "").lower()]
    return json.dumps(hits, indent=2) if hits else "No matching contact."


@tool
def create_contact(name: str, email: str, kind: str = "lead", organization: str = "") -> str:
    """Create a CRM contact. kind: client | lead | vendor."""
    s = get_store()
    row = {"id": s.new_id("CON"), "name": name, "email": email, "kind": kind, "organization": organization,
           "no_shows": 0, "booking_paused": False, "retainer": 0}
    s.insert("contacts", row)
    return json.dumps(row)


@tool
def triage_inbound(channel: str, sender: str, message: str) -> str:
    """Triage one inbound call/email/chat. Returns a routing decision:
    known client -> 'route_to_owner' or 'book_working_session'; vendor -> 'forward_to_payables';
    new lead -> 'offer_intake_call'; likely spam -> 'discard'; unclear -> raises an unknown_caller decision."""
    s = get_store()
    text = message.lower()
    hits = [c for c in s.find("contacts") if sender.lower() in c.get("email", "").lower() or sender.lower() in c["name"].lower()]
    contact = hits[0] if hits else None
    if any(h in text for h in SPAM_HINTS):
        route, reason = "discard", "matched spam patterns"
    elif contact and contact["kind"] == "client":
        route = "book_working_session" if any(w in text for w in ("meet", "schedule", "session", "call")) else "route_to_owner"
        reason = f"known client {contact['name']}"
    elif contact and contact["kind"] == "vendor":
        route, reason = "forward_to_payables", f"known vendor {contact['name']}"
    elif any(w in text for w in ("invoice", "bill", "payment", "remit")):
        route, reason = "forward_to_payables", "billing language from unknown sender"
    elif any(w in text for w in ("help", "hire", "consult", "fractional", "coo", "hr", "interested")):
        route, reason = "offer_intake_call", "reads like a new lead"
    else:
        d = raise_decision("unknown_caller", f"{channel} from {sender}: \"{message[:120]}\" — how should reception respond?",
                           ["offer_intake_call", "route_to_owner", "discard"], {"sender": sender, "channel": channel})
        route, reason = "hold_for_decision", f"unclear intent -> {d['id']}"
    row = {"id": s.new_id("IN"), "channel": channel, "sender": sender, "message": message, "route": route,
           "contact_id": contact["id"] if contact else None, "on": s.today.isoformat()}
    s.insert("inbound", row)
    s.audit("reception", "triaged", f"{row['id']} {channel} {sender} -> {route} ({reason})")
    return json.dumps({"route": route, "reason": reason, "contact": contact, "inbound_id": row["id"]})
