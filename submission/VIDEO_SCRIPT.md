# Demo video script — 4 min 30 sec target (max 5:00)

Record with screen capture + voiceover. No camera needed. Terminal font large (18pt+), dark theme.
Before recording: `export QUIET_OFFICE_PROVIDER=bedrock` (or `scripted` if Bedrock isn't set up — say so honestly on screen: "running the scripted model for reproducibility").

---

**[0:00–0:35] Problem — slide: title + one sentence**
"I'm a fractional COO. Every small firm I work with loses eight to twelve hours a week to the same loop: close out the calendar, type invoices, chase late payers, categorize the bank feed, approve bills, screen calls, and remember the insurance renews Friday. None of it is hard. All of it interrupts the actual work.

Quiet Office is a back office that does that loop overnight — and only speaks up when there's a real decision."

**[0:35–1:05] Who it's for + why it matters — slide: the six functions**
"It's built for two-to-ten-person consultancies, studios and nonprofits — the people who can't afford an office manager but are doing the job themselves at 11pm. The goal isn't another dashboard to check. The goal is one morning message and a handful of one-tap decisions."

**[1:05–1:45] Architecture — show docs/architecture.png**
"It's built on the Strands Agents SDK. Six specialist agents, each with a narrow tool set. An Office manager orchestrates them as tools for ad-hoc requests. The nightly run is a Strands Graph — scheduler, receivables, bookkeeper, payables, compliance, then a digest writer — so the order is deterministic and the handoffs are explicit. Two Strands hooks sit on every agent: an approval gate that cancels money-moving tools unless a human approved, and an audit trail."

**[1:45–2:15] Seed — terminal**
```
quiet-office seed
```
"Here's a demo practice: five contacts, yesterday's sessions waiting to be closed — one was a no-show — a bank feed, three bills including a first-time vendor, and a sales-tax filing due Friday."

**[2:15–3:15] The nightly run — terminal**
```
quiet-office -v daily
```
"Watch the Graph run. The scheduler closes yesterday's events and records the no-show. Receivables turns the held session into a $250 invoice and the no-show into a $75 fee, then runs the reminder ladder — one invoice is 47 days old, so that escalates. The bookkeeper categorizes the feed, matches a Stripe payout to an invoice, and asks about the one line no rule can place. Payables auto-approves the known print vendor under $500 and pays it — and here, the approval gate blocks the $1,450 insurance bill from a first-time vendor. Compliance flags the two items due Friday.

And the digest." *(pause on the digest output)*

**[3:15–3:50] The inbox — terminal**
```
quiet-office inbox
quiet-office decide DEC-0029 approve
quiet-office audit | tail -8
```
"Five decisions. Each has fixed options. I approve the insurance bill — and the audit trail shows exactly what the office did, including the tool the gate blocked."

**[3:50–4:15] Interactive — terminal**
```
quiet-office ask "Ava wants another working session Thursday at 2pm — book it and tell me what else is open"
```
"The Office manager delegates to the Scheduler, which enforces the buffer and cap rules, then reports back."

**[4:15–4:30] Close — slide**
"Quiet Office: Strands Graph for the loop, agents-as-tools for requests, hooks for safety, one decision inbox for the human. Apache-licensed, AgentCore-ready. Thank you."

---

Slides needed (3): title, six functions, close. Reuse docs/architecture.png for the architecture beat.
