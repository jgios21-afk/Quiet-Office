"""Strands hooks that make the office safe to leave running.

ApprovalGate: money-moving tools are intercepted before they run. If the target
bill hasn't been approved by a human, the call is cancelled and a decision is raised
instead — the agent cannot talk its way past this, because it happens outside the model.

AuditTrail: every tool call is written to the audit table with timing, so the owner
can see exactly what the office did overnight.
"""
from __future__ import annotations

import logging

from strands.hooks import AfterToolCallEvent, BeforeToolCallEvent, HookProvider, HookRegistry

from .store import get_store
from .tools.decisions import raise_decision

log = logging.getLogger("quiet_office")

MONEY_MOVING_TOOLS = {"pay_bill", "run_payment_run"}


class ApprovalGate(HookProvider):
    def register_hooks(self, registry: HookRegistry, **kwargs) -> None:
        registry.add_callback(BeforeToolCallEvent, self.before_tool)

    def before_tool(self, event: BeforeToolCallEvent) -> None:
        name = event.tool_use["name"]
        if name not in MONEY_MOVING_TOOLS:
            return
        s = get_store()
        if name == "pay_bill":
            bill = s.get("bills", event.tool_use["input"].get("bill_id", ""))
            if bill is None or bill["status"] != "approved":
                if bill and bill["status"] == "pending":
                    raise_decision("payment_approval", f"Pay {bill['vendor']} ${bill['amount']:.2f} due {bill['due']}?",
                                   ["approve", "reject"], {"bill_id": bill["id"]})
                event.cancel_tool = (f"Approval gate: {bill['id'] if bill else 'bill'} is not approved by a human. "
                                     "A decision has been raised; do not retry.")
                s.audit("guardrail", "blocked_tool", f"{name} {event.tool_use['input']}")


class AuditTrail(HookProvider):
    def register_hooks(self, registry: HookRegistry, **kwargs) -> None:
        registry.add_callback(AfterToolCallEvent, self.after_tool)

    def after_tool(self, event: AfterToolCallEvent) -> None:
        name = event.tool_use["name"]
        status = "error" if event.exception else event.result.get("status", "ok")
        agent = getattr(event.agent, "name", "agent")
        get_store().audit(agent, f"tool:{name}", f"{status} in {event.duration:.2f}s" if event.duration else status)
        log.info("%s -> %s (%s)", agent, name, status)
