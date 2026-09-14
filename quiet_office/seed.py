"""Demo data: a two-person consulting practice with a month of activity queued up."""
from __future__ import annotations

from datetime import date, timedelta

from .store import Store


def seed(path="data/office.json", today: date | None = None) -> Store:
    s = Store(path)
    s.data = {t: [] for t in s.data if t != "meta"} | {"meta": {"today": (today or date(2026, 9, 14)).isoformat(), "next_id": 1}}
    t = s.today
    contacts = [
        ("Ava Chen", "ava@northwindstudio.example", "client", "Northwind Studio", 1500),
        ("Marcus Reid", "marcus@reidfamilyoffice.example", "client", "Reid Family Office", 0),
        ("Priya Natarajan", "priya@brightpath.example", "client", "BrightPath Nonprofit", 900),
        ("Tomás Álvarez", "tomas@alvarezlaw.example", "lead", "Álvarez Law", 0),
        ("Metro Print Co", "billing@metroprint.example", "vendor", "Metro Print Co", 0),
    ]
    for name, email, kind, org, ret in contacts:
        s.insert("contacts", {"id": s.new_id("CON"), "name": name, "email": email, "kind": kind, "organization": org,
                              "no_shows": 0, "booking_paused": False, "retainer": ret})
    c = {r["name"]: r["id"] for r in s.find("contacts")}
    # Past events awaiting close, and upcoming ones
    ev = [
        ("working_session", c["Ava Chen"], t - timedelta(days=1), "held"),
        ("working_session", c["Marcus Reid"], t - timedelta(days=1), "no_show"),
        ("intake_call", c["Tomás Álvarez"], t - timedelta(days=2), "held"),
        ("working_session", c["Priya Natarajan"], t + timedelta(days=1), None),
        ("vendor_meeting", c["Metro Print Co"], t + timedelta(days=3), None),
    ]
    for i, (typ, cid, d, _) in enumerate(ev):
        s.insert("events", {"id": s.new_id("EVT"), "type": typ, "contact_id": cid,
                            "start": d.isoformat() + f"T{10 + i}:00:00", "minutes": 50 if typ == "working_session" else 20,
                            "status": "scheduled", "reminders_sent": []})
    s.data["meta"]["demo_outcomes"] = {e["id"]: o for e, (_, _, _, o) in zip(s.find("events"), ev) if o}
    # An old invoice already deep in the ladder
    s.insert("invoices", {"id": s.new_id("INV"), "contact_id": c["Marcus Reid"], "kind": "milestone", "amount": 2400.0, "paid": 0.0,
                          "memo": "Org design milestone 2", "source_id": "MS-2", "issued": (t - timedelta(days=47)).isoformat(),
                          "due": (t - timedelta(days=32)).isoformat(), "status": "open", "ladder_step": 4})
    s.insert("invoices", {"id": s.new_id("INV"), "contact_id": c["Ava Chen"], "kind": "event", "amount": 250.0, "paid": 0.0,
                          "memo": "working_session", "source_id": "EVT-old", "issued": (t - timedelta(days=8)).isoformat(),
                          "due": (t + timedelta(days=7)).isoformat(), "status": "open", "ladder_step": 0})
    # Bank feed
    feed = [(-14.40, "GOOGLE WORKSPACE"), (-32.00, "AMTRAK NE REGIONAL"), (250.00, "STRIPE PAYOUT"),
            (-89.99, "BLUE HERON SUPPLY CO"), (400.00, "ZELLE FROM P NATARAJAN"), (-1200.00, "GUSTO PAYROLL")]
    for amt, desc in feed:
        s.insert("transactions", {"id": s.new_id("TXN"), "date": (t - timedelta(days=1)).isoformat(), "amount": amt,
                                  "description": desc, "status": "new", "category": None})
    # Bills: one known vendor (has a paid history), one new, one large
    s.insert("bills", {"id": s.new_id("BILL"), "vendor": "Metro Print Co", "amount": 180.0, "due": (t - timedelta(days=20)).isoformat(),
                       "memo": "August print run", "received": (t - timedelta(days=30)).isoformat(), "status": "paid", "paid_on": (t - timedelta(days=21)).isoformat()})
    s.insert("bills", {"id": s.new_id("BILL"), "vendor": "Metro Print Co", "amount": 210.0, "due": (t + timedelta(days=5)).isoformat(),
                       "memo": "September print run", "received": t.isoformat(), "status": "pending"})
    s.insert("bills", {"id": s.new_id("BILL"), "vendor": "Harbor Insurance Group", "amount": 1450.0, "due": (t + timedelta(days=6)).isoformat(),
                       "memo": "GL policy renewal", "received": t.isoformat(), "status": "pending"})
    # Compliance
    for name, days, kind in [("NY quarterly sales tax filing", 6, "tax"), ("General liability policy renewal", 6, "renewal"),
                             ("Biennial statement (NY DOS)", 40, "filing")]:
        s.insert("compliance", {"id": s.new_id("CMP"), "name": name, "due": (t + timedelta(days=days)).isoformat(), "kind": kind, "notes": "", "status": "open"})
    s.save()
    return s
