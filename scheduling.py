"""Phase 1 — scheduling and calendar. Bookings obey buffers, caps, notice and window rules;
completed events become records that receivables consumes."""
from __future__ import annotations

import json
from datetime import datetime, timedelta

from strands import tool

from .. import rules
from ..store import get_store
from .decisions import raise_decision


@tool
def list_events(status: str = "scheduled") -> str:
    """List calendar events by status: scheduled, completed, no_show, cancelled. Returns JSON."""
    return json.dumps(get_store().find("events", status=status), indent=2)


@tool
def book_event(event_type: str, contact_id: str, start_iso: str) -> str:
    """Book an event on the Bookings calendar, enforcing the booking rules
    (type must exist, 24h minimum notice, 30-day max lead, 10:00-16:00 window, daily cap,
    buffer after the previous event, guest not paused). Returns the event or the rule that blocked it."""
    s = get_store()
    bt = rules.BOOKING_TYPES.get(event_type)
    if bt is None:
        return f"Unknown event type. Choose from {list(rules.BOOKING_TYPES)}"
    contact = s.get("contacts", contact_id)
    if contact is None:
        return f"Unknown contact {contact_id}"
    if contact.get("booking_paused"):
        return f"Blocked: {contact['name']} has booking privileges paused after repeated no-shows."
    start = datetime.fromisoformat(start_iso)
    now = s.now()
    if start < now + timedelta(hours=rules.MIN_NOTICE_HOURS):
        return f"Blocked: less than {rules.MIN_NOTICE_HOURS} hours notice."
    if start > now + timedelta(days=rules.MAX_LEAD_DAYS):
        return f"Blocked: more than {rules.MAX_LEAD_DAYS} days out."
    lo, hi = rules.BOOKING_WINDOW
    end = start + timedelta(minutes=bt.minutes)
    if start.hour < lo or end.hour > hi or (end.hour == hi and end.minute > 0):
        return f"Blocked: outside the {lo:02d}:00-{hi:02d}:00 booking window."
    same_day = [e for e in s.find("events", status="scheduled") if e["start"][:10] == start.date().isoformat()]
    if len([e for e in same_day if e["type"] == event_type]) >= bt.daily_cap:
        return f"Blocked: daily cap of {bt.daily_cap} for {event_type} reached on {start.date()}."
    for e in same_day:
        e_start = datetime.fromisoformat(e["start"])
        e_end = e_start + timedelta(minutes=rules.BOOKING_TYPES[e["type"]].minutes + rules.BOOKING_TYPES[e["type"]].buffer_after)
        my_end = end + timedelta(minutes=bt.buffer_after)
        if start < e_end and e_start < my_end:
            return f"Blocked: overlaps {e['id']} (including buffer)."
    row = {"id": s.new_id("EVT"), "type": event_type, "contact_id": contact_id, "start": start.isoformat(),
           "minutes": bt.minutes, "status": "scheduled", "reminders_sent": []}
    s.insert("events", row)
    s.audit("scheduling", "booked", f"{row['id']} {event_type} with {contact['name']} at {start_iso}")
    return json.dumps(row)


@tool
def send_event_reminders() -> str:
    """Send the 24-hour and 1-hour reminders for tomorrow's and today's events (simulated send).
    Returns a summary of what went out."""
    s = get_store()
    sent = []
    for e in s.find("events", status="scheduled"):
        start = datetime.fromisoformat(e["start"])
        delta = start - s.now()
        if timedelta(0) <= delta <= timedelta(hours=36) and "24h" not in e["reminders_sent"]:
            e["reminders_sent"].append("24h"); sent.append(f"{e['id']} 24h email")
        if timedelta(0) <= delta <= timedelta(hours=2) and "1h" not in e["reminders_sent"]:
            e["reminders_sent"].append("1h"); sent.append(f"{e['id']} 1h sms")
    s.save()
    return "Sent: " + (", ".join(sent) if sent else "nothing due")


@tool
def close_completed_events(outcomes_json: str = "{}") -> str:
    """Close every scheduled event whose end time has passed. outcomes_json optionally maps
    event_id -> 'held' | 'no_show' (default 'held'). Writes the completed-event record
    (type, guest, duration, outcome, billable) that receivables reads. Repeated no-shows raise a decision."""
    s = get_store()
    outcomes = json.loads(outcomes_json or "{}")
    closed = []
    for e in s.find("events", status="scheduled"):
        end = datetime.fromisoformat(e["start"]) + timedelta(minutes=e["minutes"])
        if end > s.now():
            continue
        outcome = outcomes.get(e["id"], "held")
        bt = rules.BOOKING_TYPES[e["type"]]
        s.update("events", e["id"], status="completed" if outcome == "held" else "no_show",
                 outcome=outcome, billable=bt.billable and outcome == "held", invoiced=False)
        closed.append(f"{e['id']}:{outcome}")
        if outcome == "no_show":
            c = s.get("contacts", e["contact_id"])
            c["no_shows"] = c.get("no_shows", 0) + 1
            s.save()
            if c["no_shows"] >= rules.NO_SHOWS_BEFORE_PAUSE and not c.get("booking_paused"):
                raise_decision("no_show_pause", f"{c['name']} has missed {c['no_shows']} bookings. Pause booking privileges?",
                               ["pause", "allow"], {"contact_id": c["id"]})
    s.audit("scheduling", "closed_events", ", ".join(closed) or "none")
    return "Closed: " + (", ".join(closed) if closed else "nothing to close")
