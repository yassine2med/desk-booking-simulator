"""Command line for the desk booking simulator."""
from __future__ import annotations

import argparse
import sys

from .engine import load_desks, load_requests, simulate, summarize


def _run(args: argparse.Namespace) -> int:
    desks = load_desks(args.desks)
    decisions = simulate(load_requests(args.requests), desks, args.max_hours)
    for d in decisions:
        r = d.request
        when = f"{r.start:%m-%d %H:%M}-{r.end:%H:%M}"
        verdict = "OK      " if d.accepted else "REJECTED"
        print(f"{r.rid:<5}{verdict} {r.person:<8}{r.desk:<6}{when}  {d.reason}".rstrip())
    s = summarize(decisions, desks, args.day_hours)
    print()
    print(f"Requests {s['requests']}: accepted {s['accepted']}, rejected {s['rejected']}")
    for reason, count in sorted(s["reasons"].items()):
        print(f"  {count} x {reason}")
    print(f"Booked but no-show: {s['no_show_hours']:g} desk-hours")
    if args.by_desk:
        print()
        print(f"Booked share of a {args.day_hours:g}-hour day:")
        for desk, pct in s["by_desk"].items():
            print(f"  {desk:<6}{pct:>6.1f} %")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="deskbook", description="Replay desk requests against booking rules.")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="decide every request in order and print a summary")
    r.add_argument("desks")
    r.add_argument("requests")
    r.add_argument("--max-hours", type=float, default=8.0, help="longest single booking (default 8)")
    r.add_argument("--day-hours", type=float, default=8.0, help="hours in a desk day for utilization (default 8)")
    r.add_argument("--by-desk", action="store_true", help="also print booked share per desk")
    r.set_defaults(func=_run)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, OSError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 2
