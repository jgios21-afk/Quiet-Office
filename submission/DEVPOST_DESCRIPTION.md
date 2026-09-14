# Devpost submission text — Quiet Office

**Track:** Professional Agents
**Tagline (≤60 chars):** The back office that only speaks up when it matters.

## Inspiration

I run a fractional COO/CHRO practice. The clients I serve — two-to-ten-person consultancies, studios, and nonprofits — all lose the same 8–12 hours a week: closing out the calendar, typing invoices, chasing late payers, categorizing the bank feed, approving bills, screening inbound calls, and remembering that the insurance renews Friday. I had already designed an "automated office" template for these clients as an operating standard. The hackathon was the push to make the template *run*.

## What it does

Quiet Office is an autonomous back office. Every night, a Strands Graph runs six specialist agents in dependency order — Scheduler, Receivables clerk, Bookkeeper, Payables clerk, Receptionist, Compliance clerk — and a Digest writer turns the run into one morning message. The owner reads 3–6 lines about what happened and a numbered list of the decisions that genuinely need a human: *pay this first-time vendor $1,450?* *This client is 47 days late — payment plan, pause, or write off?* *Which category is "Blue Heron Supply"?* Each is one tap.

Everything else — reminders, closing events, generating invoices from completed work, the four-step collections ladder, categorizing 80% of the bank feed, auto-paying known vendors under $500, routing a known client's email, flagging a renewal due in 30 days — happens without the owner.

## How we built it

- **Strands Agents SDK** throughout: six specialist `Agent`s, each with a narrow `@tool` set (25 tools across 7 modules) and a plain-language job description.
- **Agents-as-tools**: an Office manager agent wraps each specialist as a tool for interactive requests and owns the decision inbox.
- **Strands Graph**: the nightly close is a `GraphBuilder` graph — scheduler → receivables → bookkeeper → payables → compliance → digest — so the order is deterministic and the handoffs (completed events → invoices → bank matching → payment run) are explicit.
- **Strands hooks as guardrails**: `ApprovalGate` uses `BeforeToolCallEvent` to cancel money-moving tools unless a human has approved the bill; the check happens outside the model, so the agent cannot talk its way past it. `AuditTrail` logs every tool call via `AfterToolCallEvent`.
- **Policy as configuration**: every number the agents act on (booking window, buffers, Net-15, reminder days, $500 auto-pay limit, category rules, alert thresholds) lives in `rules.py`, so onboarding a new client means editing config, not prompts.
- **Claude on Amazon Bedrock** as the default model, with an AgentCore Runtime entrypoint (`agentcore/app.py`) and an EventBridge-schedulable `{"action": "daily"}` payload.
- A JSON systems-of-record layer stands in for Google Calendar, Cal.com, QuickBooks Online, the bank feed, and the CRM so the whole office runs end to end in a demo; each table maps 1:1 to a real adapter.

## Challenges we ran into

Deciding what the agent should *not* do. The first instinct is to let the model categorize every transaction and pay every bill. The right design was the opposite: rules handle the 80% with certainty, and the model's job is orchestration, summarization, and knowing when to stop and ask. Putting the approval gate in a hook rather than a prompt was the turning point — it made the system trustworthy enough to run unattended.

## Accomplishments we're proud of

A complete office loop — book → hold → invoice → remind → collect → categorize → close — that runs in one Graph call and produces a digest a real owner would read. Eight passing tests, including one that proves the hook blocks an unapproved payment from inside the agent event loop.

## What we learned

Strands hooks and Graph make "autonomous but safe" a structural property rather than a prompt-engineering hope. The decision inbox pattern — one queue, typed decisions, fixed options, an audit trail — generalizes to any back-office domain.

## What's next

Real adapters (Google Calendar, Cal.com webhooks, QuickBooks Online, Plaid, Bill.com), a voice front door on Amazon Connect, AgentCore Memory for per-client preferences, and a one-page owner dashboard. Then deployment to the consulting clients the template was designed for.

## Built with

Python, Strands Agents SDK, Amazon Bedrock (Claude), Amazon Bedrock AgentCore, pytest
