"""Policy defaults for the office. Everything the agents decide on their own is defined here,
so a client can change a number without touching agent prompts or tool code."""
from dataclasses import dataclass


@dataclass(frozen=True)
class BookingType:
    name: str
    minutes: int
    buffer_after: int
    daily_cap: int
    billable: bool
    rate: float  # USD per event when billable


BOOKING_TYPES = {
    "intake_call": BookingType("intake_call", 20, 10, 4, billable=False, rate=0),
    "working_session": BookingType("working_session", 50, 10, 3, billable=True, rate=250),
    "vendor_meeting": BookingType("vendor_meeting", 30, 5, 2, billable=False, rate=0),
}

MIN_NOTICE_HOURS = 24
MAX_LEAD_DAYS = 30
BOOKING_WINDOW = (10, 16)  # local hours, inclusive start / exclusive end
NO_SHOW_FEE = 75.0
NO_SHOWS_BEFORE_PAUSE = 2

PAYMENT_TERMS_DAYS = {"event": 15, "no_show": 15, "milestone": 15, "retainer": 0}

# Receivables reminder ladder: day offset from invoice date -> (channel, tone)
REMINDER_LADDER = [
    (7, "email", "friendly"),
    (14, "email", "direct"),
    (16, "email+sms", "direct"),
    (30, "email", "formal"),
]
ESCALATE_AT_DAY = 45  # becomes a human decision

# Payables: anything above this, or any first-time vendor, needs a human approval
AUTO_PAY_LIMIT = 500.0

# Bookkeeping: keyword -> ledger category. Unknown descriptions become a decision.
CATEGORY_RULES = {
    "google": "Software & subscriptions",
    "workspace": "Software & subscriptions",
    "quickbooks": "Software & subscriptions",
    "cal.com": "Software & subscriptions",
    "zoom": "Software & subscriptions",
    "amtrak": "Travel",
    "uber": "Travel",
    "lyft": "Travel",
    "mta": "Travel",
    "staples": "Office supplies",
    "usps": "Postage & shipping",
    "fedex": "Postage & shipping",
    "insurance": "Insurance",
    "verizon": "Telephone & internet",
    "payroll": "Payroll",
    "gusto": "Payroll",
}

DSO_ALERT_DAYS = 20
UNAPPLIED_CASH_MAX_AGE_DAYS = 7
COMPLIANCE_LOOKAHEAD_DAYS = 30
