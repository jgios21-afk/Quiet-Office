import json
import os
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.fake_model import ScriptedModel  # noqa: E402

from quiet_office import store as st  # noqa: E402
from quiet_office.agents import build_daily_close_graph, build_office_manager, DAILY_CLOSE_TASK  # noqa: E402
from quiet_office.seed import seed  # noqa: E402
from quiet_office.tools import bookkeeping, payables, receivables, scheduling  # noqa: E402
from quiet_office.tools.decisions import list_open_decisions, resolve_decision  # noqa: E402


def fresh(tmp_path):
    s = seed(tmp_path / "office.json")
    st.use_store(s)
    return s


def test_booking_rules_block_bad_slots(tmp_path):
    s = fresh(tmp_path)
    ava = s.find("contacts", name="Ava Chen")[0]["id"]
    assert "notice" in scheduling.book_event(event_type="working_session", contact_id=ava, start_iso=s.today.isoformat() + "T11:00:00")
    ok = scheduling.book_event(event_type="working_session", contact_id=ava, start_iso=(s.today + timedelta(days=2)).isoformat() + "T11:00:00")
    assert ok.startswith("{")
    assert "window" in scheduling.book_event(event_type="working_session", contact_id=ava, start_iso=(s.today + timedelta(days=2)).isoformat() + "T18:00:00")


def test_completed_events_become_invoices_and_no_show_fee(tmp_path):
    s = fresh(tmp_path)
    scheduling.close_completed_events(outcomes_json=json.dumps(s.data["meta"]["demo_outcomes"]))
    out = receivables.generate_invoices_from_events()
    kinds = sorted(i["kind"] for i in json.loads(out))
    assert kinds == ["event", "no_show"]


def test_ladder_escalates_old_invoice(tmp_path):
    fresh(tmp_path)
    out = receivables.run_reminder_ladder()
    assert "escalated" in out
    assert any(d["kind"] == "collections_escalation" for d in json.loads(list_open_decisions()))


def test_bookkeeper_asks_instead_of_guessing(tmp_path):
    fresh(tmp_path)
    r = json.loads(bookkeeping.categorize_transactions())
    assert r["asked_human"] and r["applied_to_invoices"] and r["booked"]


def test_payables_gate_and_human_approval(tmp_path):
    s = fresh(tmp_path)
    r = json.loads(payables.run_payment_run())
    assert any("Metro Print" in p for p in r["paid"])           # known vendor, under limit: paid
    assert any("Harbor" in x for x in r["skipped"])             # new vendor: held
    dec = next(d for d in json.loads(list_open_decisions()) if d["kind"] == "payment_approval")
    resolve_decision(decision_id=dec["id"], choice="approve")
    assert s.get("bills", dec["context"]["bill_id"])["status"] == "approved"
    assert "Paid" in payables.pay_bill(bill_id=dec["context"]["bill_id"])


def test_hook_blocks_unapproved_payment_through_agent(tmp_path):
    s = fresh(tmp_path)
    harbor = s.find("bills", vendor="Harbor Insurance Group")[0]
    from quiet_office.tools import payables as p
    from quiet_office.agents import _agent
    agent = _agent(ScriptedModel({"pay_bill": {"bill_id": harbor["id"]}}), "Payables clerk", "test", [p.pay_bill])
    agent("pay it")
    assert s.get("bills", harbor["id"])["status"] == "pending"
    assert any(a["action"] == "blocked_tool" for a in s.find("audit"))


def test_daily_close_graph_runs_end_to_end(tmp_path):
    s = fresh(tmp_path)
    model = ScriptedModel({"close_completed_events": {"outcomes_json": json.dumps(s.data["meta"]["demo_outcomes"])}})
    graph = build_daily_close_graph(model)
    result = graph(DAILY_CLOSE_TASK)
    assert str(result.status).endswith("COMPLETED")
    assert result.completed_nodes == 6
    kinds = {d["kind"] for d in json.loads(list_open_decisions())}
    assert {"payment_approval", "uncategorized_transaction", "collections_escalation", "compliance_due"} <= kinds


def test_office_manager_delegates(tmp_path):
    s = fresh(tmp_path)
    mgr = build_office_manager(ScriptedModel({f"ask_{k}": {"request": "run your daily tasks"} for k in ("scheduler", "receivables", "bookkeeper", "payables", "receptionist", "compliance")}))
    out = str(mgr("run everything"))
    assert "Done" in out
    assert any(a["action"].startswith("tool:ask_") for a in s.find("audit"))
