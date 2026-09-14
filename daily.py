"""The background loop. Run once per day (cron, EventBridge Scheduler, or AgentCore) — it does the
office's work and produces one digest. Returns the digest text."""
from __future__ import annotations

from .agents import DAILY_CLOSE_TASK, build_daily_close_graph
from .models import make_model
from .store import get_store


def render_digest() -> str:
    s = get_store()
    audit = [a for a in s.find("audit") if a["ts"].startswith(s.today.isoformat())]
    did = list(dict.fromkeys(f"- {a['action'].replace('_', ' ')}: {a['detail']}" for a in audit
                             if a["action"] in ("booked", "invoice_issued", "paid", "closed_events", "payment", "blocked_tool")))
    lines = [f"Quiet Office digest for {s.today:%A, %B %d}", "", "Overnight the office:"] + (did or ["- nothing to do"])
    open_ = s.find("decisions", status="open")
    lines += ["", f"Needs you ({len(open_)}):"] + [f"{i}. [{d['id']}] {d['summary']}  ->  {' / '.join(d['options'])}" for i, d in enumerate(open_, 1)]
    return "\n".join(lines)


def run_daily_close(model=None) -> str:
    model = model or make_model()
    graph = build_daily_close_graph(model)
    result = graph(DAILY_CLOSE_TASK)
    node = result.results.get("digest")
    text = str(node.result) if node else "(no digest produced)"
    if text.startswith("Done:"):  # scripted offline model: render the digest deterministically
        text = render_digest()
    s = get_store()
    s.audit("office", "daily_close", f"status={result.status} nodes={result.completed_nodes}/{result.total_nodes}")
    return text
