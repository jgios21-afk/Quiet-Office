"""The office staff. Each specialist is a Strands Agent with a narrow toolset and a plain-language
job description. The Office Manager orchestrates them (agents-as-tools) and owns the decision inbox.
The nightly close runs the specialists as a Strands Graph in a fixed order."""
from __future__ import annotations

from strands import Agent, tool
from strands.multiagent import GraphBuilder

from .guardrails import ApprovalGate, AuditTrail
from .tools import bookkeeping, compliance, decisions, payables, receivables, reception, scheduling

HOUSE_RULES = (
    "You work inside a small professional-services office. Act, don't ask: use your tools to do the work, "
    "and only raise a decision when the rules say a human must choose. Never invent data; if a tool returns "
    "nothing, say so. Keep your final reply to a short, plain-language summary of what you did and anything "
    "that now needs the owner. Do not repeat tool output verbatim."
)


def _agent(model, name: str, role: str, tools: list) -> Agent:
    return Agent(model=model, name=name, description=role, tools=tools,
                 system_prompt=f"You are the {name}. {role}\n\n{HOUSE_RULES}",
                 hooks=[ApprovalGate(), AuditTrail()], callback_handler=None)


def build_specialists(model) -> dict[str, Agent]:
    return {
        "scheduler": _agent(model, "Scheduler",
            "You keep the calendar honest: send reminders, close events that have ended, book requested slots "
            "within the booking rules, and record no-shows. Completed events are the handoff to Receivables.",
            [scheduling.list_events, scheduling.book_event, scheduling.send_event_reminders, scheduling.close_completed_events]),
        "receivables": _agent(model, "Receivables clerk",
            "You turn completed events and retainers into invoices, run the reminder ladder, apply payments, "
            "and report AR aging. You never write an invoice by hand; invoices come from records.",
            [receivables.generate_invoices_from_events, receivables.issue_retainer_invoices, receivables.run_reminder_ladder,
             receivables.record_payment, receivables.ar_aging]),
        "bookkeeper": _agent(model, "Bookkeeper",
            "You categorize the bank feed by the client's rules, match deposits to invoices, keep the unapplied-cash "
            "queue empty, and run the month-close checklist. When a rule can't place a transaction you ask, not guess.",
            [bookkeeping.categorize_transactions, bookkeeping.unapplied_cash_queue, bookkeeping.month_close_checklist]),
        "payables": _agent(model, "Payables clerk",
            "You capture bills, list what's due, and run the weekly payment run for approved bills only. "
            "You never pay an unapproved bill; the approval gate will stop you and raise a decision.",
            [payables.capture_bill, payables.bills_due, payables.pay_bill, payables.run_payment_run]),
        "receptionist": _agent(model, "Receptionist",
            "You answer inbound calls, emails and chats: look the sender up, triage intent, route known clients, "
            "forward vendor billing, offer new leads an intake call, and hold anything unclear for the owner.",
            [reception.lookup_contact, reception.create_contact, reception.triage_inbound, scheduling.book_event]),
        "compliance": _agent(model, "Compliance clerk",
            "You watch renewals, filings, taxes and licenses, and make sure nothing expires silently.",
            [compliance.add_compliance_item, compliance.upcoming_compliance, compliance.mark_compliance_done]),
    }


def build_office_manager(model, specialists: dict[str, Agent] | None = None) -> Agent:
    """Interactive orchestrator: delegates to specialists and owns the decision inbox."""
    staff = specialists or build_specialists(model)

    def delegate(key: str, doc: str):
        @tool(name=f"ask_{key}", description=doc)
        def _t(request: str) -> str:
            return str(staff[key](request))
        return _t

    delegates = [
        delegate("scheduler", "Hand a calendar task to the Scheduler (book, remind, close events, no-shows)."),
        delegate("receivables", "Hand an invoicing or collections task to the Receivables clerk."),
        delegate("bookkeeper", "Hand a bank-feed, categorization or month-close task to the Bookkeeper."),
        delegate("payables", "Hand a bill or payment task to the Payables clerk."),
        delegate("receptionist", "Hand an inbound call/email/chat to the Receptionist for triage and routing."),
        delegate("compliance", "Hand a renewal, filing or deadline task to the Compliance clerk."),
    ]
    return _agent(model, "Office manager",
        "You run the office for a busy owner. Route each request to the right specialist, combine their answers, "
        "and keep the decision inbox as the single place the owner has to look. When the owner resolves a decision, "
        "apply it with resolve_decision.",
        delegates + [decisions.list_open_decisions, decisions.resolve_decision])


def build_daily_close_graph(model, specialists: dict[str, Agent] | None = None):
    """The background job. A Strands Graph runs the specialists in dependency order:
    scheduler -> receivables -> bookkeeper -> payables -> compliance -> office manager digest."""
    staff = specialists or build_specialists(model)
    digest = _agent(model, "Digest writer",
        "You write the owner's morning digest: 3-6 short lines on what the office did overnight, then the open "
        "decisions as a numbered list with their options. If there are no decisions, say the office needs nothing.",
        [decisions.list_open_decisions, receivables.ar_aging, payables.bills_due])
    b = GraphBuilder()
    for key in ("scheduler", "receivables", "bookkeeper", "payables", "compliance"):
        b.add_node(staff[key], key)
    b.add_node(digest, "digest")
    b.add_edge("scheduler", "receivables")
    b.add_edge("receivables", "bookkeeper")
    b.add_edge("bookkeeper", "payables")
    b.add_edge("payables", "compliance")
    b.add_edge("compliance", "digest")
    b.set_entry_point("scheduler")
    return b.build()


DAILY_CLOSE_TASK = (
    "Run today's close for your part of the office. Scheduler: send reminders, close ended events. "
    "Receivables: invoice completed events and retainers, run the reminder ladder, report aging. "
    "Bookkeeper: categorize the bank feed, check unapplied cash. Payables: run the payment run for approved "
    "bills due this week. Compliance: check the next 30 days. Digest writer: write the owner's digest."
)
