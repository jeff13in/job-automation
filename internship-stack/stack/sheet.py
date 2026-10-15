"""The application tracker. One table, two interchangeable backends:

- GoogleSheetStore: the shared Google Sheet (what Claude, the applier and you all see)
- CsvStore: a local file with the same columns, for testing and dry runs
"""
from __future__ import annotations

import csv
from abc import ABC, abstractmethod
from pathlib import Path

from . import config
from .models import COLUMNS, Role, Status, now_iso


class Store(ABC):
    @abstractmethod
    def all(self) -> list[Role]: ...

    @abstractmethod
    def _append(self, roles: list[Role]) -> None: ...

    @abstractmethod
    def update(self, role_id: str, **changes: str) -> None: ...

    def add_new(self, roles: list[Role]) -> list[Role]:
        """Append roles whose id isn't already in the sheet. Returns what was added."""
        seen = {r.id for r in self.all()}
        fresh: list[Role] = []
        for r in roles:
            if r.id not in seen:
                seen.add(r.id)
                fresh.append(r)
        if fresh:
            self._append(fresh)
        return fresh

    def by_status(self, *statuses: Status) -> list[Role]:
        wanted = {s.value for s in statuses}
        return [r for r in self.all() if r.status in wanted]

    def claim_next(self) -> Role | None:
        """Oldest `new` row -> `in_progress`. Single-writer assumption: run one applier at a time."""
        queue = sorted(self.by_status(Status.NEW), key=lambda r: r.date_found)
        if not queue:
            return None
        role = queue[0]
        self.set_status(role.id, Status.IN_PROGRESS)
        role.status = Status.IN_PROGRESS.value
        return role

    def set_status(self, role_id: str, status: Status, **changes: str) -> None:
        if status != Status.BLOCKED:
            changes.setdefault("blocked_reason", "")
        self.update(role_id, status=status.value, **changes)

    def block(self, role_id: str, reason: str) -> None:
        self.set_status(role_id, Status.BLOCKED, blocked_reason=reason)


class CsvStore(Store):
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            with open(self.path, "w", newline="") as f:
                csv.writer(f).writerow(COLUMNS)

    def all(self) -> list[Role]:
        with open(self.path, newline="") as f:
            return [Role.from_dict(row) for row in csv.DictReader(f)]

    def _write_all(self, roles: list[Role]) -> None:
        tmp = self.path.with_suffix(".tmp")
        with open(tmp, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(COLUMNS)
            w.writerows(r.to_row() for r in roles)
        tmp.replace(self.path)

    def _append(self, roles: list[Role]) -> None:
        with open(self.path, "a", newline="") as f:
            csv.writer(f).writerows(r.to_row() for r in roles)

    def update(self, role_id: str, **changes: str) -> None:
        roles = self.all()
        for r in roles:
            if r.id == role_id:
                for k, v in changes.items():
                    setattr(r, k, str(v))
                r.last_update = now_iso()
                break
        else:
            raise KeyError(role_id)
        self._write_all(roles)


class GoogleSheetStore(Store):
    def __init__(self, sheet_id: str, worksheet: str, service_account_file: Path):
        import gspread

        gc = gspread.service_account(filename=str(service_account_file))
        sh = gc.open_by_key(sheet_id)
        try:
            self.ws = sh.worksheet(worksheet)
        except gspread.WorksheetNotFound:
            self.ws = sh.add_worksheet(worksheet, rows=1000, cols=len(COLUMNS))
        header = self.ws.row_values(1)
        if header != COLUMNS:
            if header:
                raise RuntimeError(f"Sheet header {header} doesn't match expected {COLUMNS}")
            self.ws.update(range_name="A1", values=[COLUMNS])
            self.ws.freeze(rows=1)

    def all(self) -> list[Role]:
        return [Role.from_dict(r) for r in self.ws.get_all_records(expected_headers=COLUMNS)]

    def _append(self, roles: list[Role]) -> None:
        self.ws.append_rows([r.to_row() for r in roles], value_input_option="RAW")

    def update(self, role_id: str, **changes: str) -> None:
        import gspread.utils as u

        cell = self.ws.find(role_id, in_column=1)
        if cell is None:
            raise KeyError(role_id)
        changes["last_update"] = now_iso()
        self.ws.batch_update([
            {"range": u.rowcol_to_a1(cell.row, COLUMNS.index(k) + 1), "values": [[str(v)]]}
            for k, v in changes.items()
        ])


def open_store() -> Store:
    cfg = config.load()["sheet"]
    if cfg["backend"] == "google":
        return GoogleSheetStore(cfg["google_sheet_id"], cfg["worksheet"],
                                config.path(cfg["service_account_file"]))
    return CsvStore(config.path(cfg["csv_path"]))
