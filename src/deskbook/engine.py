"""Booking rules applied to a stream of desk requests, first come first served."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class Request:
    """One desk request, in the order it arrived."""

    rid: str
    person: str
    desk: str
    start: datetime
    end: datetime
    showed_up: bool = True

    @property
    def hours(self) -> float:
        return (self.end - self.start).total_seconds() / 3600


@dataclass(frozen=True)
class Decision:
    """The outcome for one request. `reason` is empty when accepted."""

    request: Request
    accepted: bool
    reason: str = ""


def _time(value: str, line: int) -> datetime:
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d %H:%M")
    except ValueError:
        raise ValueError(f"line {line}: bad time '{value}', expected YYYY-MM-DD HH:MM") from None


def load_desks(path: str | Path) -> set[str]:
    """Read a CSV with a `desk` column and return the desk names."""
    with open(path, newline="", encoding="utf-8") as fh:
        desks = {row["desk"].strip() for row in csv.DictReader(fh) if row.get("desk")}
    if not desks:
        raise ValueError(f"{path}: no desks found, need a 'desk' column")
    return desks


def load_requests(path: str | Path) -> list[Request]:
    """Read a CSV with request,person,desk,start,end and an optional showed_up (yes/no) column."""
    out: list[Request] = []
    with open(path, newline="", encoding="utf-8") as fh:
        for n, row in enumerate(csv.DictReader(fh), start=2):
            try:
                out.append(Request(
                    row["request"].strip(), row["person"].strip(), row["desk"].strip(),
                    _time(row["start"], n), _time(row["end"], n),
                    (row.get("showed_up") or "yes").strip().lower() != "no",
                ))
            except (KeyError, AttributeError):
                raise ValueError(f"{path} line {n}: need request,person,desk,start,end") from None
    return out


def _overlaps(a: Request, b: Request) -> bool:
    return a.start < b.end and b.start < a.end


def simulate(requests: list[Request], desks: set[str], max_hours: float = 8.0) -> list[Decision]:
    """Accept or reject each request in order.

    A request is rejected when: the desk does not exist, the end is not after the start, the booking is longer
    than max_hours, the desk is already booked for part of that time, or the person already holds another
    booking that overlaps it.
    """
    taken: list[Request] = []
    result: list[Decision] = []
    for r in requests:
        reason = ""
        if r.desk not in desks:
            reason = "unknown desk"
        elif r.end <= r.start:
            reason = "end not after start"
        elif r.hours > max_hours:
            reason = f"longer than {max_hours:g} hours"
        elif any(t.desk == r.desk and _overlaps(t, r) for t in taken):
            reason = "desk already booked"
        elif any(t.person == r.person and _overlaps(t, r) for t in taken):
            reason = "person already booked then"
        if reason:
            result.append(Decision(r, False, reason))
        else:
            taken.append(r)
            result.append(Decision(r, True))
    return result


def summarize(decisions: list[Decision], desks: set[str], day_hours: float = 8.0) -> dict:
    """Counts, rejection reasons, no-show hours and booked-hours utilization per desk."""
    ok = [d.request for d in decisions if d.accepted]
    days = {r.start.date() for r in ok} or set()
    reasons: dict[str, int] = {}
    for d in decisions:
        if not d.accepted:
            reasons[d.reason] = reasons.get(d.reason, 0) + 1
    by_desk = {}
    for desk in sorted(desks):
        booked = sum(r.hours for r in ok if r.desk == desk)
        capacity = day_hours * len(days)
        by_desk[desk] = round(100 * booked / capacity, 1) if capacity else 0.0
    return {
        "requests": len(decisions),
        "accepted": len(ok),
        "rejected": len(decisions) - len(ok),
        "reasons": reasons,
        "no_show_hours": round(sum(r.hours for r in ok if not r.showed_up), 1),
        "by_desk": by_desk,
    }
