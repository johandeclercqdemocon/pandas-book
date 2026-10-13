"""Check the book's key numbers with code that does not use pandas.

    python3 scripts/verify_claims.py        (needs only the standard library, plus pandas for the other side)

Each claim is computed twice: once from data/*.csv with the csv module and plain Python, and once
by the book's pandas code. The two must agree. The files are also pinned by SHA-256, so that a
regenerated data set (another numpy can change the bytes) is noticed before the text goes stale.
"""
from __future__ import annotations

import csv
import hashlib
import math
import pathlib
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DATA = ROOT / "data"

SHA256 = {
    "calls.csv": "03e292e147d8b9df665201fb7570fe928a13108cdf9254267849ed0a74219ad2",
    "cells.csv": "ad4033f772f830d2ba759d7f20ae2c3c74b8eab30c040bdb3a15160436d2f301",
    "contacts_messy.csv": "e22afa752aec94278f85f6fc41f3bf8e9ba924d37302ccc0aff13e21271ddce3",
    "kpi.csv": "2d01424cfc6c9cbd3b0feb017d0747dc1f8fa4d00d783509ea4aa9f59a3b5190",
    "plans.csv": "9664e71daa3b06fe8426f99d2e7b84c5bb94736a39a62d7a58b00b73fab0db4d",
    "subscribers.csv": "a1d3722bd60e76cfa75bc99ee33baf63e98959afa3a7ca6f007f8816785d9809",
    "runs.jsonl": "4ceefdf35dd851e3e684490ff9b296447eec8cc9cdbdb450d42f626077a0baf3",
    "traces.jsonl": "6a3907e3bae0189b4e73916017d76e6df1b257a96698fd58c282b82a5db95669",
}

results: list[tuple[bool, str]] = []


def claim(name: str, by_hand, by_pandas, tol: float = 0.0) -> None:
    ok = (by_hand == by_pandas) if tol == 0 else abs(by_hand - by_pandas) <= tol
    results.append((ok, f"{name}: hand {by_hand!r}, pandas {by_pandas!r}"))


def rows(name: str) -> list[dict]:
    with open(DATA / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def check_hashes() -> None:
    for name, want in SHA256.items():
        got = hashlib.sha256((DATA / name).read_bytes()).hexdigest()
        results.append((got == want, f"sha256 {name}"))


def main() -> int:
    import pandas as pd

    from pdbook.io import load_calls, load_cells, load_plans, load_subscribers
    from pdbook.rating import rate_vector
    from pdbook.report import monthly_report
    from pdbook.sessions import session_table, sessionize

    check_hashes()
    calls_raw, subs_raw, plans_raw = rows("calls.csv"), rows("subscribers.csv"), rows("plans.csv")
    calls, subs, cells, plans = load_calls(), load_subscribers(), load_cells(), load_plans()

    # Chapter 1, 2, 5: size, statuses, nulls, identifiers
    claim("rows of calls.csv", len(calls_raw), len(calls))
    status = Counter(r["status"] for r in calls_raw)
    claim("answered calls", status["answered"], int((calls["status"] == "answered").sum()))
    claim("failed calls", status["failed"], int((calls["status"] == "failed").sum()))
    claim("null durations", sum(r["duration_s"] == "" for r in calls_raw), int(calls["duration_s"].isna().sum()))
    claim("null cells", sum(r["cell_id"] == "" for r in calls_raw), int(calls["cell_id"].isna().sum()))
    claim("null codecs", sum(r["codec"] == "" for r in calls_raw), int(calls["codec"].isna().sum()))
    claim("roaming calls", sum(r["roaming"] == "True" for r in calls_raw), int(calls["roaming"].sum()))
    claim("distinct callers", len({r["caller"] for r in calls_raw}), int(calls["caller"].nunique()))
    claim("distinct callees", len({r["callee"] for r in calls_raw}), int(calls["callee"].nunique()))
    total = sum(float(r["duration_s"]) for r in calls_raw if r["duration_s"] != "")
    claim("total duration, s", total, float(calls["duration_s"].sum()), tol=1e-6)

    # Chapter 8: calls and answered calls for each plan
    plan_of = {r["subscriber_id"]: r["plan"] for r in subs_raw}
    answered_by_plan = Counter(plan_of[r["caller"]] for r in calls_raw if r["status"] == "answered")
    mapped = calls["caller"].map(dict(zip(subs["subscriber_id"], subs["plan"])))
    pandas_by_plan = calls[calls["status"] == "answered"].groupby(mapped).size().to_dict()
    claim("answered calls for each plan", dict(answered_by_plan), dict(pandas_by_plan))

    # Chapter 7, 16, 20: the bill, in plain Python
    rate = {r["plan"]: float(r["rate_per_min_eur"]) for r in plans_raw}
    bill = 0.0
    for r in calls_raw:
        if r["status"] == "answered":
            minutes = max(1, math.ceil(float(r["duration_s"]) / 60))
            bill += round(minutes * rate[plan_of[r["caller"]]], 2)
    claim("total bill, EUR", round(bill, 2), round(float(rate_vector(calls, subs, plans).sum()), 2), tol=0.005)
    report = monthly_report(calls, subs, cells, plans)
    claim("bill from the report", round(bill, 2), round(float(report["revenue_eur"].sum()), 2), tol=0.005)

    # Chapter 10: calls in the busiest local hour. September 2026 is summer time (UTC+2) for all of it.
    hours = Counter()
    for r in calls_raw:
        t = datetime.strptime(r["start"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) + timedelta(hours=2)
        hours[t.hour] += 1
    local_hours = calls["start"].dt.tz_convert("Europe/Brussels").dt.hour.value_counts()
    claim("busiest local hour", hours.most_common(1)[0], (int(local_hours.idxmax()), int(local_hours.max())))

    # Chapter 14: sessions with a gap of 30 minutes, in plain Python
    by_caller: dict[str, list[datetime]] = defaultdict(list)
    for r in calls_raw:
        by_caller[r["caller"]].append(datetime.strptime(r["start"], "%Y-%m-%dT%H:%M:%SZ"))
    sessions = 0
    for times in by_caller.values():
        times.sort()
        sessions += 1 + sum(1 for a, b in zip(times, times[1:]) if b - a > timedelta(minutes=30))
    claim("sessions, gap 30 min", sessions, len(session_table(sessionize(calls, "30min"))))

    # Chapter 9: calls whose callee is a subscriber
    msisdn = {r["msisdn"] for r in subs_raw}
    claim("on-net calls", sum(r["callee"] in msisdn for r in calls_raw),
          int(calls["callee"].isin(set(subs["msisdn"])).sum()))

    for ok, text in results:
        print(("PASS  " if ok else "FAIL  ") + text)
    failed = [t for ok, t in results if not ok]
    print(f"\n{len(results) - len(failed)} of {len(results)} claims agree")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
