"""A tiny JSON-backed office ledger. In production each table maps to a real system
(Google Calendar, QuickBooks Online, Cal.com, a CRM); here the same shapes live in one file
so the whole office runs end to end without credentials."""
from __future__ import annotations

import json
import os
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path(os.environ.get("QUIET_OFFICE_DATA", "data/office.json"))

TABLES = ["contacts", "events", "invoices", "reminders", "transactions", "bills",
          "payments", "compliance", "inbound", "decisions", "audit"]

_lock = threading.RLock()


class Store:
    def __init__(self, path: Path | str = DEFAULT_PATH):
        self.path = Path(path)
        self.data: dict[str, list[dict[str, Any]]] = {t: [] for t in TABLES}
        self.data["meta"] = {"today": date.today().isoformat(), "next_id": 1}  # type: ignore[assignment]
        if self.path.exists():
            self.data = json.loads(self.path.read_text())
            for t in TABLES:
                self.data.setdefault(t, [])

    # ---- persistence -------------------------------------------------
    def save(self) -> None:
        with _lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.data, indent=2, default=str))

    # ---- clock (the demo advances "today" so a month of activity can run in seconds)
    @property
    def today(self) -> date:
        return date.fromisoformat(self.data["meta"]["today"])

    def set_today(self, d: date) -> None:
        self.data["meta"]["today"] = d.isoformat()

    def now(self) -> datetime:
        return datetime.combine(self.today, datetime.min.time()).replace(hour=9)

    # ---- generic table ops ---------------------------------------------
    def new_id(self, prefix: str) -> str:
        n = self.data["meta"]["next_id"]
        self.data["meta"]["next_id"] = n + 1
        return f"{prefix}-{n:04d}"

    def insert(self, table: str, row: dict[str, Any]) -> dict[str, Any]:
        with _lock:
            self.data[table].append(row)
            self.save()
        return row

    def find(self, table: str, **where: Any) -> list[dict[str, Any]]:
        rows = self.data[table]
        return [r for r in rows if all(r.get(k) == v for k, v in where.items())]

    def get(self, table: str, id_: str) -> dict[str, Any] | None:
        hits = self.find(table, id=id_)
        return hits[0] if hits else None

    def update(self, table: str, id_: str, **changes: Any) -> dict[str, Any]:
        row = self.get(table, id_)
        if row is None:
            raise KeyError(f"{table}:{id_} not found")
        row.update(changes)
        self.save()
        return row

    def audit(self, actor: str, action: str, detail: str) -> None:
        self.insert("audit", {"ts": self.now().isoformat(), "actor": actor, "action": action, "detail": detail})


_store: Store | None = None


def get_store() -> Store:
    global _store
    if _store is None:
        _store = Store()
    return _store


def use_store(store: Store) -> None:
    global _store
    _store = store
