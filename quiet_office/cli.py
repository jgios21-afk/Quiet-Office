"""Command line for the office.

  quiet-office seed                 create demo data
  quiet-office daily                run the background daily close (Strands Graph)
  quiet-office inbox                show open decisions
  quiet-office decide DEC-0001 approve [--note "..."]
  quiet-office ask "book Ava a working session Thursday at 2"
  quiet-office advance 7            move the demo clock forward N days
  quiet-office audit                show the audit trail
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import timedelta

from .agents import build_office_manager
from .daily import run_daily_close
from .models import make_model
from .seed import seed
from .store import get_store
from .tools.decisions import list_open_decisions, resolve_decision


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="quiet-office", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("seed")
    sub.add_parser("daily")
    sub.add_parser("inbox")
    d = sub.add_parser("decide"); d.add_argument("decision_id"); d.add_argument("choice"); d.add_argument("--note", default="")
    a = sub.add_parser("ask"); a.add_argument("request")
    adv = sub.add_parser("advance"); adv.add_argument("days", type=int)
    sub.add_parser("audit")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(message)s")

    if args.cmd == "seed":
        s = seed(); print(f"Seeded {s.path} with {len(s.find('contacts'))} contacts, {len(s.find('events'))} events, "
                          f"{len(s.find('transactions'))} bank lines, {len(s.find('bills'))} bills.")
    elif args.cmd == "daily":
        print(run_daily_close())
    elif args.cmd == "inbox":
        rows = json.loads(list_open_decisions())
        if not rows:
            print("Inbox empty — the office needs nothing from you."); return
        for r in rows:
            print(f"[{r['id']}] {r['kind']}: {r['summary']}\n    options: {', '.join(r['options'])}")
    elif args.cmd == "decide":
        print(resolve_decision(decision_id=args.decision_id, choice=args.choice, note=args.note))
    elif args.cmd == "ask":
        print(build_office_manager(make_model())(args.request))
    elif args.cmd == "advance":
        s = get_store(); s.set_today(s.today + timedelta(days=args.days)); s.save(); print(f"Today is now {s.today}")
    elif args.cmd == "audit":
        for r in get_store().find("audit")[-40:]:
            print(f"{r['ts'][:16]}  {r['actor']:<18} {r['action']:<24} {r['detail']}")


if __name__ == "__main__":
    main()
