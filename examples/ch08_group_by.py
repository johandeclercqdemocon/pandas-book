"""Chapter 8: one row per subscriber, and the checks that make it trustworthy."""
import pandas as pd

from pdbook.io import load_calls, load_subscribers
from pdbook.summary import subscriber_summary

calls, subs = load_calls(), load_subscribers()
summary = subscriber_summary(calls, subs)
print(summary.head(5).drop(columns=["first_call", "last_call"]).to_string(index=False))
print()
checks = {
    "one row per subscriber": len(summary) == len(subs) and summary["subscriber_id"].is_unique,
    "calls add up to the table": int(summary["calls"].sum()) == len(calls),
    "answered add up": int(summary["answered"].sum()) == int((calls["status"] == "answered").sum()),
    "talk time adds up": abs(summary["talk_min"].sum() - calls["duration_s"].fillna(0).sum() / 60) < 0.05 * len(summary),
}
for name, ok in checks.items():
    print(("PASS  " if ok else "FAIL  ") + name)
assert all(checks.values())
